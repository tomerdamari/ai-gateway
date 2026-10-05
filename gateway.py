"""AI gateway: every model call in the company goes through here.

Accounts (employees or apps) belong to teams. Each account and each team has a monthly budget; a call is blocked
when either runs out. Employees log in to the chat page (/) with a password; apps call the provider APIs through
us with a gateway key. Provider keys never leave this server; gateway keys and passwords are stored only as hashes.

Run:      ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... python gateway.py
Pages:    /        management (open from the office network; from outside only with ADMIN_PASSWORD); also /admin
          /chat    chat for employees
Apps:     Anthropic SDK -> base_url http://HOST:8080        (POST /v1/messages)
          OpenAI SDK    -> base_url http://HOST:8080/v1     (POST /v1/chat/completions, also for Gemini models)
"""
import base64
import collections
import hashlib
import http.cookies
import ipaddress
import json
import math
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import mcp
import security
import sources

# Without Docker: read KEY=VALUE lines from .env next to this file. Real environment variables win.
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env):
    with open(_env, encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())

VERSION = "1.0.0"  # also in ui.js (shown in the admin footer); CHANGELOG.md lists what each version changed
DB =os.environ.get("GATEWAY_DB", "gateway.db")
# Admin from a private-network address (office LAN, this machine) needs no password.
# From anywhere else: this password, or no access at all when it's empty.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
# Host names this server answers to, besides IP addresses and localhost. Blocks "DNS rebinding": a hostile site
# pointing its own name at this server's address so the victim's browser talks to us as that site.
# Open access: from the office network the chat needs no password; people pick their own name.
# Budgets and logs still work per name, but anyone inside can act as anyone. From outside, passwords as usual.
# Public deployment (a cloud host): every visitor arrives through the host's private network, so "private address"
# no longer means "inside the office". Then the admin page always needs ADMIN_PASSWORD and open access is off.
PUBLIC = os.environ.get("PUBLIC_DEPLOY", "").strip().lower() in ("1", "true", "yes", "on")
OPEN_ACCESS = not PUBLIC and os.environ.get("OPEN_ACCESS", "").strip().lower() in ("1", "true", "yes", "on")
ALLOWED_HOSTS = {h.strip().lower() for h in [os.environ.get("SITE_ADDRESS", ""), os.environ.get("RENDER_EXTERNAL_HOSTNAME", ""),
                                             *os.environ.get("ALLOWED_HOSTS", "").split(",")]
                 if h.strip() and not h.strip().startswith(":")}
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = {"/": ("admin.html", "text/html"), "/admin": ("admin.html", "text/html"), "/chat": ("chat.html", "text/html"), "/docs": ("docs.html", "text/html"), "/style.css": ("style.css", "text/css"),
         "/ui.js": ("ui.js", "text/javascript"),
         "/logo.svg": ("logo.svg", "image/svg+xml"),
         "/docs.js": ("docs.js", "text/javascript"),
         "/en-admin.js": ("en-admin.js", "text/javascript"),
         "/en-chat.js": ("en-chat.js", "text/javascript"),
         "/en-docs.js": ("en-docs.js", "text/javascript"),
         "/i18n.js": ("i18n.js", "text/javascript"),
         "/fonts/heebo-hebrew.woff2": ("fonts/heebo-hebrew.woff2", "font/woff2"), "/fonts/heebo-latin.woff2": ("fonts/heebo-latin.woff2", "font/woff2"),
         "/chat.js": ("chat.js", "text/javascript"), "/admin.js": ("admin.js", "text/javascript")}
# Scripts only from our own files: an injected <script> or onclick= in any text we show can't run.
CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
SOFT_LIMIT = 0.8  # warn at 80% of budget, block at 100%
SESSION_HOURS = 12
LOCK_AFTER, LOCK_MINUTES = 5, 15  # wrong passwords in a row -> account locked for a while
PBKDF2_ROUNDS = 200_000
_int = lambda k, d: int(os.environ.get(k, "").strip() or d)
MAX_BODY = _int("MAX_BODY", 40 * 1024 * 1024)  # bytes: document uploads (base64) and app calls (may carry images/PDFs)
MAX_REQUEST_BODY = _int("MAX_REQUEST_BODY", 1024 * 1024)  # bytes: every other request (chat, admin changes)
MAX_OUTPUT_TOKENS = _int("MAX_OUTPUT_TOKENS", 8192)  # an app asking for more answer tokens is clamped to this
MAX_CONCURRENT = _int("MAX_CONCURRENT", 4)  # questions in progress at once per account; more -> 429
MAX_MESSAGES = _int("MAX_MESSAGES", 500)  # messages in one request
LOGIN_IP_LIMIT, LOGIN_IP_MINUTES = 10, 15  # wrong passwords from one address (any names) -> that address waits
SPIKE_MIN, SPIKE_FACTOR = 5.0, 5  # cost-spike alert: last hour above max($5, 5x the account's usual hour)
# Proxies whose X-Forwarded-For / X-Forwarded-Proto we believe (IPs or CIDR ranges, comma-separated). Anyone else
# sending those headers is ignored: otherwise a visitor could claim an office address and skip the admin password.
TRUSTED_PROXIES = [ipaddress.ip_network(p.strip(), strict=False)
                   for p in os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if p.strip()]
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# provider -> (client-facing path, upstream URL, auth headers, usage field names for input/output tokens).
# Each provider keeps its own request format, so apps use the provider's own SDK pointed at us.
PROVIDERS = {
    "anthropic": (
        "/v1/messages",
        os.environ.get("ANTHROPIC_URL", "https://api.anthropic.com/v1/messages"),
        {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01"},
        ("input_tokens", "output_tokens"),
    ),
    "openai": (
        "/v1/chat/completions",
        os.environ.get("OPENAI_URL", "https://api.openai.com/v1/chat/completions"),
        {"authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "")},
        ("prompt_tokens", "completion_tokens"),
    ),
    "gemini": (  # Gemini's OpenAI-compatible endpoint
        "/v1/chat/completions",
        os.environ.get("GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
        {"authorization": "Bearer " + os.environ.get("GEMINI_API_KEY", "")},
        ("prompt_tokens", "completion_tokens"),
    ),
}

# Models live in the database and are managed from the admin "models" page.
# These are only the first-run defaults: alias, label, provider, real model, $ per 1M input / output tokens.
# Prices checked 2026-10-04; Gemini 3.8 Flash price is promotional until 2026-12-31.
DEFAULT_MODELS = [
    ("fast", "Claude מהיר", "anthropic", "claude-haiku-4-5-20251001", 1.0, 5.0),
    ("smart", "Claude חכם", "anthropic", "claude-sonnet-5-5", 2.0, 10.0),
    ("gpt-fast", "GPT מהיר", "openai", "gpt-6-luna", 0.10, 0.50),
    ("gpt-smart", "GPT חכם", "openai", "gpt-6.1-sol", 2.0, 10.0),
    ("gemini-fast", "Gemini מהיר", "gemini", "gemini-3.8-flash", 0.75, 3.75),
    ("gemini-smart", "Gemini חכם", "gemini", "gemini-3.1-pro-preview", 2.0, 12.0),
]
# alias -> (provider, real model, $ in, $ out) for ENABLED models; ALL_MODELS also holds disabled ones.
# Refreshed from the database on every connection, so a change on the models page applies to the next request.
MODELS = {a: (p, m, pi, po) for a, _, p, m, pi, po in DEFAULT_MODELS}
ALL_MODELS = dict(MODELS)
# alias -> {"price_cached": $ per 1M tokens read back from the provider's cache, "fallback": backup alias or None}
MODEL_EXTRA = {a: {"price_cached": pi * 0.1, "fallback": None} for a, _, _, _, pi, _ in DEFAULT_MODELS}
RETRYABLE = {429, 500, 502, 503, 504, 529}  # provider overloaded or down: worth trying the backup model
_migrated = False
MODEL_ALIAS = __import__("re").compile(r"^[a-z0-9][a-z0-9._-]{1,39}$")

SCHEMA = """
create table if not exists teams(name text primary key, budget real not null default 0, spent real not null default 0, month text);
create table if not exists accounts(
    name text primary key, team text not null default '', models text not null, budget real not null,
    spent real not null default 0, rpm int not null default 0, month text,
    pw_hash text, key_hash text unique, key_prefix text, failed int not null default 0, locked_until real not null default 0);
create table if not exists sessions(token_hash text primary key, name text not null, expires real not null);
create table if not exists logs(ts real, name text, team text, model text, tokens_in int, tokens_out int, cost real, request text, response text);
create index if not exists logs_ts on logs(ts);
create table if not exists conversations(id text primary key, name text not null, title text, updated real, messages text);
create table if not exists audit(ts real, action text, detail text);
create table if not exists models(alias text primary key, label text not null default '', provider text not null, model text not null,
    price_in real not null, price_out real not null, enabled int not null default 1, created real);
create table if not exists settings(key text primary key, value text);
create table if not exists blocked_requests(ts real, name text, team text, reason text, model text, request_id text, excerpt text);
create index if not exists blocked_requests_ts on blocked_requests(ts);
create index if not exists logs_name_ts on logs(name, ts);
"""


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA + sources.SCHEMA + security.SCHEMA)
    migrate(c)
    # monthly budgets: first touch in a new month zeroes spending (history stays in logs)
    month = time.strftime("%Y-%m")
    with c:
        c.execute("update accounts set spent = 0, month = ? where month is not ?", (month, month))
        c.execute("update teams set spent = 0, month = ? where month is not ?", (month, month))
        if not c.execute("select 1 from models limit 1").fetchone():
            c.executemany("insert into models(alias, label, provider, model, price_in, price_out, created) values (?,?,?,?,?,?,?)",
                          [(*m, time.time() + i / 1000) for i, m in enumerate(DEFAULT_MODELS)])
            c.execute("insert or ignore into settings values ('default_model', 'fast')")
            c.execute("update models set price_cached = round(price_in * 0.1, 6)")
    refresh_models(c)
    return c


_migrate_lock = threading.Lock()


def migrate(c):
    """Columns and tables added after the first release, the data key, and one-time rewrites; runs once per process.
    Data is never deleted: columns are only added, and before any rewrite of existing rows the whole database is
    copied to backups/ next to it."""
    global _migrated, _aead
    with _migrate_lock:
        if _migrated:
            return
        for table, col in (("models", "price_cached real"), ("models", "fallback text"), ("logs", "cache_read int not null default 0"),
                           ("logs", "cache_write int not null default 0"), ("logs", "note text"), ("sources", "config text"),
                           ("logs", "request_id text"), ("accounts", "key_expires real"), ("accounts", "key_created real"),
                           ("accounts", "daily_tokens int not null default 0"),
                           ("audit", "seq int"), ("audit", "prev_hash text"), ("audit", "hash text"),
                           # archive instead of delete: when the item was archived, NULL = in use
                           *((t, "archived real") for t in ("accounts", "teams", "models", "sources", "docs", "conversations"))):
            try:
                c.execute(f"alter table {table} add column {col}")
            except sqlite3.OperationalError:
                pass  # already there
        with c:
            c.execute("update models set price_cached = round(price_in * 0.1, 6) where price_cached is null")
            c.execute("update accounts set key_created = ? where key_hash is not null and key_created is null", (time.time(),))
        _aead = load_key(c, DB)
        pending = [name for name, needed in (("encrypt", plaintext_left(c)), ("audit-chain", audit_unchained(c))) if needed]
        if pending:
            backup(c, "+".join(pending))
            encrypt_existing(c)
            chain_audit(c)
        _migrated = True


# --- encryption at rest: questions, answers, saved chats and stored secrets ---
# AES-256-GCM. Each value is stored as "enc1:" + base64(12-byte nonce + ciphertext + tag); values without the prefix are
# older plaintext rows, which the one-time migration encrypts. The document search index (chunks) stays plaintext:
# full-text search can't search encrypted text.
ENC = "enc1:"
KEY_CHECK = "firegate-data-key"
_aead = None
ENCRYPTED = {"logs": ("request", "response"), "conversations": ("title", "messages"), "sources": ("config",),
             "blocked_requests": ("excerpt",)}


class DataKeyError(RuntimeError):
    pass


def encrypt(s):
    if not isinstance(s, str) or s == "":
        return s
    nonce = os.urandom(12)
    return ENC + base64.urlsafe_b64encode(nonce + _aead.encrypt(nonce, s.encode(), None)).decode()


def decrypt(s):
    if not isinstance(s, str) or not s.startswith(ENC):
        return s  # older plaintext row
    try:
        raw = base64.urlsafe_b64decode(s[len(ENC):])
        return _aead.decrypt(raw[:12], raw[12:], None).decode()
    except (ValueError, InvalidTag):
        return "[cannot decrypt: wrong FIREGATE_DATA_KEY]"


def key_path(db_path):
    return os.path.abspath(db_path) + ".key"


def load_key(c, db_path):
    """The data key: FIREGATE_DATA_KEY, else the key file next to the database, else a new key written there. Refuses
    (DataKeyError) when encrypted data exists but no key is found, or the key doesn't match: a new key could never
    read the old data, so starting would only bury it."""
    env, path = os.environ.get("FIREGATE_DATA_KEY", "").strip(), key_path(db_path)
    check = setting(c, "data_key_check")
    if env:
        raw = env
    elif os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            raw = f.read().strip()
    elif check or c.execute("select 1 from logs where request like 'enc1:%' or response like 'enc1:%' limit 1").fetchone():
        raise DataKeyError(f"The database {os.path.abspath(db_path)} holds encrypted data, but there is no key: FIREGATE_DATA_KEY "
                           f"is empty and {path} is missing. Set FIREGATE_DATA_KEY or put the key file back. Refusing to "
                           "start: a new key could never read the existing questions and answers.")
    else:
        raw = base64.urlsafe_b64encode(os.urandom(32)).decode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # owner-only where the OS supports it
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(raw + "\n")
        print("\n" + "!" * 78 + f"\nNEW DATA ENCRYPTION KEY created: {path}\nBACK IT UP NOW, somewhere other than this server's "
              "disk. Without it the saved questions,\nanswers and chats can never be read again. Or move it into the "
              "FIREGATE_DATA_KEY setting.\n" + "!" * 78 + "\n", flush=True)
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except ValueError:
        key = b""
    if len(key) != 32:
        raise DataKeyError("FIREGATE_DATA_KEY must be 32 random bytes in URL-safe base64, for example the output of: "
                           "python -c \"import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\"")
    aead = AESGCM(key)
    global _aead
    old, _aead = _aead, aead
    try:
        if check:
            if decrypt(check) != KEY_CHECK:
                raise DataKeyError("FIREGATE_DATA_KEY (or the key file) is not the key this database was encrypted with. "
                                   "Refusing to start; put back the original key.")
        else:
            with c:
                c.execute("insert into settings values ('data_key_check', ?)", (encrypt(KEY_CHECK),))
    finally:
        _aead = old
    return aead


def _plain_where(cols):
    return " or ".join(f"({col} is not null and {col} != '' and {col} not like 'enc1:%')" for col in cols)


def plaintext_left(c):
    return any(c.execute(f"select 1 from {t} where {_plain_where(cols)} limit 1").fetchone() for t, cols in ENCRYPTED.items())


def encrypt_existing(c):
    """One-time: encrypt rows written before encryption existed, in batches (an interrupted run just continues)."""
    for table, cols in ENCRYPTED.items():
        while True:
            rows = c.execute(f"select rowid, {', '.join(cols)} from {table} where {_plain_where(cols)} limit 2000").fetchall()
            if not rows:
                break
            with c:
                c.executemany(f"update {table} set {', '.join(col + ' = ?' for col in cols)} where rowid = ?",
                              [(*[v if not isinstance(v, str) or v.startswith(ENC) else encrypt(v) for v in r[1:]], r[0]) for r in rows])


def backup(c, label):
    """Consistent copy of the whole database (SQLite backup API) to backups/ in the database's own folder."""
    folder = os.path.join(os.path.dirname(os.path.abspath(DB)), "backups")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{os.path.splitext(os.path.basename(DB))[0]}-before-{label}-{time.strftime('%Y%m%d-%H%M%S')}.db")
    dst = sqlite3.connect(path)
    try:
        c.backup(dst)
    finally:
        dst.close()
    print(f"database backed up before migration ({label}): {path}", flush=True)
    return path


# --- tamper-evident change log: each row's hash covers the previous row's hash ---

def audit_hash(prev, ts, action, detail):
    return hashlib.sha256(f"{prev}{float(ts)!r}{action}{detail}".encode()).hexdigest()


def audit_unchained(c):
    """True when the change log has rows but no chain yet (first start after the upgrade)."""
    return bool(c.execute("select 1 from audit limit 1").fetchone()) and not c.execute(
        "select 1 from audit where hash is not null limit 1").fetchone()


def chain_audit(c):
    """One-time: chain the existing rows in time order. Their content is not changed."""
    if not audit_unchained(c):
        return
    prev, seq = "", 0
    with c:
        for r in c.execute("select rowid, ts, action, detail from audit order by ts, rowid").fetchall():
            seq += 1
            h = audit_hash(prev, r["ts"], r["action"], r["detail"])
            c.execute("update audit set seq = ?, prev_hash = ?, hash = ? where rowid = ?", (seq, prev, h, r["rowid"]))
            prev = h
        c.execute("insert into settings values ('audit_head', ?) on conflict(key) do update set value = excluded.value", (f"{seq}:{prev}",))


def verify_audit(c):
    """Walk the chain. A row edited, removed or added outside the gateway breaks it; first_bad says where."""
    rows = c.execute("select seq, ts, action, detail, prev_hash, hash from audit order by seq is null, seq, rowid").fetchall()
    prev = ""
    for i, r in enumerate(rows):
        if r["seq"] != i + 1 or r["prev_hash"] != prev or r["hash"] != audit_hash(prev, r["ts"], r["action"], r["detail"]):
            return {"ok": False, "rows": len(rows), "first_bad": {"seq": i + 1, "ts": r["ts"], "action": r["action"]}}
        prev = r["hash"]
    head = setting(c, "audit_head")
    if (head or rows) and head != f"{len(rows)}:{prev}":  # rows removed from the end
        return {"ok": False, "rows": len(rows), "first_bad": {"seq": len(rows) + 1, "ts": None, "action": None}}
    return {"ok": True, "rows": len(rows), "first_bad": None}


def setting(c, key, default=None):
    row = c.execute("select value from settings where key = ?", (key,)).fetchone()
    return row[0] if row and row[0] is not None else default


def refresh_models(c):
    global MODELS, ALL_MODELS, MODEL_EXTRA
    rows = c.execute("select alias, provider, model, price_in, price_out, enabled, price_cached, fallback from models"
                     " where archived is null order by created, alias").fetchall()
    ALL_MODELS = {r["alias"]: (r["provider"], r["model"], r["price_in"], r["price_out"]) for r in rows}
    MODEL_EXTRA = {r["alias"]: {"price_cached": r["price_cached"] if r["price_cached"] is not None else r["price_in"] * 0.1,
                                "fallback": r["fallback"] or None} for r in rows}
    MODELS = {r["alias"]: ALL_MODELS[r["alias"]] for r in rows if r["enabled"]}


def default_model(c):
    row = c.execute("select value from settings where key = 'default_model'").fetchone()
    return row[0] if row and row[0] in MODELS else next(iter(MODELS), None)


def audit(c, action, detail, ts=None):
    ts = time.time() if ts is None else ts
    d = json.dumps(detail, ensure_ascii=False)
    # insert first: that takes the database's write lock, so two changes can't both chain onto the same previous row
    rowid = c.execute("insert into audit(ts, action, detail) values (?,?,?)", (ts, action, d)).lastrowid
    last = c.execute("select seq, hash from audit where seq is not null order by seq desc limit 1").fetchone()
    seq, prev = (last[0] + 1, last[1]) if last else (1, "")
    h = audit_hash(prev, ts, action, d)
    c.execute("update audit set seq = ?, prev_hash = ?, hash = ? where rowid = ?", (seq, prev, h, rowid))
    c.execute("insert into settings values ('audit_head', ?) on conflict(key) do update set value = excluded.value", (f"{seq}:{h}",))


# --- archive: nothing is deleted. An archived row stays in the database, out of every list and out of use, until restored ---
# kind -> (table, key column)
ARCHIVE = {"account": ("accounts", "name"), "team": ("teams", "name"), "model": ("models", "alias"), "source": ("sources", "name")}


def not_archived(c, kind, name):
    """Refuses a new item whose name belongs to an archived one: restoring it is the way back."""
    table, col = ARCHIVE[kind]
    if c.execute(f"select 1 from {table} where {col} = ? and archived is not null", (name,)).fetchone():
        raise ValueError(f"name '{name}' is in the archive; restore it instead")


def archive_list(c):
    return {"accounts": [dict(r) for r in c.execute("select name, team, archived from accounts where archived is not null order by archived desc")],
            "teams": [dict(r) for r in c.execute("select name, archived from teams where archived is not null order by archived desc")],
            "models": [dict(r) for r in c.execute("select alias, label, archived from models where archived is not null order by archived desc")],
            "sources": [dict(r) for r in c.execute("select name, kind, archived from sources where archived is not null order by archived desc")],
            "docs": [dict(r) for r in c.execute("select d.id, d.source, d.title, d.archived from docs d join sources s on s.name = d.source"
                                                " where d.archived is not null and s.archived is null order by d.archived desc")]}


def set_archived(c, kind, body, name, restore):
    """Archive (or restore) one item. Returns (http status, reply body); writes the change log."""
    now = None if restore else time.time()
    if kind == "doc":
        doc_id = int(body.get("id"))
        title = c.execute("select title from docs where id = ? and source = ?", (doc_id, name)).fetchone()
        n = c.execute(f"update docs set archived = ? where id = ? and source = ? and archived is {'not ' if restore else ''}null",
                      (now, doc_id, name)).rowcount
        detail = {"kind": kind, "name": name, "title": title[0] if title else None, "id": doc_id}
    elif kind in ARCHIVE:
        table, col = ARCHIVE[kind]
        if not c.execute(f"select 1 from {table} where {col} = ? and archived is {'not ' if restore else ''}null", (name,)).fetchone():
            return 404, {"error": f"no {kind} '{name}'" + (" in the archive" if restore else "")}
        if not restore and kind == "team" and c.execute("select 1 from accounts where team = ? and archived is null", (name,)).fetchone():
            raise ValueError("the team still has people; move them to another team first")
        if not restore and kind == "model":
            users = c.execute("select count(*) from accounts where archived is null and ',' || models || ',' like ?", (f"%,{name},%",)).fetchone()[0]
            if users:
                raise ValueError(f"{users} accounts still use this model; remove it from them or turn it off instead")
            if setting(c, "default_model") == name:
                raise ValueError("this is the default model; choose another default first")
        if restore and kind == "account":
            team = c.execute("select team from accounts where name = ?", (name,)).fetchone()[0]
            if team and c.execute("select 1 from teams where name = ? and archived is not null", (team,)).fetchone():
                raise ValueError(f"the account's team '{team}' is in the archive; restore the team first")
        n = c.execute(f"update {table} set archived = ? where {col} = ?", (now, name)).rowcount
        if kind == "account":
            c.execute("delete from sessions where name = ?", (name,))  # login tokens, not data: archived means logged out
        detail = {"kind": kind, "name": name}
    else:
        raise ValueError("unknown kind")
    if not n:
        return 404, {"error": "not found"}
    audit(c, "restore" if restore else "archive", detail)
    return 200, {"ok": True}


# --- secrets: only hashes are stored ---

def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def hash_password(pw):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def check_password(pw, stored):
    try:
        _, rounds, salt, digest = stored.split("$")
        return secrets.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(rounds)).hex(), digest)
    except (AttributeError, ValueError):
        return False


DUMMY_HASH = hash_password(secrets.token_hex(16))


def new_key(c, name):
    """Give the account a fresh gateway key; the old one stops working. Returns the key (shown once)."""
    key = "gw-" + secrets.token_urlsafe(32)
    c.execute("update accounts set key_hash = ?, key_prefix = ?, key_created = ? where name = ?", (sha(key), key[:10], time.time(), name))
    return key


# --- validation ---

def account_fields(c, body, partial):
    """Budget/rpm/models/team from an admin request, validated. partial=True only checks fields present."""
    out = {}
    if "budget" in body or not partial:
        out["budget"] = float(body.get("budget"))
        if out["budget"] < 0:
            raise ValueError("budget must be >= 0")
    if "rpm" in body:
        out["rpm"] = int(body["rpm"] or 0)
        if out["rpm"] < 0:
            raise ValueError("rpm must be >= 0")
    if "models" in body or not partial:
        models = body.get("models") or []
        if not models or any(m not in ALL_MODELS for m in models):
            raise ValueError("pick at least one known model")
        out["models"] = ",".join(models)
    if "team" in body:
        out["team"] = str(body["team"] or "")
        if out["team"] and not c.execute("select 1 from teams where name = ? and archived is null", (out["team"],)).fetchone():
            raise ValueError(f"team '{out['team']}' does not exist")
    if "daily_tokens" in body:
        out["daily_tokens"] = int(body["daily_tokens"] or 0)
        if out["daily_tokens"] < 0:
            raise ValueError("daily tokens must be >= 0")
    if "key_expires" in body:  # a date (the key works until the end of that day), or empty for no expiry
        v = str(body["key_expires"] or "").strip()
        try:
            out["key_expires"] = time.mktime((*map(int, v.split("-")), 23, 59, 59, 0, 0, -1)) if v else None
        except (ValueError, TypeError):
            raise ValueError("key expiry must be a date like 2026-12-31")
    return out  # only these fields: anything else in the request (spent, key_hash, pw_hash...) is ignored


def check_new_password(pw):
    if not isinstance(pw, str) or len(pw) < 8:
        raise ValueError("password must be at least 8 characters")
    return pw


# --- redaction: sensitive values never leave the building and never reach the log ---

def _luhn(digits):
    total = 0
    for i, d in enumerate(reversed(digits)):
        d = int(d) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _il_id(digits):  # Israeli ID check digit
    return sum(sum(divmod(int(d) * (1 + i % 2), 10)) for i, d in enumerate(digits)) % 10 == 0


_CARD = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_ID = re.compile(r"\b\d{9}\b")
# access keys: provider and gateway keys (prefix + separator), Google keys, AWS key ids, private-key blocks
_SECRET = re.compile(r"\b(?:(?:sk|gw|ghp|gho|ghs|github_pat|glpat|hf|xox[bpoas])[-_]|AIza)[-_A-Za-z0-9]{16,}|\bAKIA[0-9A-Z]{16}\b"
                     r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)")
_IBAN = re.compile(r"\bIL\d{2}(?:[ -]?\d{4}){4}[ -]?\d{3}\b")
_PHONE = re.compile(r"(?<![\w+])(?:\+972[- ]?|0)(?:5\d|7\d|[2-4689])[- ]?\d{3}[- ]?\d{4}\b")  # Israeli mobiles and landlines
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
# bank accounts and passports only next to a label saying so: bare numbers are too often something else
_BANK = re.compile(r"((?:חשבון\s+בנק|מס(?:פר|')\s+חשבון\s+בנק|סניף\s+\d{3}\s*,?\s*חשבון|bank\s+account(?:\s+(?:no\.?|number|#))?)"
                   r"\s*[:#]?\s*)(?:\d{2,3}[-/ ]\d{3}[-/ ])?\d{4,9}\b", re.I)
_PASSPORT = re.compile(r"((?:passport|דרכון)[^\d\n]{0,20}?)[A-Z]?\d{7,9}\b", re.I)


def redact_text(s):
    s = _SECRET.sub("[REDACTED_SECRET]", s)
    s = _IBAN.sub("[REDACTED_IBAN]", s)
    s = _CARD.sub(lambda m: "[REDACTED_CARD]" if _luhn(re.sub(r"\D", "", m[0])) else m[0], s)
    s = _ID.sub(lambda m: "[REDACTED_ID]" if _il_id(m[0]) else m[0], s)
    s = _PHONE.sub("[REDACTED_PHONE]", s)
    s = _EMAIL.sub("[REDACTED_EMAIL]", s)
    s = _BANK.sub(lambda m: m[1] + "[REDACTED_BANK]", s)
    return _PASSPORT.sub(lambda m: m[1] + "[REDACTED_PASSPORT]", s)


def redact(obj, fn=None):
    # ponytail: one policy for every account; add a per-account switch if a team must send IDs to a model
    fn = fn or redact_text
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [redact(v, fn) for v in obj]
    if isinstance(obj, dict):
        return {k: redact(v, fn) for k, v in obj.items()}
    return obj


def mask_answer(s):
    """Answers: only access keys and credentials are masked (an answer may rightly contain an email or a phone)."""
    return _SECRET.sub("[REDACTED_SECRET]", s)


class AnswerMasker:
    """Masks keys in a streamed answer. Text is held back until whitespace (a key never contains any), and a
    private-key block until its end line, so a key split across pieces is still caught."""
    def __init__(self):
        self.buf, self.count = "", 0

    def _out(self, s):
        m = mask_answer(s)
        self.count += m.count("[REDACTED_SECRET]") - s.count("[REDACTED_SECRET]")
        return m

    def feed(self, piece):
        self.buf += piece
        if "-----BEGIN" in self.buf and "-----END" not in self.buf.split("-----BEGIN")[-1]:
            return ""
        cut = max(self.buf.rfind(" "), self.buf.rfind("\n"), self.buf.rfind("\t")) + 1
        out, self.buf = self.buf[:cut], self.buf[cut:]
        return self._out(out)

    def flush(self):
        out, self.buf = self.buf, ""
        return self._out(out)


def leaked(text, secret, n=60):
    """Mask every run of n+ characters of secret (the gateway's own instructions) that appears word for word in text.
    Returns (text, how many runs)."""
    found, i = 0, 0
    while i + n <= len(secret):
        if secret[i:i + n] in text:
            j = i + n
            while j < len(secret) and secret[i:j + 1] in text:
                j += 1
            text, found, i = text.replace(secret[i:j], "[REDACTED_SYSTEM_PROMPT]"), found + 1, j
        else:
            i += 1
    return text, found


def masked(before, after):
    """How many sensitive values redaction replaced between two JSON dumps."""
    return after.count("[REDACTED_") - before.count("[REDACTED_")


# --- rate limit: requests per minute per account, in memory ---
_hits = collections.defaultdict(collections.deque)
_hits_lock = threading.Lock()


def rate_ok(name, rpm):
    # ponytail: per-process memory, resets on restart; move to the DB if running several gateway processes
    if not rpm:
        return True
    now = time.time()
    with _hits_lock:
        q = _hits[name]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= rpm:
            return False
        q.append(now)
        return True


# --- questions in progress per account, and wrong passwords per client address (memory) ---
# ponytail: per-process memory, resets on restart; move to the DB if running several gateway processes
_inflight = collections.Counter()
_login_fails = collections.defaultdict(collections.deque)


def inflight_enter(name):
    with _hits_lock:
        if _inflight[name] >= MAX_CONCURRENT:
            return False
        _inflight[name] += 1
        return True


def inflight_leave(name):
    with _hits_lock:
        _inflight[name] -= 1


def login_fails(ip, add=False):
    """Wrong passwords from this address in the last LOGIN_IP_MINUTES (after recording one more if add)."""
    now = time.time()
    with _hits_lock:
        q = _login_fails[ip]
        while q and q[0] < now - LOGIN_IP_MINUTES * 60:
            q.popleft()
        if add:
            q.append(now)
        return len(q)


# --- budgets ---

def day_start(t=None):
    lt = time.localtime(t)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def authorize(c, acct, alias):
    """None if the account may call this model now, else (http status, message, reason code)."""
    if alias in ALL_MODELS and alias not in MODELS and alias in acct["models"].split(","):
        return 403, f"model '{alias}' is turned off by the administrator", "model-off"
    if alias not in MODELS or alias not in acct["models"].split(","):
        return 403, f"model '{alias}' not allowed", "model-not-allowed"
    # ponytail: check-then-charge, concurrent requests can overshoot a budget by one request each
    if acct["spent"] >= acct["budget"]:
        return 402, "personal monthly budget exhausted", "budget"
    team = c.execute("select budget, spent from teams where name = ?", (acct["team"],)).fetchone()
    if team and team["budget"] and team["spent"] >= team["budget"]:
        return 402, "team monthly budget exhausted", "team-budget"
    if acct["daily_tokens"] and c.execute("select coalesce(sum(tokens_in + tokens_out), 0) from logs where name = ? and ts >= ?",
                                          (acct["name"], day_start())).fetchone()[0] >= acct["daily_tokens"]:
        return 429, "daily token quota reached", "daily-quota"
    if not rate_ok(acct["name"], acct["rpm"]):
        return 429, f"rate limit: {acct['rpm']} requests per minute", "rate-limit"
    return None


def policy(c):
    """(injection policy: block|log, sensitive-data policy: mask|block|log), set on the admin security page."""
    inj, sens = setting(c, "policy_injection", "block"), setting(c, "policy_sensitive", "mask")
    return inj if inj in ("block", "log") else "block", sens if sens in ("mask", "block", "log") else "mask"


def last_user_text(messages):
    """Text of the newest message if the user wrote it (string or a list of text parts)."""
    m = messages[-1] if isinstance(messages, list) and messages else None
    if not isinstance(m, dict) or m.get("role") != "user":
        return ""
    content = m.get("content")
    if isinstance(content, list):
        return "\n".join(p["text"] for p in content if isinstance(p, dict) and isinstance(p.get("text"), str))
    return content if isinstance(content, str) else ""


def check_spike(c, name):
    """Security event (once per account per day) when the last hour cost more than max($5, 5x the account's average
    hour over the 7 days before it)."""
    now = time.time()
    hour = c.execute("select coalesce(sum(cost), 0) from logs where name = ? and ts >= ?", (name, now - 3600)).fetchone()[0]
    if hour <= SPIKE_MIN:
        return
    week = c.execute("select coalesce(sum(cost), 0) from logs where name = ? and ts >= ? and ts < ?",
                     (name, now - 7 * 86400 - 3600, now - 3600)).fetchone()[0]
    if hour > max(SPIKE_MIN, SPIKE_FACTOR * week / 168) and not c.execute(
            "select 1 from security_events where kind = 'cost-spike' and name = ? and ts >= ?", (name, day_start())).fetchone():
        security.event(c, "cost-spike", name, {"hour": round(hour, 4), "average": round(week / 168, 4)})


def new_usage():
    return {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}


def price_usage(price_in, price_out, price_cached, u):
    """Dollar cost of one call. Writing to the provider's cache costs 1.25x input; reading back costs price_cached."""
    return (u["in"] * price_in + u["cache_write"] * price_in * 1.25 + u["cache_read"] * price_cached + u["out"] * price_out) / 1e6


def log_call(c, name, team, model, u, cost, request, response, note="", request_id=None):
    c.execute("insert into logs(ts, name, team, model, tokens_in, tokens_out, cost, request, response, cache_read, cache_write, note,"
              " request_id) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (time.time(), name, team, model, u["in"] + u["cache_read"] + u["cache_write"], u["out"], cost, encrypt(request),
               encrypt(response), u["cache_read"], u["cache_write"], note or None, request_id))


def charge(c, acct, alias, u, request, response, note="", request_id=None):
    _, real, price_in, price_out = ALL_MODELS[alias]
    cost = price_usage(price_in, price_out, MODEL_EXTRA.get(alias, {}).get("price_cached", price_in * 0.1), u)
    with c:
        c.execute("update accounts set spent = spent + ? where name = ?", (cost, acct["name"]))
        c.execute("update teams set spent = spent + ? where name = ?", (cost, acct["team"]))
        log_call(c, acct["name"], acct["team"], real, u, cost, request, response, note, request_id)
        check_spike(c, acct["name"])
    if acct["spent"] < acct["budget"] * SOFT_LIMIT <= acct["spent"] + cost:
        print(f"WARNING: {acct['name']} passed {SOFT_LIMIT:.0%} of budget (${acct['budget']})", flush=True)
    return cost


def month_bounds(t=None):
    lt = time.localtime(t)
    start = time.mktime((lt.tm_year, lt.tm_mon, 1, 0, 0, 0, 0, 0, -1))
    y, m = (lt.tm_year + 1, 1) if lt.tm_mon == 12 else (lt.tm_year, lt.tm_mon + 1)
    return start, time.mktime((y, m, 1, 0, 0, 0, 0, 0, -1))


def forecast(spent, last_month):
    """Projected spend at month end, and a recommended monthly budget (20% headroom, rounded up to $5)."""
    # ponytail: straight-line projection from days elapsed; good enough until usage has strong weekly patterns
    start, end = month_bounds()
    elapsed = max(time.time() - start, 86400) / (end - start)
    projected = spent / min(elapsed, 1)
    base = max(projected, last_month)
    return round(projected, 4), (math.ceil(base * 1.2 / 5) * 5 if base > 0 else 0)


# --- calling providers ---

def read_usage(obj, provider, u):
    """Merge token counts from a response or stream event into u (see new_usage).
    Anthropic reports cache reads/writes separately from input; OpenAI-style APIs count cached tokens inside
    prompt_tokens, so they are moved out of "in" here to be priced at the cache rate."""
    for src in (obj.get("usage"), (obj.get("message") or {}).get("usage")):
        if not isinstance(src, dict):
            continue
        if provider == "anthropic":
            vals = {"in": src.get("input_tokens"), "out": src.get("output_tokens"),
                    "cache_read": src.get("cache_read_input_tokens"), "cache_write": src.get("cache_creation_input_tokens")}
        else:
            cached = (src.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            prompt = src.get("prompt_tokens")
            vals = {"in": None if prompt is None else prompt - cached, "out": src.get("completion_tokens"),
                    "cache_read": cached or None, "cache_write": None}
        for k, v in vals.items():
            if v is not None:
                u[k] = max(u[k], v)
    return u


def upstream(provider, body, on_line):
    """POST body to the provider. Streams call on_line(raw line, parsed event or None) per line.
    Returns (status, raw response bytes, usage). Raises URLError if unreachable."""
    _, url, auth, _ = PROVIDERS[provider]
    req = urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json", **auth})
    try:
        r = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.read(), new_usage()  # provider error: nothing to charge
    u = new_usage()
    with r:
        if not body.get("stream"):
            data = r.read()
            try:
                read_usage(json.loads(data), provider, u)
            except (ValueError, AttributeError):
                pass
            return r.status, data, u
        chunks = []
        for line in r:
            chunks.append(line)
            ev = None
            if line.startswith(b"data:"):
                try:
                    ev = json.loads(line[5:])
                    read_usage(ev, provider, u)
                except (ValueError, AttributeError):
                    ev = None  # "[DONE]" and other non-JSON lines
            on_line(line, ev)
        return r.status, b"".join(chunks), u


# --- meaning vectors for document search (OpenAI or Gemini embeddings; Anthropic has none) ---
# provider -> (env var for model, default model, $ per 1M tokens). Checked 2026-10-05.
EMBED_MODELS = {"openai": ("OPENAI_EMBED_MODEL", "text-embedding-3-small", 0.02),
                "gemini": ("GEMINI_EMBED_MODEL", "gemini-embedding-001", 0.15)}


def embed_provider():
    """Which provider computes meaning vectors: EMBEDDINGS=openai|gemini|off, default the first one with a key."""
    choice = os.environ.get("EMBEDDINGS", "auto").strip().lower()
    for p in (("openai", "gemini") if choice in ("", "auto") else (choice,)):
        if p in EMBED_MODELS and PROVIDERS[p][2]["authorization"].removeprefix("Bearer ").strip():
            return p
    return None


def embed_texts(c, texts):
    """Meaning vectors for texts, or None if no provider or the call failed. The cost is logged, charged to nobody."""
    p = embed_provider()
    if not p or not texts:
        return None
    env, default, price = EMBED_MODELS[p]
    model = os.environ.get(env, default)
    url = PROVIDERS[p][1].rsplit("/chat/completions", 1)[0] + "/embeddings"
    vecs, tokens = [], 0
    try:
        for i in range(0, len(texts), 64):
            req = urllib.request.Request(url, json.dumps({"model": model, "input": [t[:8000] for t in texts[i:i + 64]]}).encode(),
                                         {"content-type": "application/json", **PROVIDERS[p][2]})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            vecs += [x["embedding"] for x in sorted(d["data"], key=lambda x: x["index"])]
            tokens += (d.get("usage") or {}).get("prompt_tokens") or 0
    except (OSError, ValueError, KeyError) as e:  # OSError covers unreachable and dropped connections
        print(f"embeddings unavailable ({p}): {e}", flush=True)
        return None
    args = (c, "(אינדקס מסמכים)", "", model, {**new_usage(), "in": tokens}, tokens * price / 1e6, "", f"{len(texts)} texts")
    if c.in_transaction:  # inside an admin change: saved together with it
        log_call(*args)
    else:  # during a chat question: save now, so the open write doesn't block other requests
        with c:
            log_call(*args)
    return vecs


sources.EMBED = embed_texts
sources.ENCRYPT = encrypt


# --- MCP knowledge sources ---
MCP_RESULT_CHARS = 3000  # per source per question
MCP_MAX_RESOURCES = 300


def mcp_config(row):
    return load_config(row["config"])


def load_config(raw):
    """A source's settings (stored encrypted: they hold the MCP server's token)."""
    try:
        cfg = json.loads(decrypt(raw) or "{}")
        return cfg if isinstance(cfg, dict) else {}
    except ValueError:
        return {}


MCP_NAME = re.compile(r"^[A-Za-z0-9_.:/-]{1,64}$")


def mcp_search(c, names, question, who, request_id=None):
    """Live search: call the configured tool of each chosen MCP source with the question. Returns [(source, title, text)].
    Only that one tool, only with that one argument, and only if the server doesn't mark it as changing data.
    A failing server is skipped (and logged), never allowed to break the chat. The caller screens the text."""
    hits = []
    marks = ",".join("?" * len(names))
    for row in c.execute(f"select * from sources where kind = 'mcp' and name in ({marks})", names).fetchall() if names else []:
        cfg = mcp_config(row)
        tool, arg = str(cfg.get("tool") or ""), str(cfg.get("arg") or "query")
        if cfg.get("mode") != "search" or not MCP_NAME.match(tool) or not MCP_NAME.match(arg):
            continue
        try:
            client = mcp.Client(row["path"], cfg.get("token", ""))
            client.connect()
            refused = mcp.check_tool(client.tools(), tool, arg)
            if refused:
                with c:
                    security.event(c, "mcp-tool-refused", row["name"], {"file": f"MCP: {tool}", "reason": refused, "user": who,
                                                                        "request_id": request_id})
                continue
            text = client.run_tool(tool, {arg: question})[:MCP_RESULT_CHARS]
        except mcp.MCPError as e:
            print(f"MCP source {row['name']} failed: {e}", flush=True)
            continue
        if text.strip():
            hits.append((row["name"], tool, redact_text(text)))
    return hits


def mcp_sync(c, row):
    """Copy the server's text resources (and PDF/Word blobs) into the document index; resources that are gone are archived.
    Returns (indexed, skipped, flagged, archived titles)."""
    client = mcp.Client(row["path"], mcp_config(row).get("token", ""))
    client.connect()
    seen, skipped, flagged = set(), 0, []
    for res in client.resources()[:MCP_MAX_RESOURCES]:
        title = str(res.get("name") or res.get("uri"))[:200]
        text = ""
        for part in client.read(res["uri"]):
            if part.get("text"):
                text += part["text"] + "\n\n"
            elif part.get("blob") and part.get("mimeType") in ("application/pdf",
                                                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
                ext = ".pdf" if part["mimeType"] == "application/pdf" else ".docx"
                try:
                    text += sources.extract_text(title + ext, base64.b64decode(part["blob"])) + "\n\n"
                except ValueError:
                    pass
        if not text.strip():
            skipped += 1
            continue
        found = security.scan(text)
        if found:
            flagged.append((title, found))
            continue
        sources.add_doc(c, row["name"], title, text.strip())
        seen.add(title)
    gone = sources.archive_missing(c, row["name"], seen)
    c.execute("update sources set synced = ? where name = ?", (time.time(), row["name"]))
    return len(seen), skipped, flagged, gone


def fallback_for(alias, path=None):
    """The backup model for alias, if it is on and (for app calls) speaks the same request format."""
    fb = MODEL_EXTRA.get(alias, {}).get("fallback")
    if fb and fb != alias and fb in MODELS and (path is None or PROVIDERS[MODELS[fb][0]][0] == path):
        return fb
    return None


_HEAVY = __import__("re").compile(
    r"```|\b(code|function|debug|refactor|analy[sz]e|compare|strategy|architecture|contract|legal|step by step|why)\b"
    r"|קוד|פונקצי|באג|נתח|ניתוח|השווה|השוואה|אסטרטגי|ארכיטקטור|חוזה|משפטי|שלב אחר שלב|למה|תכנן|תוכנית", __import__("re").I)


def route_auto(c, acct, messages):
    """Pick the cheap or the strong model for one question. Returns (alias, reason) or (None, error)."""
    cheap, strong = setting(c, "auto_cheap", "fast"), setting(c, "auto_strong", "smart")
    allowed = [m for m in acct["models"].split(",") if m in MODELS]
    last = messages[-1]["content"]
    total = sum(len(m["content"]) for m in messages)
    if len(last) > 1200:
        want, reason = strong, "שאלה ארוכה"
    elif _HEAVY.search(last):
        want, reason = strong, "קוד, ניתוח או השוואה"
    elif total > 8000 or len(messages) > 12:
        want, reason = strong, "שיחה ארוכה"
    else:
        want, reason = cheap, "שאלה קצרה ופשוטה"
    for a in (want, cheap, strong):
        if a in allowed:
            return a, reason if a == want else f"{reason} (המודל המתאים לא זמין לך)"
    return None, "no model available for automatic choice"


def delta_text(provider, ev):
    """The text piece inside one stream event, if any."""
    if not isinstance(ev, dict):
        return None
    if provider == "anthropic":
        return (ev.get("delta") or {}).get("text") if ev.get("type") == "content_block_delta" else None
    choices = ev.get("choices") or []
    return (choices[0].get("delta") or {}).get("content") if choices else None


class TooLarge(Exception):
    pass


def trusted_proxy(ip):
    try:
        ip = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(ip in net for net in TRUSTED_PROXIES if net.version == ip.version)


PROVIDER_PATHS = {p[0] for p in PROVIDERS.values()}


class Handler(BaseHTTPRequestHandler):
    timeout = 60  # a client that stops sending mid-request is dropped instead of holding a thread forever
    rid = None
    # ---------- helpers ----------
    def send_header(self, keyword, value):
        # every header goes out through here: a line break in a value would start a header (or a body) of its own
        super().send_header(keyword, re.sub(r"[^\t\x20-\x7e\xa0-\xff]", "", str(value)))

    def end_headers(self):
        if self.rid:
            self.send_header("x-request-id", self.rid)
        super().end_headers()

    def log_message(self, fmt, *args):
        # method, path without the query string, status: never bodies, keys or cookies
        line = (getattr(self, "requestline", "") or "-").split(" ")
        path = line[1].split("?")[0][:200] if len(line) > 1 else ""
        status = args[1] if fmt.startswith('"%s" %s') and len(args) > 1 else "-"
        try:
            ip = self.client_ip()
        except (AttributeError, ValueError):
            ip = self.client_address[0]
        sys.stderr.write(f"{ip} {self.log_date_time_string()} {line[0][:10]} {path} {status} {self.rid or ''}\n")

    def start(self):
        """Per request: a trace id (the client's own if it looks sane) and a check of how the body is framed."""
        given = self.headers.get("x-request-id") or ""
        self.rid = given if REQUEST_ID.match(given) else uuid.uuid4().hex
        te, lengths = self.headers.get("transfer-encoding"), self.headers.get_all("content-length") or []
        # two ways of saying where the body ends is how "request smuggling" makes two servers disagree
        if te and lengths:
            return 400, "conflicting content-length and transfer-encoding"
        if te:
            return 400, "chunked request bodies are not supported; send content-length"
        if len(set(lengths)) > 1 or any(not v.strip().isdigit() for v in lengths):
            return 400, "invalid content-length"
        return None

    def reply(self, status, obj, headers=()):
        self.send_raw(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json", headers)

    def https(self):
        return trusted_proxy(self.client_address[0]) and self.headers.get("x-forwarded-proto") == "https"

    def send_raw(self, status, data, ctype, headers=()):
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("referrer-policy", "no-referrer")
        if self.https():
            self.send_header("strict-transport-security", "max-age=31536000")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def json_body(self, path):
        n = int(self.headers.get("content-length") or 0)
        if n > (MAX_BODY if path == "/admin/api/sources/upload" or path in PROVIDER_PATHS else MAX_REQUEST_BODY):
            raise TooLarge()
        body = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("body must be a JSON object")
        return body

    def client_ip(self):
        ip = self.client_address[0]
        # Behind Caddy the direct peer is Caddy; the real client is the right-most forwarded address that isn't
        # one of our own proxies. From anyone else the header is ignored: it's just text the sender typed.
        if not trusted_proxy(ip):
            return ip
        for hop in reversed((self.headers.get("x-forwarded-for") or "").split(",")):
            hop = hop.strip()
            try:
                ipaddress.ip_address(hop)
            except ValueError:
                break
            if not trusted_proxy(hop):
                return hop
            ip = hop
        return ip

    def event(self, c, kind, name, detail):
        security.event(c, kind, name, {**detail, "request_id": self.rid})

    def refuse(self, c, acct, status, message, reason, model=None, text=""):
        """Turn a request away, and remember it (with a masked, encrypted excerpt of the question at most)."""
        with c:
            c.execute("insert into blocked_requests values (?,?,?,?,?,?,?)",
                      (time.time(), acct["name"] if acct else "", acct["team"] if acct else "", reason,
                       model if isinstance(model, str) else None, self.rid, encrypt(redact_text(text)[:200]) if text else None))
        self.reply(status, {"error": message, "code": reason})

    def screen(self, c, acct, text, model):
        """The injection policy for the newest question. True if the request may continue; otherwise it was refused."""
        found = security.scan(text)
        blocked = bool(security.ATTACKS & set(found)) and policy(c)[0] == "block"
        if found:
            with c:
                self.event(c, "suspicious-prompt", acct["name"], {"found": found, "excerpt": encrypt(redact_text(text)[:200]),
                                                                  "action": "blocked" if blocked else "logged"})
        if blocked:
            self.refuse(c, acct, 403, "request blocked: possible prompt injection or jailbreak", "policy-injection", model, text)
        return not blocked

    def sensitive(self, c, acct, original, masked_obj, count, model, text):
        """The sensitive-data policy. Returns what to send on (masked or original), or None if refused."""
        if not count:
            return masked_obj
        mode = policy(c)[1]
        kind = {"mask": "sensitive-data-masked", "block": "sensitive-data-blocked", "log": "sensitive-data-logged"}[mode]
        with c:
            self.event(c, kind, acct["name"], {"count": count})
        if mode == "block":
            self.refuse(c, acct, 403, "request blocked: sensitive data", "policy-sensitive", model, text)
            return None
        return masked_obj if mode == "mask" else original

    def host_ok(self):
        host = (self.headers.get("host") or "").lower()
        host = host[1:host.find("]")] if host.startswith("[") else host.rsplit(":", 1)[0]
        if host == "localhost" or host in ALLOWED_HOSTS:
            return True
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return False

    def browser_post_ok(self):
        """Blocks other websites from making a visitor's browser post to us (CSRF): JSON only, from our own pages."""
        if self.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            return False  # a plain HTML form on another site can't send this content type
        origin = self.headers.get("origin")
        if origin and urllib.parse.urlsplit(origin).netloc.lower() != (self.headers.get("host") or "").lower():
            return False
        return self.headers.get("sec-fetch-site") in (None, "same-origin", "none")

    def blocked(self, kind, status, message):
        with db() as c:
            self.event(c, kind, "", {"path": self.path.split("?")[0], "ip": self.client_ip(),
                                     "host": self.headers.get("host"), "origin": self.headers.get("origin")})
        self.reply(status, {"error": message})

    def inside(self):
        if PUBLIC:
            return False
        try:
            return ipaddress.ip_address(self.client_ip()).is_private
        except ValueError:
            return False

    def open_ok(self):
        return OPEN_ACCESS and self.inside()

    def admin_ok(self):
        inside = self.inside()
        given = self.headers.get("x-admin-password", "").encode()
        if inside or (ADMIN_PASSWORD and secrets.compare_digest(given, ADMIN_PASSWORD.encode())):
            return True
        if given:  # a wrong password from outside is worth knowing about; a page load without one is not
            with db() as c:
                self.event(c, "admin-denied", "", {"ip": self.client_ip(), "path": self.path.split("?")[0]})
        self.reply(401, {"error": "admin is open only from the office network" if not ADMIN_PASSWORD else "wrong admin password"})
        return False

    def session_account(self, c):
        try:
            token = http.cookies.SimpleCookie(self.headers.get("cookie", "")).get("session")
        except http.cookies.CookieError:
            return None
        if not token:
            return None
        return c.execute("select a.* from sessions s join accounts a on a.name = s.name"
                         " where s.token_hash = ? and s.expires > ? and a.archived is null", (sha(token.value), time.time())).fetchone()

    def cookie(self, value, max_age):
        secure = "; Secure" if self.https() else ""
        return ("set-cookie", f"session={value}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}{secure}")

    # ---------- routing ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        bad = self.start()
        if bad:
            return self.reply(bad[0], {"error": bad[1]})
        if not self.host_ok():
            return self.blocked("bad-host", 421, "unknown host name; add it to ALLOWED_HOSTS")
        if path == "/health":
            return self.reply(200, {"ok": True, "version": VERSION})
        if path in PAGES:
            file, ctype = PAGES[path]
            with open(os.path.join(HERE, file), "rb") as f:
                text = ctype.startswith("text/")
                return self.send_raw(200, f.read(), ctype + ("; charset=utf-8" if text else ""),
                                     [("content-security-policy", CSP)] if text else [("cache-control", "max-age=31536000, immutable")])
        try:
            if path.startswith("/admin/api/"):
                if self.admin_ok():
                    self.admin_get(path)
                return
            if path.startswith("/api/"):
                return self.user_get(path)
        except (ValueError, KeyError, TypeError) as e:
            return self.reply(400, {"error": str(e)})
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        bad = self.start()
        if bad:
            return self.reply(bad[0], {"error": bad[1]})
        if not self.host_ok():
            return self.blocked("bad-host", 421, "unknown host name; add it to ALLOWED_HOSTS")
        # apps calling the provider paths authenticate with a key, which a hostile page can't attach
        if path not in PROVIDER_PATHS and not self.browser_post_ok():
            return self.blocked("cross-site-request", 403, "request must come from this site's own pages")
        try:
            if path.startswith("/admin/api/"):
                if self.admin_ok():
                    self.admin_post(path, self.json_body(path))
                return
            if path.startswith("/api/"):
                return self.user_post(path, self.json_body(path))
            if path in PROVIDER_PATHS:
                return self.proxy(path, self.json_body(path))
            self.reply(404, {"error": "not found"})
        except TooLarge:
            self.close_connection = True  # the unread body must not be taken for a next request
            self.reply(413, {"error": "request too large"})
        except (ValueError, KeyError, TypeError) as e:
            self.reply(400, {"error": str(e)})

    def call_with_backup(self, alias, build, on_line, started, path=None):
        """Call alias; if the provider fails before any answer was sent, try its backup model once.
        Returns (alias that answered, status, raw data, usage, note)."""
        note, last = "", None
        for a in (alias, fallback_for(alias, path)):
            if not a:
                continue
            self.current_alias = a
            try:
                status, data, u = upstream(MODELS[a][0], build(a), on_line)
            except urllib.error.URLError as e:
                status, data, u = 502, json.dumps({"error": f"provider unreachable: {e.reason}"}).encode(), new_usage()
            last = (a, status, data, u)
            if status < 400 or started or status not in RETRYABLE:
                break
            note = f"backup: {alias} failed ({status})"
        a, status, data, u = last
        return a, status, data, u, (note if a != alias else "")

    # ---------- apps: provider API passthrough ----------
    def proxy(self, path, body):
        key = self.headers.get("x-api-key") or self.headers.get("authorization", "").removeprefix("Bearer ")
        c = db()
        acct = c.execute("select * from accounts where key_hash = ? and archived is null", (sha(key),)).fetchone() if key else None
        if not acct:
            return self.reply(401, {"error": "invalid key"})
        alias, question = body.get("model"), last_user_text(body.get("messages"))
        if acct["key_expires"] and acct["key_expires"] < time.time():
            return self.refuse(c, acct, 401, "api key expired", "key-expired", alias, question)
        if isinstance(body.get("messages"), list) and len(body["messages"]) > MAX_MESSAGES:
            return self.refuse(c, acct, 400, "too many messages", "too-many-messages", alias)
        err = authorize(c, acct, alias)
        if err:
            return self.refuse(c, acct, *err, alias, question)
        provider = MODELS[alias][0]
        if PROVIDERS[provider][0] != path:
            return self.reply(400, {"error": f"model '{alias}' must be called via {PROVIDERS[provider][0]}"})
        if not self.screen(c, acct, question, alias):
            return
        clean = redact(body)  # masked before anything leaves for the provider; the log keeps the same masked version
        body = self.sensitive(c, acct, body, clean, masked(json.dumps(body, ensure_ascii=False), json.dumps(clean, ensure_ascii=False)),
                              alias, question)
        if body is None:
            return
        for k in ("max_tokens", "max_completion_tokens", "max_output_tokens"):
            if isinstance(body.get(k), (int, float)) and body[k] > MAX_OUTPUT_TOKENS:
                body[k] = MAX_OUTPUT_TOKENS
        if not inflight_enter(acct["name"]):
            return self.refuse(c, acct, 429, "too many requests in progress", "concurrency", alias, question)
        try:
            self.forward(c, acct, path, alias, body)
        finally:
            inflight_leave(acct["name"])

    def forward(self, c, acct, path, alias, body):
        def build(a):
            up = {**body, "model": MODELS[a][1]}
            if body.get("stream") and path == "/v1/chat/completions":
                up["stream_options"] = {**(body.get("stream_options") or {}), "include_usage": True}
            return up
        started, sent, hidden = [], [], [0]

        def on_line(line, ev):
            if not started:
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("x-gateway-model", self.current_alias)
                self.end_headers()  # no content-length: HTTP/1.0 closes the connection at the end
                started.append(True)
            if isinstance(ev, dict):  # keys in the answer are masked event by event (one split across events gets through)
                clean = redact(ev, mask_answer)
                if clean != ev:
                    hidden[0] += 1
                    line = b"data: " + json.dumps(clean, ensure_ascii=False).encode() + b"\n"
            sent.append(line)
            self.wfile.write(line)
            self.wfile.flush()

        used_alias, status, data, u, note = self.call_with_backup(alias, build, on_line, started, path)
        if status >= 400 and not u["in"] and not u["out"] and b"provider unreachable" in data:
            return self.reply(502, json.loads(data))
        if started:
            data = b"".join(sent)
        else:
            try:
                parsed = json.loads(data)
                clean = redact(parsed, mask_answer)
                if clean != parsed:
                    hidden[0] += 1
                    data = json.dumps(clean, ensure_ascii=False).encode()
            except ValueError:
                pass
        text = data.decode(errors="replace")
        charge(c, acct, used_alias, u, json.dumps(body, ensure_ascii=False), text, note, self.rid)
        self.answer_events(c, acct, used_alias, text, hidden[0], security.bad_links(text))
        if not started:
            self.send_raw(status, data, "application/json", [("x-gateway-model", used_alias)])

    def answer_events(self, c, acct, alias, text, hidden, links):
        found = security.scan(text)
        with c:
            if "dangerous-command" in found:
                self.event(c, "dangerous-answer", acct["name"], {"model": MODELS[alias][1]})
            if hidden:
                self.event(c, "answer-masked", acct["name"], {"model": MODELS[alias][1], "count": hidden})
            if links:
                self.event(c, "suspicious-link", acct["name"], {"model": MODELS[alias][1], "links": links[:5]})

    # ---------- employees: login + chat ----------
    def user_get(self, path):
        c = db()
        if path == "/api/config":
            return self.reply(200, {"open": self.open_ok()})
        if path == "/api/people" and self.open_ok():
            rows = c.execute("select name, team from accounts where pw_hash is not null and archived is null order by team, name")
            return self.reply(200, [dict(r) for r in rows])
        acct = self.session_account(c)
        if not acct:
            return self.reply(401, {"error": "not logged in"})
        if path == "/api/me":
            team = c.execute("select budget, spent from teams where name = ?", (acct["team"],)).fetchone()
            names = sources.allowed(c, acct["team"])
            readable = [dict(r) for r in c.execute("select name, description from sources order by name") if r["name"] in names]
            labels = dict(c.execute("select alias, label from models").fetchall())
            mine = [m for m in acct["models"].split(",") if m in MODELS]
            return self.reply(200, {"name": acct["name"], "team": acct["team"], "models": mine,
                                    "model_labels": {m: labels.get(m) or m for m in mine}, "default_model": default_model(c),
                                    "auto": setting(c, "auto_enabled", "1") == "1" and setting(c, "auto_cheap", "fast") in mine,
                                    "budget": acct["budget"], "spent": acct["spent"],
                                    "team_budget": team["budget"] if team else 0, "team_spent": team["spent"] if team else 0,
                                    "sources": readable})
        if path in ("/api/conversations", "/api/conversations/archived"):  # saved chats, or the ones moved to the archive
            rows = c.execute("select id, title, updated, archived from conversations where name = ? and archived is "
                             + ("not null" if path.endswith("archived") else "null") + " order by updated desc limit 200", (acct["name"],))
            return self.reply(200, [{**dict(r), "title": decrypt(r["title"])} for r in rows])
        if path.startswith("/api/conversations/"):
            row = c.execute("select id, title, messages from conversations where id = ? and name = ?",
                            (path.rsplit("/", 1)[1], acct["name"])).fetchone()
            if not row:
                return self.reply(404, {"error": "not found"})
            return self.reply(200, {"id": row["id"], "title": decrypt(row["title"]), "messages": json.loads(decrypt(row["messages"]))})
        self.reply(404, {"error": "not found"})

    def user_post(self, path, body):
        c = db()
        if path == "/api/login":
            return self.login(c, body)
        if path == "/api/as":  # open access: start a session as the chosen person, no password
            if not self.open_ok():
                return self.reply(403, {"error": "open access is off"})
            name = str(body.get("name", ""))
            if not c.execute("select 1 from accounts where name = ? and pw_hash is not null and archived is null", (name,)).fetchone():
                return self.reply(404, {"error": "no such user"})
            return self.start_session(c, name)
        acct = self.session_account(c)
        if not acct:
            return self.reply(401, {"error": "not logged in"})
        if path == "/api/logout":
            token = http.cookies.SimpleCookie(self.headers.get("cookie", "")).get("session")
            with c:
                c.execute("delete from sessions where token_hash = ?", (sha(token.value),))
            return self.reply(200, {"ok": True}, [self.cookie("", 0)])
        if path == "/api/password":
            if not check_password(str(body.get("old", "")), acct["pw_hash"]):
                return self.reply(403, {"error": "current password is wrong"})
            with c:
                c.execute("update accounts set pw_hash = ? where name = ?", (hash_password(check_new_password(body.get("new"))), acct["name"]))
                c.execute("delete from sessions where name = ?", (acct["name"],))  # log out everywhere else too
            return self.reply(200, {"ok": True}, [self.cookie("", 0)])
        if path == "/api/chat":
            return self.chat(c, acct, body)
        if path == "/api/conversations":
            cid = str(body.get("id") or secrets.token_hex(8))
            messages = body.get("messages")
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            with c:
                owner = c.execute("select name from conversations where id = ?", (cid,)).fetchone()
                if owner and owner["name"] != acct["name"]:
                    return self.reply(404, {"error": "not found"})
                c.execute("insert or replace into conversations(id, name, title, updated, messages) values (?,?,?,?,?)",
                          (cid, acct["name"], encrypt(redact_text(str(body.get("title") or ""))[:100]), time.time(),
                           encrypt(json.dumps(redact(messages), ensure_ascii=False))))
            return self.reply(200, {"id": cid})
        if path in ("/api/conversations/archive", "/api/conversations/restore"):  # own chats only; nothing is deleted
            restore, cid = path.endswith("restore"), str(body.get("id"))
            with c:
                n = c.execute("update conversations set archived = ? where id = ? and name = ? and archived is "
                              + ("not null" if restore else "null"), (None if restore else time.time(), cid, acct["name"])).rowcount
                if n:
                    audit(c, "restore" if restore else "archive", {"kind": "chat", "name": acct["name"], "id": cid})
            return self.reply(200 if n else 404, {"ok": True} if n else {"error": "not found"})
        self.reply(404, {"error": "not found"})

    def login(self, c, body):
        name, pw = str(body.get("name", "")), str(body.get("password", ""))
        acct = c.execute("select * from accounts where name = ? and archived is null", (name,)).fetchone()  # archived: as if unknown
        now, ip = time.time(), self.client_ip()
        # guessing across many names from one address: that address waits, whatever name it tries next
        if login_fails(ip) >= LOGIN_IP_LIMIT:
            return self.reply(429, {"error": f"too many wrong passwords from this address, try again in {LOGIN_IP_MINUTES} minutes"})
        if acct and acct["locked_until"] > now:
            return self.reply(429, {"error": f"too many wrong passwords, try again in {LOCK_MINUTES} minutes"})
        # unknown names still pay the password-hash cost, so response time doesn't reveal which names exist
        if not check_password(pw, acct["pw_hash"] if acct and acct["pw_hash"] else DUMMY_HASH) or not acct:
            if login_fails(ip, add=True) == LOGIN_IP_LIMIT:
                with c:
                    self.event(c, "login-throttled", "", {"ip": ip, "minutes": LOGIN_IP_MINUTES})
            if acct:
                with c:
                    failed = acct["failed"] + 1
                    c.execute("update accounts set failed = ?, locked_until = ? where name = ?",
                              (0 if failed >= LOCK_AFTER else failed, now + LOCK_MINUTES * 60 if failed >= LOCK_AFTER else 0, name))
                    if failed >= LOCK_AFTER:
                        self.event(c, "account-locked", name, {"ip": ip, "minutes": LOCK_MINUTES})
            return self.reply(401, {"error": "wrong name or password"})
        with c:
            c.execute("update accounts set failed = 0 where name = ?", (name,))
        self.start_session(c, name)

    def start_session(self, c, name):
        token, now = secrets.token_urlsafe(32), time.time()
        with c:
            c.execute("delete from sessions where expires < ?", (now,))
            c.execute("insert into sessions values (?,?,?)", (sha(token), name, now + SESSION_HOURS * 3600))
        self.reply(200, {"name": name}, [self.cookie(token, SESSION_HOURS * 3600)])

    def chat(self, c, acct, body):
        alias, messages = body.get("model"), body.get("messages")
        if not isinstance(messages, list) or not messages or not all(
                isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) for m in messages):
            raise ValueError("messages must be a non-empty list of {role: user|assistant, content: text}")
        route = ""
        wanted = body.get("sources") or []
        if alias == "auto":  # automatic choice: cheap model for simple questions, strong one for heavy work
            if setting(c, "auto_enabled", "1") != "1":
                return self.reply(403, {"error": "automatic model choice is turned off"})
            alias, route = route_auto(c, acct, messages)
            if not alias:
                return self.reply(403, {"error": route})
        last = messages[-1]["content"]
        if len(messages) > MAX_MESSAGES:
            return self.refuse(c, acct, 400, "too many messages", "too-many-messages", alias)
        err = authorize(c, acct, alias)
        if err:
            return self.refuse(c, acct, *err, alias, last)
        if not self.screen(c, acct, last if messages[-1]["role"] == "user" else "", alias):
            return
        original = [{"role": m["role"], "content": m["content"]} for m in messages]
        clean = redact(original)
        messages = self.sensitive(c, acct, original, clean, masked(last, clean[-1]["content"]), alias, last)
        if messages is None:
            return
        if not inflight_enter(acct["name"]):
            return self.refuse(c, acct, 429, "too many requests in progress", "concurrency", alias, last)
        try:
            self.chat_forward(c, acct, alias, route, messages, body.get("sources") or [])
        finally:
            inflight_leave(acct["name"])

    def screen_hits(self, c, acct, hits):
        """Retrieved passages are data handed to the model: a passage with browser code is always left out, one that
        tries to give the model instructions is left out under the block policy (and only logged otherwise)."""
        out, block = [], policy(c)[0] == "block"
        for source, title, body in hits:
            found = security.scan(body)
            drop = "script" in found or (block and security.ATTACKS & set(found))
            if found:
                with c:
                    self.event(c, "document-refused" if drop else "document-flagged", source,
                               {"file": title, "found": found, "user": acct["name"]})
            if not drop:
                out.append((source, title, body))
        return out

    def chat_forward(self, c, acct, alias, route, messages, wanted):
        # company documents: only sources the user's team may read, and only the ones the user switched on
        names = [n for n in sources.allowed(c, acct["team"]) if n in wanted]
        question = messages[-1]["content"] if messages[-1]["role"] == "user" else None
        hits = (mcp_search(c, names, question, acct["name"], self.rid) + sources.search(c, names, question)) if question else []
        hits = self.screen_hits(c, acct, hits)
        system = redact_text(sources.system_prompt(hits)) if hits else None
        used = list(dict.fromkeys(f"{s} / {t}" for s, t, _ in hits))
        def build(a):
            up = {"model": MODELS[a][1], "messages": messages, "stream": True}
            if MODELS[a][0] == "anthropic":
                up["max_tokens"] = MAX_OUTPUT_TOKENS
                # provider-side cache: the conversation so far is re-read at about a tenth of the input price next turn
                up["cache_control"] = {"type": "ephemeral"}
                if system:
                    up["system"] = system
            else:  # OpenAI and Gemini cache repeated prefixes on their own
                up["stream_options"] = {"include_usage": True}
                if system:
                    up["messages"] = [{"role": "system", "content": system}, *messages]
            return up
        started, text, masker = [], [], AnswerMasker()
        labels = dict(c.execute("select alias, label from models").fetchall())

        def write(s):
            if s:
                text.append(s)
                self.wfile.write(s.encode())
                self.wfile.flush()

        def on_line(line, ev):
            if not started:
                a = self.current_alias
                note = route if a == alias else f"גיבוי: {labels.get(alias) or alias} לא זמין"
                self.send_response(200)
                self.send_header("content-type", "text/plain; charset=utf-8")
                self.send_header("x-sources", urllib.parse.quote(json.dumps(used, ensure_ascii=False)))
                self.send_header("x-model-used", a)
                self.send_header("x-model-label", urllib.parse.quote(labels.get(a) or a))
                self.send_header("x-route", urllib.parse.quote(note))
                self.end_headers()
                started.append(True)
            piece = delta_text(MODELS[self.current_alias][0], ev)
            if piece:
                write(masker.feed(piece))  # keys in the answer are masked before they reach the employee

        used_alias, status, data, u, note = self.call_with_backup(alias, build, on_line, started)
        answer = ""
        if started:
            write(masker.flush())
            answer = "".join(text)
            links = security.bad_links(answer)
            warning = security.answer_warning(security.scan(answer), links)
            write(warning)
            self.answer_events(c, acct, used_alias, answer, masker.count, links)
            # the gateway's own instructions repeated word for word: kept out of the log, and flagged
            answer, leaks = leaked("".join(text), sources.HEADER) if system else ("".join(text), 0)
            if leaks:
                with c:
                    self.event(c, "prompt-leak", acct["name"], {"model": MODELS[used_alias][1], "count": leaks})
        logged = {"sources": used, "messages": messages} if used else messages
        note = "; ".join(x for x in (f"auto: {route}" if route else "", note) if x)
        charge(c, acct, used_alias, u, json.dumps(logged, ensure_ascii=False),
               answer if started else data.decode(errors="replace"), note, self.rid)
        if not started:
            self.reply(502 if status < 400 else status, {"error": "provider error", "detail": data.decode(errors="replace")[:500]})

    def test_model(self, c, row):
        """Send a 5-token question to the provider and report whether the key and model id work."""
        _, url, auth, fields = PROVIDERS[row["provider"]]
        if not next((v.removeprefix("Bearer ").strip() for k, v in auth.items() if k != "anthropic-version"), ""):
            return {"ok": False, "error": "no API key for this provider in .env"}
        body = {"model": row["model"], "messages": [{"role": "user", "content": "Reply with the word OK."}]}
        body["max_completion_tokens" if row["provider"] == "openai" else "max_tokens"] = 5  # newer OpenAI models reject max_tokens
        started = time.time()
        try:
            status, data, u = upstream(row["provider"], body, lambda *_: None)
        except urllib.error.URLError as e:
            return {"ok": False, "error": f"provider unreachable: {e.reason}"}
        ms = round((time.time() - started) * 1000)
        cost = price_usage(row["price_in"], row["price_out"], row["price_cached"] or 0, u)
        log_call(c, "(בדיקת מודל)", "", row["model"], u, cost, json.dumps(body, ensure_ascii=False), data.decode(errors="replace")[:2000])
        if status >= 400:
            try:
                detail = json.loads(data).get("error")
                detail = detail.get("message") if isinstance(detail, dict) else detail
            except (ValueError, AttributeError):
                detail = data.decode(errors="replace")[:200]
            return {"ok": False, "status": status, "ms": ms, "error": str(detail or f"HTTP {status}")[:300]}
        return {"ok": True, "status": status, "ms": ms}

    # ---------- admin ----------
    def admin_get(self, path):
        c = db()
        if path == "/admin/api/overview":
            start, _ = month_bounds()
            prev = month_bounds(start - 1)[0]
            last = dict(c.execute("select name, sum(cost) from logs where ts >= ? and ts < ? group by name", (prev, start)).fetchall())
            last_team = dict(c.execute("select team, sum(cost) from logs where ts >= ? and ts < ? group by team", (prev, start)).fetchall())
            accounts = []
            for a in c.execute("select * from accounts where archived is null order by team, name"):
                projected, recommended = forecast(a["spent"], last.get(a["name"]) or 0)
                accounts.append({"name": a["name"], "team": a["team"], "models": a["models"].split(","), "budget": a["budget"],
                                 "spent": a["spent"], "rpm": a["rpm"], "has_password": bool(a["pw_hash"]),
                                 "key_prefix": a["key_prefix"] if a["key_hash"] else None,
                                 "locked": a["locked_until"] > time.time(), "last_month": last.get(a["name"]) or 0,
                                 "key_expires": a["key_expires"] if a["key_hash"] else None,
                                 "key_created": a["key_created"] if a["key_hash"] else None, "daily_tokens": a["daily_tokens"],
                                 "projected": projected, "recommended": recommended})
            teams = []
            for t in c.execute("select * from teams where archived is null order by name"):
                projected, recommended = forecast(t["spent"], last_team.get(t["name"]) or 0)
                members = c.execute("select count(*), coalesce(sum(budget), 0) from accounts where team = ? and archived is null", (t["name"],)).fetchone()
                teams.append({"name": t["name"], "budget": t["budget"], "spent": t["spent"], "members": members[0],
                              "members_budget": members[1], "last_month": last_team.get(t["name"]) or 0,
                              "projected": projected, "recommended": recommended})
            model_info = {r["alias"]: {"provider": r["provider"], "model": r["model"], "price_in": r["price_in"], "price_out": r["price_out"],
                                       "label": r["label"], "enabled": bool(r["enabled"])}
                          for r in c.execute("select * from models where archived is null order by created, alias")}
            return self.reply(200, {"models": list(model_info), "model_info": model_info, "default_model": default_model(c), "soft_limit": SOFT_LIMIT,
                                    "accounts": accounts, "teams": teams})
        if path == "/admin/api/logs":
            # ponytail: last 200 only, add paging/search when someone needs older rows in the UI
            rows = c.execute("select ts, name, team, model, tokens_in, tokens_out, cost, request, response, request_id from logs"
                             " order by ts desc limit 200")
            return self.reply(200, [{**dict(r), "request": decrypt(r["request"]), "response": decrypt(r["response"])} for r in rows])
        if path == "/admin/api/usage":
            rows = c.execute("select name, team, model, count(*) requests, sum(tokens_in) tokens_in, sum(tokens_out) tokens_out,"
                             " sum(cost) cost from logs where ts >= ? group by name, model order by cost desc", (month_bounds()[0],))
            return self.reply(200, [dict(r) for r in rows])
        if path == "/admin/api/activity":
            start, _ = month_bounds()
            prev = month_bounds(start - 1)[0]
            first = month_bounds(month_bounds(prev - 1)[0] - 1)[0]  # three months back, for the monthly team totals
            day = lambda lo, hi: [dict(r) for r in c.execute(
                "select cast(strftime('%d', ts, 'unixepoch', 'localtime') as int) day, sum(cost) cost from logs"
                " where ts >= ? and ts < ? group by day order by day", (lo, hi))]
            return self.reply(200, {
                "heat": [dict(r) for r in c.execute(
                    "select cast(strftime('%w', ts, 'unixepoch', 'localtime') as int) wd, cast(strftime('%H', ts, 'unixepoch', 'localtime') as int) hour,"
                    " count(*) requests from logs where ts >= ? group by wd, hour", (time.time() - 28 * 86400,))],
                "this_month": day(start, time.time() + 1), "last_month": day(prev, start),
                "days_in_month": time.localtime(month_bounds()[1] - 1).tm_mday,
                "months": [dict(r) for r in c.execute(
                    "select strftime('%Y-%m', ts, 'unixepoch', 'localtime') month, coalesce(nullif(team, ''), 'בלי צוות') team, sum(cost) cost"
                    " from logs where ts >= ? group by month, team order by month", (first,))]})
        if path == "/admin/api/daily":
            rows = c.execute("select date(ts, 'unixepoch', 'localtime') day, sum(cost) cost, count(*) requests from logs"
                             " where ts >= ? group by day order by day", (time.time() - 30 * 86400,))
            return self.reply(200, [dict(r) for r in rows])
        if path == "/admin/api/sources/status":
            try:
                import pypdf  # noqa: F401
                pdf = True
            except ImportError:
                pdf = False
            return self.reply(200, {"embeddings": embed_provider(), "vectors": sources.vector_status(c), "pdf": pdf,
                                    "extensions": sorted(sources.ALL_EXT)})
        if path == "/admin/api/sources":
            out = []
            for s in c.execute("select * from sources where archived is null order by name").fetchall():
                docs = [dict(d) for d in c.execute("select id, title, chars, updated from docs where source = ? and archived is null"
                                                   " order by title", (s["name"],))]
                cfg = mcp_config(s)
                public = {k: v for k, v in cfg.items() if k != "token"}
                out.append({**{k: s[k] for k in s.keys() if k != "config"}, "teams": [t for t in s["teams"].split(",") if t],
                            "docs": docs, "mcp": {**public, "has_token": bool(cfg.get("token"))} if s["kind"] == "mcp" else None})
            return self.reply(200, out)
        if path == "/admin/api/security":
            week = time.time() - 7 * 86400
            def detail(raw):
                d = json.loads(raw)
                if isinstance(d, dict) and "excerpt" in d:
                    d["excerpt"] = decrypt(d["excerpt"])
                return d
            events = [{"ts": r["ts"], "kind": r["kind"], "name": r["name"], "detail": detail(r["detail"])}
                      for r in c.execute("select * from security_events order by ts desc limit 200")]
            blocked = [{**dict(r), "excerpt": decrypt(r["excerpt"])} for r in c.execute(
                "select ts, name, team, reason, model, request_id, excerpt from blocked_requests order by ts desc limit 200")]
            blocked_counts = dict(c.execute("select reason, count(*) from blocked_requests where ts >= ? group by reason", (week,)).fetchall())
            spikes = [{"name": r["name"], "ts": r["ts"], **json.loads(r["detail"])} for r in c.execute(
                "select * from security_events where kind = 'cost-spike' and ts >= ? order by ts desc", (time.time() - 86400,))]
            inj, sens = policy(c)
            counts = dict(c.execute("select kind, count(*) from security_events where ts >= ? group by kind", (week,)).fetchall())
            open_keys = c.execute("select count(*) from accounts where key_hash is not null and rpm = 0 and archived is null").fetchone()[0]
            providers = [p for p, (_, _, auth, _) in PROVIDERS.items() if any(v.removeprefix("Bearer ").strip() for v in auth.values() if v != "2023-06-01")]
            checks = [
                {"ok": bool(ALLOWED_HOSTS), "text": "חיבור מוצפן (HTTPS) עם דומיין" if ALLOWED_HOSTS else
                 "אין דומיין, ולכן החיבור לא מוצפן. השאלות והסיסמאות עוברות ברשת כטקסט גלוי. מתאים לרשת המשרד בלבד."},
                {"ok": not ADMIN_PASSWORD or len(ADMIN_PASSWORD) >= 16, "text": "מסך הניהול סגור מבחוץ" if not ADMIN_PASSWORD else
                 ("סיסמת המנהל לגישה מבחוץ חזקה" if len(ADMIN_PASSWORD) >= 16 else "סיסמת המנהל לגישה מבחוץ קצרה מ-16 תווים")},
                {"ok": open_keys == 0, "text": "לכל מפתחות ה-API יש הגבלת קצב" if not open_keys else
                 ("מפתח API אחד" if open_keys == 1 else f"{open_keys} מפתחות API") + " בלי הגבלת קצב. מפתח שדלף יכול לרוקן תקציב מהר."},
                {"ok": not OPEN_ACCESS, "text": "כניסה לצ'אט עם סיסמה" if not OPEN_ACCESS else
                 "הצ'אט פתוח בלי סיסמה ברשת המשרד (OPEN_ACCESS): כל אחד יכול לבחור כל שם, להשתמש בתקציב שלו ולראות את השיחות שלו."},
                {"ok": bool(providers), "text": "ספקים מחוברים: " + ", ".join(providers) if providers else "אין מפתחות ספקים בקובץ ⁦.env⁩"},
                {"ok": bool(os.environ.get("FIREGATE_DATA_KEY", "").strip()), "text":
                 "השאלות והתשובות שמורות מוצפנות, והמפתח מוגדר בהגדרות השרת" if os.environ.get("FIREGATE_DATA_KEY", "").strip() else
                 "השאלות והתשובות שמורות מוצפנות, אבל מפתח ההצפנה נמצא בקובץ ליד מסד הנתונים. כדאי לשמור עותק שלו במקום אחר: "
                 "בלי המפתח אי אפשר לקרוא את השאלות, התשובות והשיחות."},
            ]
            return self.reply(200, {"events": events, "counts": counts, "checks": checks, "providers": providers,
                                    "policy": {"injection": inj, "sensitive": sens}, "blocked": blocked,
                                    "blocked_counts": blocked_counts, "spikes": spikes})
        if path == "/admin/api/audit/verify":
            return self.reply(200, verify_audit(c))
        if path == "/admin/api/report":
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            month = (q.get("month") or [time.strftime("%Y-%m")])[0]
            try:
                y, m = map(int, month.split("-"))
                start = time.mktime((y, m, 1, 0, 0, 0, 0, 0, -1))
            except ValueError:
                raise ValueError("month must look like 2026-10")
            end = month_bounds(start)[1]
            first = c.execute("select min(ts) from logs").fetchone()[0] or time.time()
            months, t = [], month_bounds()[0]
            while t >= month_bounds(first)[0] and len(months) < 36:
                months.append(time.strftime("%Y-%m", time.localtime(t)))
                t = month_bounds(t - 1)[0]

            def group(col):
                return [dict(r) for r in c.execute(
                    f"select {col} key, count(*) requests, sum(tokens_in) tokens_in, sum(tokens_out) tokens_out, sum(cost) cost,"
                    f" sum(cache_read) cache_read from logs where ts >= ? and ts < ? and name != '(בדיקת מודל)'"
                    f" group by {col} order by cost desc", (start, end))]
            budgets = {r["name"]: r["budget"] for r in c.execute("select name, budget from accounts")}
            team_budgets = {r["name"]: r["budget"] for r in c.execute("select name, budget from teams")}
            by_account = group("name")
            for r in by_account:
                r["team"] = (c.execute("select team from logs where name = ? and ts >= ? and ts < ? order by ts desc limit 1",
                                       (r["key"], start, end)).fetchone() or [""])[0]
                r["budget"] = budgets.get(r["key"])
            by_team = group("team")
            for r in by_team:
                r["budget"] = team_budgets.get(r["key"])
            totals = c.execute("select count(*) requests, coalesce(sum(cost), 0) cost, count(distinct name) people from logs"
                               " where ts >= ? and ts < ? and name != '(בדיקת מודל)'", (start, end)).fetchone()
            return self.reply(200, {"month": month, "months": months, "totals": dict(totals),
                                    "by_team": by_team, "by_account": by_account, "by_model": group("model")})
        if path == "/admin/api/models/daily":
            rows = c.execute("select date(ts, 'unixepoch', 'localtime') day, model, count(*) requests, sum(cost) cost from logs"
                             " where ts >= ? and name != '(בדיקת מודל)' group by day, model order by day", (time.time() - 30 * 86400,))
            return self.reply(200, [dict(r) for r in rows])
        if path == "/admin/api/models":
            start = month_bounds()[0]
            usage = {r["model"]: dict(r) for r in c.execute(
                "select model, count(*) requests, sum(cost) cost, max(ts) last_used from logs where ts >= ? group by model", (start,))}
            cache = {r["model"]: (r["cr"] or 0, r["cw"] or 0) for r in c.execute(
                "select model, sum(cache_read) cr, sum(cache_write) cw from logs where ts >= ? group by model", (start,))}
            backups = {r["model"]: r["n"] for r in c.execute(
                "select model, count(*) n from logs where ts >= ? and note like '%backup:%' group by model", (start,))}
            rows, saved = [], 0.0
            for r in c.execute("select * from models where archived is null order by created, alias"):
                users = c.execute("select count(*) from accounts where archived is null and ',' || models || ',' like ?",
                                  (f"%,{r['alias']},%",)).fetchone()[0]
                u = usage.get(r["model"], {})
                cr, cw = cache.get(r["model"], (0, 0))
                # what the cache saved: reads billed at the cache rate instead of full input, minus the 25% write premium
                model_saved = (cr * (r["price_in"] - (r["price_cached"] or 0)) - cw * r["price_in"] * 0.25) / 1e6
                saved += model_saved
                rows.append({**dict(r), "enabled": bool(r["enabled"]), "users": users, "requests": u.get("requests", 0),
                             "cost": u.get("cost") or 0, "last_used": u.get("last_used"), "cache_saved": round(model_saved, 6),
                             "backup_answers": backups.get(r["model"], 0)})
            providers = {p: bool(next((v.removeprefix("Bearer ").strip() for k, v in auth.items() if k != "anthropic-version"), ""))
                         for p, (_, _, auth, _) in PROVIDERS.items()}
            auto = {"enabled": setting(c, "auto_enabled", "1") == "1", "cheap": setting(c, "auto_cheap", "fast"),
                    "strong": setting(c, "auto_strong", "smart"),
                    "count": c.execute("select count(*) from logs where ts >= ? and note like 'auto:%'", (start,)).fetchone()[0]}
            return self.reply(200, {"models": rows, "default_model": default_model(c), "providers": providers,
                                    "cache_saved": round(saved, 6), "auto": auto})
        if path == "/admin/api/archive":
            return self.reply(200, archive_list(c))
        if path == "/admin/api/audit":
            rows = c.execute("select ts, action, detail from audit order by ts desc limit 100")
            return self.reply(200, [{"ts": r["ts"], "action": r["action"], "detail": json.loads(r["detail"])} for r in rows])
        self.reply(404, {"error": "not found"})

    def admin_post(self, path, body):
        c = db()
        name = str(body.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        with c:  # commit before replying, so the page's next read sees the change
            status, result = self.admin_write(c, path, body, name)
        refresh_models(c)  # a models-page change applies to the very next request
        self.reply(status, result)

    def admin_write(self, c, path, body, name):
        """Returns (http status, reply body)."""
        if path in ("/admin/api/archive", "/admin/api/restore"):  # kind + name (a document: name = its source, plus id)
            return set_archived(c, str(body.get("kind")), body, name, path.endswith("restore"))
        if path == "/admin/api/teams":  # create or update
            not_archived(c, "team", name)
            budget = float(body.get("budget") or 0)
            if budget < 0:
                raise ValueError("budget must be >= 0")
            old = c.execute("select budget from teams where name = ?", (name,)).fetchone()
            c.execute("insert into teams(name, budget, month) values (?,?,?) on conflict(name) do update set budget = excluded.budget",
                      (name, budget, time.strftime("%Y-%m")))
            audit(c, "team-save", {"name": name, "budget": budget, **({"old_budget": old[0]} if old else {})})
            return (200, {"ok": True})
        if path == "/admin/api/sources":  # create or update
            kind = body.get("kind")
            if kind not in ("upload", "folder", "mcp"):
                raise ValueError("kind must be upload, folder or mcp")
            not_archived(c, "source", name)
            folder = str(body.get("path") or "").strip() if kind in ("folder", "mcp") else None
            if kind == "folder":
                sources.check_folder(folder)
            config = None
            if kind == "mcp":
                if not re.match(r"^https?://", folder or ""):
                    raise ValueError("MCP server address must start with http:// or https://")
                old = c.execute("select config from sources where name = ?", (name,)).fetchone()
                old_cfg = load_config(old[0]) if old else {}
                mode = body.get("mode")
                if mode not in ("search", "resources"):
                    raise ValueError("MCP mode must be search or resources")
                if mode == "search" and not body.get("tool"):
                    raise ValueError("choose the MCP tool to call")
                tool, arg = str(body.get("tool") or ""), str(body.get("arg") or "query")
                if (tool and not MCP_NAME.match(tool)) or not MCP_NAME.match(arg):
                    raise ValueError("MCP tool and argument names may use only letters, digits and . _ - : /")
                # a blank token on edit keeps the saved one; stored encrypted
                config = encrypt(json.dumps({"token": str(body.get("token") or "") or old_cfg.get("token", ""), "mode": mode,
                                             "tool": tool, "arg": arg}, ensure_ascii=False))
            teams = [str(t) for t in body.get("teams") or []]
            known = {r[0] for r in c.execute("select name from teams where archived is null")} | {sources.EVERYONE}
            if any(t not in known for t in teams):
                raise ValueError("unknown team in access list")
            c.execute("insert into sources(name, description, kind, path, teams, config) values (?,?,?,?,?,?) on conflict(name) do update set"
                      " description = excluded.description, kind = excluded.kind, path = excluded.path, teams = excluded.teams,"
                      " config = excluded.config",
                      (name, str(body.get("description") or ""), kind, folder, ",".join(teams), config))
            audit(c, "source-save", {"name": name, "kind": kind, "path": folder, "teams": teams,
                                     **({"mode": body.get("mode"), "tool": body.get("tool")} if kind == "mcp" else {})})
            return (200, {"ok": True})
        if path == "/admin/api/sources/mcp-test":  # probe a server before saving; a saved source's token is reused if none given
            url, token = str(body.get("url") or "").strip(), str(body.get("token") or "")
            if not re.match(r"^https?://", url):
                raise ValueError("MCP server address must start with http:// or https://")
            if not token and body.get("source"):
                row = c.execute("select config from sources where name = ?", (str(body["source"]),)).fetchone()
                token = (load_config(row[0]) if row else {}).get("token", "")
            try:
                return (200, {"ok": True, **mcp.probe(url, token)})
            except mcp.MCPError as e:
                return (200, {"ok": False, "error": str(e)})
        if path.startswith("/admin/api/sources/"):
            source = c.execute("select * from sources where name = ? and archived is null", (name,)).fetchone()
            if not source:
                return (404, {"error": f"no source '{name}'"})
            if path == "/admin/api/sources/upload":
                added = []
                for f in body.get("files") or []:
                    title = str(f.get("name") or "").strip()
                    if not title or not (isinstance(f.get("text"), str) or isinstance(f.get("b64"), str)):
                        raise ValueError("each file needs a name and text")
                    if os.path.splitext(title)[1].lower() not in sources.ALL_EXT:
                        raise ValueError(f"{title}: unsupported file type ({', '.join(sorted(sources.ALL_EXT))})")
                    raw = base64.b64decode(f["b64"]) if f.get("b64") else f["text"].encode()
                    text = sources.extract_text(title, raw)
                    # check the original too: converting HTML to text drops <script> and onerror= that were there
                    found = sorted(set(security.scan(text)) | set(security.scan(raw.decode("utf-8", errors="replace"))
                                                                   if not f.get("b64") else set()))
                    if found and not body.get("force"):
                        raise ValueError(f"suspicious content in {title}: {', '.join(found)}")
                    if found:
                        self.event(c, "document-forced", name, {"file": title, "found": found})
                    sources.add_doc(c, name, title, text)
                    added.append(title)
                audit(c, "source-upload", {"name": name, "files": added})
                return (200, {"ok": True, "added": len(added)})
            if path == "/admin/api/sources/sync":
                if source["kind"] == "mcp" and mcp_config(source).get("mode") == "resources":
                    try:
                        indexed, skipped, flagged, gone = mcp_sync(c, source)
                    except mcp.MCPError as e:
                        raise ValueError(f"MCP server: {e}")
                elif source["kind"] == "folder":
                    indexed, skipped, flagged, gone = sources.sync_folder(c, name, source["path"], security.scan)
                else:
                    raise ValueError("only folder sources and MCP sources in sync mode can be synced")
                for title, found in flagged:
                    self.event(c, "document-refused", name, {"file": title, "found": found})
                audit(c, "source-sync", {"name": name, "files": indexed, "skipped": skipped, "flagged": len(flagged), "archived": gone})
                return (200, {"ok": True, "indexed": indexed, "skipped": skipped, "flagged": [t for t, _ in flagged], "archived": gone})
            if path == "/admin/api/sources/reindex":
                if not embed_provider():
                    raise ValueError("meaning search needs an OpenAI or Google key in .env")
                added, missing = sources.reindex(c, name)
                return (200, {"ok": True, "added": added, "missing": missing})
            return (404, {"error": "not found"})
        if path == "/admin/api/models":  # create or update; name = alias
            if not MODEL_ALIAS.match(name):
                raise ValueError("alias must be 2-40 lowercase letters, digits, dot, dash or underscore")
            not_archived(c, "model", name)
            provider, model = str(body.get("provider", "")), str(body.get("model", "")).strip()
            if provider not in PROVIDERS:
                raise ValueError("unknown provider")
            if not model:
                raise ValueError("model id is required")
            price_in, price_out = float(body.get("price_in")), float(body.get("price_out"))
            if price_in < 0 or price_out < 0:
                raise ValueError("price must be >= 0")
            enabled = 1 if body.get("enabled", True) else 0
            price_cached = body.get("price_cached")
            price_cached = round(price_in * 0.1, 6) if price_cached in (None, "") else float(price_cached)
            if price_cached < 0:
                raise ValueError("price must be >= 0")
            fallback = str(body.get("fallback") or "") or None
            if fallback and (fallback == name or fallback not in ALL_MODELS):
                raise ValueError("backup model must be another existing model")
            old = c.execute("select * from models where alias = ?", (name,)).fetchone()
            c.execute("insert into models(alias, label, provider, model, price_in, price_out, enabled, created, price_cached, fallback)"
                      " values (?,?,?,?,?,?,?,?,?,?) on conflict(alias) do update set label = excluded.label, provider = excluded.provider,"
                      " model = excluded.model, price_in = excluded.price_in, price_out = excluded.price_out, enabled = excluded.enabled,"
                      " price_cached = excluded.price_cached, fallback = excluded.fallback",
                      (name, str(body.get("label") or "").strip()[:60], provider, model, price_in, price_out, enabled, time.time(),
                       price_cached, fallback))
            if not enabled and c.execute("select value from settings where key = 'default_model'").fetchone()[0] == name:
                raise ValueError("this is the default model; choose another default before turning it off")
            changes = {k: [old[k], v] for k, v in (("provider", provider), ("model", model), ("price_in", price_in),
                                                     ("price_out", price_out), ("price_cached", price_cached), ("fallback", fallback),
                                                     ("enabled", enabled)) if old and old[k] != v}
            audit(c, "model-save", {"name": name, "model": model, "provider": provider, "price_in": price_in, "price_out": price_out,
                                    "enabled": bool(enabled), **({"changes": changes} if changes else {"new": not old})})
            return (200, {"ok": True})
        if path == "/admin/api/security/policy":  # name is "policy"
            inj, sens = str(body.get("injection", "")), str(body.get("sensitive", ""))
            if inj not in ("block", "log") or sens not in ("mask", "block", "log"):
                raise ValueError("unknown security policy")
            old = policy(c)
            for k, v in (("policy_injection", inj), ("policy_sensitive", sens)):
                c.execute("insert into settings values (?, ?) on conflict(key) do update set value = excluded.value", (k, v))
            audit(c, "security-policy", {"name": "policy", "injection": inj, "sensitive": sens, "old": list(old)})
            return (200, {"ok": True})
        if path == "/admin/api/models/auto":  # automatic choice settings; name is "auto"
            cheap, strong = str(body.get("cheap", "")), str(body.get("strong", ""))
            if cheap not in ALL_MODELS or strong not in ALL_MODELS:
                raise ValueError("pick existing models for automatic choice")
            for k, v in (("auto_enabled", "1" if body.get("enabled") else "0"), ("auto_cheap", cheap), ("auto_strong", strong)):
                c.execute("insert into settings values (?, ?) on conflict(key) do update set value = excluded.value", (k, v))
            audit(c, "model-auto", {"name": "auto", "enabled": bool(body.get("enabled")), "cheap": cheap, "strong": strong})
            return (200, {"ok": True})
        if path.startswith("/admin/api/models/"):
            row = c.execute("select * from models where alias = ? and archived is null", (name,)).fetchone()
            if not row:
                return (404, {"error": f"no model '{name}'"})
            if path == "/admin/api/models/default":
                if not row["enabled"]:
                    raise ValueError("turn the model on before making it the default")
                c.execute("insert into settings values ('default_model', ?) on conflict(key) do update set value = excluded.value", (name,))
                audit(c, "model-default", {"name": name})
                return (200, {"ok": True})
            if path == "/admin/api/models/test":
                return (200, self.test_model(c, row))
            return (404, {"error": "not found"})
        if path == "/admin/api/accounts":  # create
            not_archived(c, "account", name)
            fields = account_fields(c, body, partial=False)
            pw = body.get("password")
            if not pw and not body.get("api_key"):
                raise ValueError("give a password (chat login) or an API key, or both")
            try:
                c.execute("insert into accounts(name, team, models, budget, rpm, month, pw_hash, daily_tokens, key_expires)"
                          " values (?,?,?,?,?,?,?,?,?)",
                          (name, fields.get("team", ""), fields["models"], fields["budget"], fields.get("rpm", 0),
                           time.strftime("%Y-%m"), hash_password(check_new_password(pw)) if pw else None,
                           fields.get("daily_tokens", 0), fields.get("key_expires")))
            except sqlite3.IntegrityError:
                raise ValueError(f"name '{name}' already exists")
            key = new_key(c, name) if body.get("api_key") else None
            audit(c, "create", {"name": name, **fields, "password": bool(pw), "api_key": bool(key)})
            return (200, {"ok": True, "key": key})
        if not c.execute("select 1 from accounts where name = ? and archived is null", (name,)).fetchone():
            return (404, {"error": f"no account '{name}'"})
        if path == "/admin/api/accounts/update":
            fields = account_fields(c, body, partial=True)
            if body.get("password"):
                fields.update(pw_hash=hash_password(check_new_password(body["password"])), failed=0, locked_until=0)
                c.execute("delete from sessions where name = ?", (name,))
            if not fields:
                raise ValueError("nothing to update")
            old_budget = c.execute("select budget from accounts where name = ?", (name,)).fetchone()[0]
            c.execute(f"update accounts set {', '.join(k + ' = ?' for k in fields)} where name = ?", (*fields.values(), name))
            audit(c, "update", {"name": name, **{k: v for k, v in fields.items() if k not in ("pw_hash", "failed", "locked_until")},
                                **({"password": "changed"} if "pw_hash" in fields else {}),
                                **({"old_budget": old_budget} if "budget" in fields and fields["budget"] != old_budget else {})})
            return (200, {"ok": True})
        if path == "/admin/api/accounts/key":
            if body.get("action") == "revoke":
                c.execute("update accounts set key_hash = null, key_prefix = null where name = ?", (name,))
                audit(c, "key-revoke", {"name": name})
                return (200, {"ok": True})
            key = new_key(c, name)
            c.execute("update accounts set key_expires = null where name = ?", (name,))  # a new key starts without an expiry date
            audit(c, "key-new", {"name": name})
            return (200, {"ok": True, "key": key})
        return 404, {"error": "not found"}


if __name__ == "__main__":
    try:
        db().close()  # schema, data key and one-time migrations before the first request
    except DataKeyError as e:
        sys.exit(f"FireGate cannot start: {e}")
    if os.environ.get("SEED_DEMO", "").strip().lower() in ("1", "true", "yes", "on"):
        # demo hosting whose disk resets on restart: start every time with sample data
        import seed_demo  # noqa: F401  (fills an empty database; leaves a filled one alone)
    port = int(os.environ.get("PORT", 8080))
    print(f"gateway listening on :{port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
