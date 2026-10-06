"""AI gateway: every model call in the company goes through here.

Accounts (employees or apps) belong to teams. Each account and each team has a monthly budget; a call is blocked
when either runs out (a budget of 0 means no cap). Employees use the chat page (/chat); apps call the provider APIs through
us with a gateway key. Provider keys never leave this server; gateway keys and passwords are stored only as hashes.

Run:      ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=... python gateway.py
Pages:    /        management (open from the office network; from outside only with ADMIN_PASSWORD); also /admin
          /chat    chat for employees
Apps:     Anthropic SDK -> base_url http://HOST:8080        (POST /v1/messages)
          OpenAI SDK    -> base_url http://HOST:8080/v1     (POST /v1/chat/completions, also for Gemini models)
"""
import base64
import collections
import csv
import datetime
import functools
import hashlib
import html
import http.cookies
import io
import ipaddress
import json
import math
import os
import re
import secrets
import smtplib
import socket
import sqlite3
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zoneinfo
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import mcp
import security
import settings
import sources

# Without Docker: read KEY=VALUE lines from .env next to this file. Real environment variables win.
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env):
    with open(_env, encoding="utf-8") as f:
        for line in f:
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())

VERSION = "1.2.2"  # also in ui.js (shown in the admin footer); CHANGELOG.md lists what each version changed
DB =os.environ.get("GATEWAY_DB", "gateway.db")
# Every adjustable value (admin password, open access, allowed host names, limits, thresholds, provider keys...) is a
# setting: settings.py lists them all, cfg() reads one. The server's environment / .env wins over the settings screen.
# Admin from a private-network address (office LAN, this machine) needs no password; from anywhere else the admin
# password, or no access at all without one. Allowed host names block "DNS rebinding": a hostile site pointing its own
# name at this server's address so the victim's browser talks to us as that site. Open access: from the office network
# the chat needs no password; people pick their own name. Public deployment (a cloud host): every visitor arrives through
# the host's private network, so "private address" no longer means "inside the office"; the admin page then always needs
# the password and open access is off.
cfg = settings.get
FIXED_HOSTS = {h.strip().lower() for h in (os.environ.get("SITE_ADDRESS", ""), os.environ.get("RENDER_EXTERNAL_HOSTNAME", ""))
               if h.strip() and not h.strip().startswith(":")}
HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = {"/admin": ("admin.html", "text/html"), "/chat": ("chat.html", "text/html"), "/docs": ("docs.html", "text/html"), "/style.css": ("style.css", "text/css"),
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
PBKDF2_ROUNDS = 200_000
MB = 1024 * 1024
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def trusted_networks():
    # proxies whose X-Forwarded-For / X-Forwarded-Proto we believe. Anyone else sending those headers is ignored:
    # otherwise a visitor could claim an office address and skip the admin password.
    return [ipaddress.ip_network(p, strict=False) for p in cfg(None, "trusted_proxies")]


def public_deploy():
    return cfg(None, "public_deploy")


def open_access():
    return not public_deploy() and cfg(None, "open_access")


# provider -> (client-facing path, usage field names for input/output tokens). Each provider keeps its own request format,
# so apps use the provider's own SDK pointed at us. Keys and addresses are settings (anthropic_api_key, anthropic_url...).
# "local": models on the company's own server (Ollama, vLLM), the same API as OpenAI, at the address in local_base_url.
PROVIDERS = {
    "anthropic": ("/v1/messages", ("input_tokens", "output_tokens")),
    "openai": ("/v1/chat/completions", ("prompt_tokens", "completion_tokens")),
    "gemini": ("/v1/chat/completions", ("prompt_tokens", "completion_tokens")),  # Gemini's OpenAI-compatible endpoint
    "local": ("/v1/chat/completions", ("prompt_tokens", "completion_tokens")),
}


def provider_key(p):
    return cfg(None, p + "_api_key").strip()


def provider_auth(p):
    key = provider_key(p)
    if p == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {"authorization": "Bearer " + key} if key or p != "local" else {}


def provider_url(p):
    return cfg(None, "local_base_url") + "/chat/completions" if p == "local" else cfg(None, p + "_url")


# The local model server usually sits on the company network, so private addresses are allowed; this machine itself only
# with the local_loopback setting (Ollama installed next to the gateway). Cloud metadata and link-local addresses never.
LOCAL_OPENER = mcp.opener(lambda ip: mcp.blocked_ip(ip, loopback=cfg(None, "local_loopback"), private=True), "the local model server", OSError)

# Models live in the database and are managed from the admin "models" page.
# These are only the first-run defaults: alias, label, provider, real model, $ per 1M input / output tokens.
# Prices checked 2026-10-04; Gemini 3.8 Flash price is promotional until 2026-12-31.
DEFAULT_MODELS = [
    ("fast", "Claude Haiku 4.5", "anthropic", "claude-haiku-4-5-20251001", 1.0, 5.0),
    ("smart", "Claude Sonnet 5.5", "anthropic", "claude-sonnet-5-5", 2.0, 10.0),
    ("gpt-fast", "GPT-6 Luna", "openai", "gpt-6-luna", 0.10, 0.50),
    ("gpt-smart", "GPT-6.1 Sol", "openai", "gpt-6.1-sol", 2.0, 10.0),
    ("gemini-fast", "Gemini 3.8 Flash", "gemini", "gemini-3.8-flash", 0.75, 3.75),
    ("gemini-smart", "Gemini 3.1 Pro", "gemini", "gemini-3.1-pro-preview", 2.0, 12.0),
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
create table if not exists team_settings(team text not null, key text not null, value text, primary key(team, key));
create table if not exists blocked_requests(ts real, name text, team text, reason text, model text, request_id text, excerpt text);
create index if not exists blocked_requests_ts on blocked_requests(ts);
create index if not exists logs_name_ts on logs(name, ts);
"""


def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA + sources.SCHEMA + security.SCHEMA)
    migrate(c)
    settings.refresh(c)  # every connection, like the models: a change on the settings screen applies to the next request
    mcp.ALLOW_PRIVATE = cfg(c, "mcp_private")
    # monthly budgets: first touch in a new budget month zeroes spending (history stays in logs)
    month = month_of(time.time())
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
                           # teams: accounting codes for the chargeback export, and the models the team may use (NULL = no limit)
                           ("teams", "cost_center text"), ("teams", "gl_account text"), ("teams", "models text"),
                           # speed: whole call and time to the first piece of answer (ms), and the provider's HTTP status
                           ("logs", "latency_ms int"), ("logs", "ttft_ms int"), ("logs", "status int"),
                           ("audit", "seq int"), ("audit", "prev_hash text"), ("audit", "hash text"),
                           # archive instead of delete: when the item was archived, NULL = in use
                           *((t, "archived real") for t in ("accounts", "teams", "models", "sources", "docs", "conversations"))):
            try:
                c.execute(f"alter table {table} add column {col}")
            except sqlite3.OperationalError:
                pass  # already there
        # speed statistics read only these columns: an index holding them all spares reading the wide log rows
        c.execute("create index if not exists logs_speed on logs(ts, model, latency_ms, ttft_ms, status, name)")
        with c:
            c.execute("update models set price_cached = round(price_in * 0.1, 6) where price_cached is null")
            c.execute("update accounts set key_created = ? where key_hash is not null and key_created is null", (time.time(),))
            # model names: the generic "Claude מהיר"-style defaults became the real model names (1.0.1)
            for old, new, alias in (("Claude מהיר", "Claude Haiku 4.5", "fast"), ("Claude חכם", "Claude Sonnet 5.5", "smart"), ("GPT מהיר", "GPT-6 Luna", "gpt-fast"), ("GPT חכם", "GPT-6.1 Sol", "gpt-smart"), ("Gemini מהיר", "Gemini 3.8 Flash", "gemini-fast"), ("Gemini חכם", "Gemini 3.1 Pro", "gemini-smart"), ("Claude הכי חזק", "Claude Opus 5.5", "claude-top"), ("GPT הכי חזק", "GPT-6 Astra", "gpt-top"), ("Gemini חסכוני", "Gemini 3.5 Flash-Lite", "gemini-lite")):
                c.execute("update models set label = ? where alias = ? and label = ?", (new, alias, old))
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


def backup(c, label, folder="backups", tag=None):
    """Consistent copy of the whole database (SQLite backup API) to a folder in the database's own folder. Never replaces
    an existing file (and so never deletes an older backup)."""
    folder = os.path.join(os.path.dirname(os.path.abspath(DB)), folder)
    os.makedirs(folder, exist_ok=True)
    stem = f"{os.path.splitext(os.path.basename(DB))[0]}-{tag or 'before-' + label}-{time.strftime('%Y%m%d-%H%M%S')}"
    path, n = os.path.join(folder, stem + ".db"), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(folder, f"{stem}-{n}.db")
    dst = sqlite3.connect(path)
    try:
        c.backup(dst)
    finally:
        dst.close()
    print(f"database backed up ({tag or 'before migration: ' + label}): {path}", flush=True)
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
    m = cfg(c, "default_model")
    return m if m in MODELS else next(iter(MODELS), None)


# --- time: days and budget months in the chosen time zone (the timezone setting; empty = the server's clock) ---

def tzinfo():
    name = cfg(None, "timezone")
    try:
        return zoneinfo.ZoneInfo(name) if name else None
    except (ValueError, KeyError, OSError):  # no time zone data on this server (Windows without tzdata): the server's clock
        return None


def localtime(t=None):
    tz, t = tzinfo(), time.time() if t is None else t
    return datetime.datetime.fromtimestamp(t, tz).timetuple() if tz else time.localtime(t)


def mktime(y, m, d, hh=0, mm=0, ss=0):
    tz = tzinfo()
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=tz).timestamp() if tz else time.mktime((y, m, d, hh, mm, ss, 0, 0, -1))


def sql_local():
    """The SQLite modifier that turns a unix time into local time: 'localtime' (the server's clock) or the zone's offset."""
    tz = tzinfo()
    if not tz:
        return "localtime"
    # ponytail: today's offset for every row, so rows from the other side of a daylight-saving change sit an hour off in charts
    return f"{int(datetime.datetime.now(tz).utcoffset().total_seconds()):+d} seconds"


def ensure_chat_default_user(c):
    """The account the chat picks on its own (setting "chat_default_user"); created the first time it is needed:
    no budget cap (0), every enabled model, a random password nobody knows (it can be reset from the admin screen).
    Returns its name, or "" when the setting is empty or the name belongs to an archived account."""
    name = (cfg(c, "chat_default_user") or "").strip()
    if not name:
        return ""
    row = c.execute("select archived, pw_hash from accounts where name = ?", (name,)).fetchone()
    if row:
        return name if row["archived"] is None and row["pw_hash"] else ""
    team = "הנהלה" if c.execute("select 1 from teams where name = 'הנהלה' and archived is null").fetchone() else ""
    with c:
        c.execute("insert or ignore into accounts(name, team, models, budget, month, pw_hash) values (?,?,?,?,?,?)",
                  (name, team, ",".join(MODELS), 0, time.strftime("%Y-%m"), hash_password(secrets.token_urlsafe(24))))
        audit(c, "create", {"name": name, "team": team, "budget": 0, "models": ",".join(MODELS), "password": True,
                            "api_key": False, "by": "chat default user"})
    return name


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
            if cfg(c, "default_model") == name:
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
            out["key_expires"] = mktime(*map(int, v.split("-")), 23, 59, 59) if v else None
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


@functools.lru_cache(maxsize=64)
def _terms_re(terms):
    return re.compile("|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)), re.I) if terms else None


def redact_text(s, kinds=None, terms=None):
    """Hide sensitive values. kinds / terms: the mask_types and org_terms settings (default: the global ones)."""
    kinds = set(cfg(None, "mask_types") if kinds is None else kinds)
    terms = _terms_re(tuple(cfg(None, "org_terms") if terms is None else terms))
    if terms:
        s = terms.sub("[REDACTED_TERM]", s)
    if "secret" in kinds:
        s = _SECRET.sub("[REDACTED_SECRET]", s)
    if "iban" in kinds:
        s = _IBAN.sub("[REDACTED_IBAN]", s)
    if "card" in kinds:
        s = _CARD.sub(lambda m: "[REDACTED_CARD]" if _luhn(re.sub(r"\D", "", m[0])) else m[0], s)
    if "id" in kinds:
        s = _ID.sub(lambda m: "[REDACTED_ID]" if _il_id(m[0]) else m[0], s)
    if "phone" in kinds:
        s = _PHONE.sub("[REDACTED_PHONE]", s)
    if "email" in kinds:
        s = _EMAIL.sub("[REDACTED_EMAIL]", s)
    if "bank" in kinds:
        s = _BANK.sub(lambda m: m[1] + "[REDACTED_BANK]", s)
    if "passport" in kinds:
        s = _PASSPORT.sub(lambda m: m[1] + "[REDACTED_PASSPORT]", s)
    return s


def redactor(team):
    """redact_text with the team's own sensitive-data settings, when it has them."""
    kinds, terms = cfg(None, "mask_types", team), tuple(cfg(None, "org_terms", team))
    return lambda s: redact_text(s, kinds, terms)


def redact(obj, fn=None):
    fn = fn or redact_text
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [redact(v, fn) for v in obj]
    if isinstance(obj, dict):
        return {k: redact(v, fn) for k, v in obj.items()}
    return obj


def mask_answer(s):
    """Answers: only access keys and credentials are masked (an answer may rightly contain an email or a phone).
    The mask_answer_secrets setting turns it off."""
    return _SECRET.sub("[REDACTED_SECRET]", s) if cfg(None, "mask_answer_secrets") else s


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
        if _inflight[name] >= cfg(None, "max_concurrent"):
            return False
        _inflight[name] += 1
        return True


def inflight_leave(name):
    with _hits_lock:
        _inflight[name] -= 1


def login_fails(ip, add=False):
    """Wrong passwords from this address in the last login_ip_minutes (after recording one more if add)."""
    now, minutes = time.time(), cfg(None, "login_ip_minutes")
    with _hits_lock:
        q = _login_fails[ip]
        while q and q[0] < now - minutes * 60:
            q.popleft()
        if add:
            q.append(now)
        return len(q)


# --- budgets ---

def day_start(t=None):
    lt = localtime(t)
    return mktime(lt.tm_year, lt.tm_mon, lt.tm_mday)


def team_models(c, team):
    """The models a team may use, or None when the team sets no limit (no list, or no team)."""
    row = c.execute("select models from teams where name = ?", (team,)).fetchone() if team else None
    if not row or not row[0]:
        return None
    return [m for m in row[0].split(",") if m] or None


def effective_models(c, acct):
    """What the account may really use: its own models, narrowed by its team's list when the team has one."""
    allowed = team_models(c, acct["team"])
    return [m for m in acct["models"].split(",") if m and (allowed is None or m in allowed)]


def authorize(c, acct, alias):
    """None if the account may call this model now, else (http status, message, reason code)."""
    if alias in ALL_MODELS and alias not in MODELS and alias in acct["models"].split(","):
        return 403, f"model '{alias}' is turned off by the administrator", "model-off"
    if alias not in MODELS or alias not in acct["models"].split(","):
        return 403, f"model '{alias}' not allowed", "model-not-allowed"
    if alias not in effective_models(c, acct):
        return 403, f"model '{alias}' not allowed for team", "model-not-allowed-team"
    over = over_budget(c, acct)
    if over:
        mode = cfg(c, "budget_exhausted")
        if mode == "alert":  # allowed; the admin hears about it once a day per account
            if not c.execute("select 1 from security_events where kind = 'budget-exceeded' and name = ? and ts >= ?",
                             (acct["name"], day_start())).fetchone():
                with c:
                    security.event(c, "budget-exceeded", acct["name"], {"reason": over[1]})
        elif not (mode == "cheap" and alias == cfg(c, "auto_cheap")):
            return 402, over[0], over[1]
    if acct["daily_tokens"] and c.execute("select coalesce(sum(tokens_in + tokens_out), 0) from logs where name = ? and ts >= ?",
                                          (acct["name"], day_start())).fetchone()[0] >= acct["daily_tokens"]:
        return 429, "daily token quota reached", "daily-quota"
    if not rate_ok(acct["name"], acct["rpm"]):
        return 429, f"rate limit: {acct['rpm']} requests per minute", "rate-limit"
    return None


def over_budget(c, acct):
    """(message, reason code) when the person's or their team's monthly budget is used up, else None."""
    # ponytail: check-then-charge, concurrent requests can overshoot a budget by one request each
    if acct["budget"] and acct["spent"] >= acct["budget"]:  # 0 = no personal cap, like teams
        return "personal monthly budget exhausted", "budget"
    team = c.execute("select budget, spent from teams where name = ?", (acct["team"],)).fetchone()
    if team and team["budget"] and team["spent"] >= team["budget"]:
        return "team monthly budget exhausted", "team-budget"
    return None


def budget_switch(c, acct, alias, path=None):
    """When the budget is used up and the budget_exhausted setting says "cheap": the automatic choice's cheap model, if the
    person may use it (and, for apps, it speaks the same request format). Otherwise alias, which authorize() then blocks."""
    cheap = cfg(c, "auto_cheap")
    if (cfg(c, "budget_exhausted") != "cheap" or alias == cheap or cheap not in MODELS
            or cheap not in effective_models(c, acct) or not over_budget(c, acct)
            or (path and PROVIDERS[MODELS[cheap][0]][0] != path)):
        return alias
    return cheap


def policy(c, team=None):
    """(injection policy: block|log, sensitive-data policy: mask|block|log|local): the settings, or the team's own.
    local: a question with sensitive data goes, unmasked, to a model on the company's own server (mask when there is none)."""
    return cfg(c, "policy_injection", team), cfg(c, "policy_sensitive", team)


SENSITIVE_POLICIES = ("mask", "block", "log", "local")


def local_models(c, acct):
    """The account's models (team policy included) that are on and run on the company's own server."""
    return [a for a in effective_models(c, acct) if a in MODELS and MODELS[a][0] == "local"]


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
    """Security event (once per account per day) when the last hour cost more than max(spike_min, spike_factor x the
    account's average hour over the 7 days before it): $5 and 5x by default."""
    now, least, factor = time.time(), cfg(c, "spike_min"), cfg(c, "spike_factor")
    hour = c.execute("select coalesce(sum(cost), 0) from logs where name = ? and ts >= ?", (name, now - 3600)).fetchone()[0]
    if hour <= least:
        return
    week = c.execute("select coalesce(sum(cost), 0) from logs where name = ? and ts >= ? and ts < ?",
                     (name, now - 7 * 86400 - 3600, now - 3600)).fetchone()[0]
    if hour > max(least, factor * week / 168) and not c.execute(
            "select 1 from security_events where kind = 'cost-spike' and name = ? and ts >= ?", (name, day_start())).fetchone():
        security.event(c, "cost-spike", name, {"hour": round(hour, 4), "average": round(week / 168, 4)})


def new_usage():
    return {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}


def price_usage(price_in, price_out, price_cached, u):
    """Dollar cost of one call. Writing to the provider's cache costs 1.25x input; reading back costs price_cached."""
    return (u["in"] * price_in + u["cache_write"] * price_in * 1.25 + u["cache_read"] * price_cached + u["out"] * price_out) / 1e6


def log_call(c, name, team, model, u, cost, request, response, note="", request_id=None):
    """u may also carry "ms" / "ttft" (speed), "status" (the provider's answer) and "estimated" (token counts guessed).
    With the log_content setting at "metadata" the question and answer are not stored at all."""
    note = "; ".join(x for x in (note, "estimated" if u.get("estimated") else "") if x)
    if cfg(c, "log_content") == "metadata":
        request = response = None
    c.execute("insert into logs(ts, name, team, model, tokens_in, tokens_out, cost, request, response, cache_read, cache_write, note,"
              " request_id, latency_ms, ttft_ms, status) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (time.time(), name, team, model, u["in"] + u["cache_read"] + u["cache_write"], u["out"], cost, encrypt(request),
               encrypt(response), u["cache_read"], u["cache_write"], note or None, request_id, u.get("ms"), u.get("ttft"), u.get("status")))


def charge(c, acct, alias, u, request, response, note="", request_id=None):
    _, real, price_in, price_out = ALL_MODELS[alias]
    cost = price_usage(price_in, price_out, MODEL_EXTRA.get(alias, {}).get("price_cached", price_in * 0.1), u)
    with c:
        c.execute("update accounts set spent = spent + ? where name = ?", (cost, acct["name"]))
        c.execute("update teams set spent = spent + ? where name = ?", (cost, acct["team"]))
        log_call(c, acct["name"], acct["team"], real, u, cost, request, response, note, request_id)
        check_spike(c, acct["name"])
    soft = cfg(c, "soft_limit") / 100
    if acct["budget"] and acct["spent"] < acct["budget"] * soft <= acct["spent"] + cost:
        print(f"WARNING: {acct['name']} passed {soft:.0%} of budget (${acct['budget']})", flush=True)
    return cost


def month_bounds(t=None):
    """Start and end of the budget month holding t: local midnight on the budget_reset_day setting (1-28) to the same day
    a month later. A budget month is named after the calendar month it starts in."""
    day, lt = cfg(None, "budget_reset_day"), localtime(t)
    y, m = lt.tm_year, lt.tm_mon
    if lt.tm_mday < day:
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return mktime(y, m, day), mktime(ny, nm, day)


def excerpt(raw, question, n=2000):
    """Readable start of a logged question (the newest user message) or answer (the text, not the provider's JSON)."""
    try:
        d = json.loads(raw)
    except (TypeError, ValueError):
        return (raw or "")[:n]
    if question:
        msgs = d.get("messages") if isinstance(d, dict) else d
        text = last_user_text(msgs) if isinstance(msgs, list) else ""
    elif isinstance(d, dict):
        content, choices = d.get("content"), d.get("choices")
        text = (content[0].get("text") if isinstance(content, list) and content and isinstance(content[0], dict) else None) or \
               (((choices[0] or {}).get("message") or {}).get("content") if isinstance(choices, list) and choices else None)
    else:
        text = None
    return (text if isinstance(text, str) else raw)[:n]


def account_page(c, a):
    """Everything one person did: totals, last 30 days, models, latest requests, security, changes, saved chats.
    Never the key or password hashes."""
    name, start = a["name"], month_bounds()[0]
    prev = month_bounds(start - 1)[0]
    total = lambda lo, hi: dict(c.execute(
        "select count(*) requests, coalesce(sum(tokens_in), 0) tokens_in, coalesce(sum(tokens_out), 0) tokens_out,"
        " coalesce(sum(cost), 0) cost from logs where name = ? and ts >= ? and ts < ?", (name, lo, hi)).fetchone())
    this_month, last_month = total(start, time.time() + 1), total(prev, start)
    projected, recommended = forecast(a["spent"], last_month["cost"])
    has_key = bool(a["key_hash"])
    detail = lambda raw: (lambda d: {**d, "excerpt": decrypt(d["excerpt"])} if isinstance(d, dict) and "excerpt" in d else d)(json.loads(raw))
    return {
        "account": {"name": name, "team": a["team"], "models": a["models"].split(","), "budget": a["budget"], "spent": a["spent"],
                    "projected": projected, "recommended": recommended, "last_month": last_month["cost"], "rpm": a["rpm"],
                    "daily_tokens": a["daily_tokens"], "key_prefix": a["key_prefix"] if has_key else None,
                    "key_expires": a["key_expires"] if has_key else None, "key_created": a["key_created"] if has_key else None,
                    "has_password": bool(a["pw_hash"]), "locked": a["locked_until"] > time.time(), "archived": a["archived"]},
        "this_month": this_month, "last_month": last_month,
        "daily": [dict(r) for r in c.execute(
            "select date(ts, 'unixepoch', 'localtime') day, sum(cost) cost, count(*) requests from logs"
            " where name = ? and ts >= ? group by day order by day", (name, time.time() - 30 * 86400))],
        "models": [dict(r) for r in c.execute(
            "select model, count(*) requests, sum(tokens_in) tokens_in, sum(tokens_out) tokens_out, sum(cost) cost from logs"
            " where name = ? and ts >= ? group by model order by cost desc", (name, start))],
        "requests": [{"ts": r["ts"], "model": r["model"], "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"], "cost": r["cost"],
                      "note": r["note"], "request_id": r["request_id"], "question": excerpt(decrypt(r["request"]), True),
                      "answer": excerpt(decrypt(r["response"]), False)} for r in c.execute(
            "select * from logs where name = ? order by ts desc limit 100", (name,))],
        "events": [{"ts": r["ts"], "kind": r["kind"], "name": r["name"], "detail": detail(r["detail"])} for r in c.execute(
            "select * from security_events where name = ? order by ts desc limit 50", (name,))],
        "blocked": [{**dict(r), "excerpt": decrypt(r["excerpt"])} for r in c.execute(
            "select ts, reason, model, request_id, excerpt from blocked_requests where name = ? order by ts desc limit 50", (name,))],
        # this person's own changes: account actions, and archive/restore of the account or of their chats (not a team of the same name)
        "audit": [{"ts": r["ts"], "action": r["action"], "detail": json.loads(r["detail"])} for r in c.execute(
            "select ts, action, detail from audit where json_extract(detail, '$.name') = ? and (action in"
            " ('create', 'update', 'delete', 'key-new', 'key-revoke') or (action in ('archive', 'restore') and"
            " json_extract(detail, '$.kind') in ('account', 'chat'))) order by ts desc limit 50", (name,))],
        "conversations": {
            "count": c.execute("select count(*) from conversations where name = ? and archived is null", (name,)).fetchone()[0],
            "archived": c.execute("select count(*) from conversations where name = ? and archived is not null", (name,)).fetchone()[0],
            "recent": [{"title": decrypt(r["title"]), "updated": r["updated"]} for r in c.execute(
                "select title, updated from conversations where name = ? and archived is null order by updated desc limit 10", (name,))]},
    }


def forecast(spent, last_month):
    """Projected spend at month end, and a recommended monthly budget (20% headroom, rounded up to $5)."""
    # ponytail: straight-line projection from days elapsed; good enough until usage has strong weekly patterns
    start, end = month_bounds()
    elapsed = max(time.time() - start, 86400) / (end - start)
    projected = spent / min(elapsed, 1)
    base = max(projected, last_month)
    return round(projected, 4), (math.ceil(base * 1.2 / 5) * 5 if base > 0 else 0)


def put_setting(c, key, value):
    c.execute("insert into settings values (?, ?) on conflict(key) do update set value = excluded.value", (key, value))


# --- one month's numbers: the reports page, the chargeback export and the monthly summary all count the same way ---
TEST_CALLS = "(בדיקת מודל)"  # connection tests from the models page: logged, but not anyone's usage


def month_start(month):
    """Start of the budget month named like 2026-10: local midnight on the reset day of that month."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(month or ""))
    if not m or not 1 <= int(m[2]) <= 12:
        raise ValueError("month must look like 2026-10")
    return mktime(int(m[1]), int(m[2]), cfg(None, "budget_reset_day"))


def month_of(t):
    """The name (2026-10) of the budget month holding t."""
    lt = localtime(month_bounds(t)[0])
    return f"{lt.tm_year:04d}-{lt.tm_mon:02d}"


def recount_spent(c):
    """This budget month's spending, counted again from the log: after the reset day or the time zone changes, the running
    totals would otherwise belong to the old month boundaries."""
    start, month = month_bounds()[0], month_of(time.time())
    c.execute("update accounts set spent = (select coalesce(sum(cost), 0) from logs where logs.name = accounts.name and ts >= ?),"
              " month = ?", (start, month))
    c.execute("update teams set spent = (select coalesce(sum(cost), 0) from logs where logs.team = teams.name and ts >= ?),"
              " month = ?", (start, month))


def last_full_month(now=None):
    return month_of(month_bounds(now)[0] - 1)


def month_report(c, month):
    start = month_start(month)
    end = month_bounds(start)[1]
    first = c.execute("select min(ts) from logs").fetchone()[0] or time.time()
    months, t = [], month_bounds()[0]
    while t >= month_bounds(first)[0] and len(months) < 36:
        months.append(month_of(t))
        t = month_bounds(t - 1)[0]

    def group(col):
        return [dict(r) for r in c.execute(
            f"select {col} key, count(*) requests, sum(tokens_in) tokens_in, sum(tokens_out) tokens_out, sum(cost) cost,"
            f" sum(cache_read) cache_read from logs where ts >= ? and ts < ? and name != ?"
            f" group by {col} order by cost desc", (start, end, TEST_CALLS))]
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
                       " where ts >= ? and ts < ? and name != ?", (start, end, TEST_CALLS)).fetchone()
    return {"month": month, "months": months, "totals": dict(totals), "by_team": by_team, "by_account": by_account,
            "by_model": group("model")}


# --- savings recommendations: where the same work could cost less ---
# a "short question" (simple_tokens_in / _out settings) and the smallest saving worth showing (savings_min) are settings
STRONG_FACTOR = 2  # a model is "strong" when it is the automatic choice's strong model, or costs (in + out) this many times the cheap one
CONCENTRATION = 0.8  # a team spending more than this share on its provider's priciest model gets a recommendation
SAVINGS_DAYS = 30
SAVINGS_ORDER = {"simple-questions": 0, "concentrated": 1, "unused-model": 2}


def usd(v):
    return f"${v:,.0f}" if v >= 10 else f"${v:,.2f}"


def model_price(alias):
    return ALL_MODELS[alias][2] + ALL_MODELS[alias][3]


def cheap_for(c, alias):
    """Where alias's simple questions could go: the automatic choice's cheap model when it is the same provider, else the
    provider's cheapest model that is on. None when alias isn't a strong model or nothing cheaper is on."""
    provider = ALL_MODELS[alias][0]
    auto = cfg(c, "auto_cheap")
    if auto in MODELS and auto != alias and MODELS[auto][0] == provider:
        cheap = auto
    else:
        cheap = min((a for a, m in MODELS.items() if m[0] == provider and a != alias), key=model_price, default=None)
    if not cheap or model_price(cheap) >= model_price(alias):
        return None
    strong = alias == cfg(c, "auto_strong") or model_price(alias) >= STRONG_FACTOR * model_price(cheap)
    return cheap if strong else None


def savings(c, now=None):
    """Recommendations from the last 30 days, biggest monthly saving first:
    simple-questions: short questions (few tokens in and out) a team, or an account without a team, sent to a strong model,
      re-priced at the same provider's cheap model (cache reads and writes too);
    concentrated: a team spending over 80% on its provider's priciest model;
    unused-model: a model that is on but nobody used for 30 days (and that is older than that)."""
    now = time.time() if now is None else now
    since = now - SAVINGS_DAYS * 86400
    short_in, short_out, least = cfg(c, "simple_tokens_in"), cfg(c, "simple_tokens_out"), cfg(c, "savings_min")
    labels = {r[0]: r[1] or r[0] for r in c.execute("select alias, label from models")}
    alias_of = {}  # logs keep the provider's model name; an enabled alias wins over a disabled one with the same name
    for a, m in [*MODELS.items(), *ALL_MODELS.items()]:
        alias_of.setdefault(m[1], a)
    teams = {r[0] for r in c.execute("select name from teams where archived is null")}
    accounts = {r[0] for r in c.execute("select name from accounts where archived is null and team = ''")}
    first = c.execute("select min(ts) from logs where ts >= ? and name not like '(%'", (since,)).fetchone()[0]
    # ponytail: straight scale-up to 30 days; under a week of history counts as a week, so one busy day isn't taken for a month
    days = min(max((now - first) / 86400 if first else SAVINGS_DAYS, 7), SAVINGS_DAYS)
    scale = SAVINGS_DAYS / days
    out = []

    def rec(kind, team, account, src, dst, requests, current, projected, saving, text):
        out.append({"kind": kind, "team": team, "account": account, "from_model": src, "to_model": dst,
                    "from_label": labels.get(src, src), "to_label": labels.get(dst, dst) if dst else None, "requests": requests,
                    "current_cost": round(current, 2), "projected_cost": None if projected is None else round(projected, 2),
                    "monthly_saving": round(saving, 2), "text_he": text})

    # one pass over the 30 days (the log rows are wide, so each scan is slow): per team, person and model, all usage and,
    # separately, the usage of the short questions
    groups, spend, used = {}, {}, set()  # groups: (team, account without a team, model) -> its short questions' usage
    for r in c.execute("select team, name, model, count(*) n, sum(cost) cost, sum(short) s_n, sum(short * (tokens_in - cache_read - cache_write)) s_in,"
                       " sum(short * tokens_out) s_out, sum(short * cache_read) s_cr, sum(short * cache_write) s_cw, sum(short * cost) s_cost"
                       " from (select team, name, model, cost, tokens_in, tokens_out, cache_read, cache_write,"
                       " (tokens_in <= ? and tokens_out <= ?) short from logs where ts >= ? and name not like '(%') group by team, name, model",
                       (short_in, short_out, since)):
        used.add(r["model"])
        if (r["team"] not in teams) if r["team"] else (r["name"] not in accounts):
            continue  # archived teams and people
        if r["team"]:
            n, cost = spend.setdefault(r["team"], {}).get(r["model"], (0, 0.0))
            spend[r["team"]][r["model"]] = (n + r["n"], cost + (r["cost"] or 0))
        if r["s_n"]:
            g = groups.setdefault((r["team"], "" if r["team"] else r["name"], r["model"]),
                                  {"n": 0, "in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "cost": 0.0})
            for k, v in (("n", r["s_n"]), ("in", r["s_in"]), ("out", r["s_out"]), ("cache_read", r["s_cr"]), ("cache_write", r["s_cw"]),
                         ("cost", r["s_cost"])):
                g[k] += v or 0
    for (team, account, real), g in groups.items():
        src = alias_of.get(real)
        dst = cheap_for(c, src) if src else None
        allowed = team_models(c, team)
        if not dst or (allowed is not None and dst not in allowed):
            continue
        _, _, price_in, price_out = ALL_MODELS[dst]
        current, projected = g["cost"] * scale, price_usage(price_in, price_out, MODEL_EXTRA[dst]["price_cached"], g) * scale
        if current - projected < least:
            continue
        who = f"צוות {team}" if team else account
        rec("simple-questions", team, account, src, dst, g["n"], current, projected, current - projected,
            f"{who} שולח שאלות קצרות למודל החזק {labels[src]}. מעבר ל-{labels[dst]} בשאלות כאלה יחסוך כ-{usd(current - projected)} בחודש.")

    for team, by in spend.items():
        total = sum(cost for _, cost in by.values())
        real, (n, top) = max(by.items(), key=lambda kv: kv[1][1])
        src = alias_of.get(real)
        if total * scale < least or top <= total * CONCENTRATION or src not in MODELS:
            continue
        same = sorted((a for a, m in MODELS.items() if m[0] == MODELS[src][0]), key=model_price)
        allowed = team_models(c, team)
        down = [a for a in same if model_price(a) < model_price(src) and (allowed is None or a in allowed)]
        if same[-1] != src or not down:
            continue  # not the provider's priciest model, or nothing cheaper the team may use
        dst = down[-1]  # one step down: the priciest of the cheaper ones
        rec("concentrated", team, "", src, dst, n, top * scale, None, 0,
            f"{round(top / total * 100)}% מההוצאה של צוות {team} הולכים ל-{labels[src]}, המודל היקר ביותר של הספק. "
            f"כדאי לבדוק אם חלק מהעבודה מתאים ל-{labels[dst]}.")

    for r in c.execute("select alias, model, created from models where enabled = 1 and archived is null order by created, alias"):
        if r["model"] not in used and r["alias"] != cfg(c, "default_model") and (r["created"] or now) < since:
            rec("unused-model", "", "", r["alias"], None, 0, 0, None, 0,
                f"המודל {labels[r['alias']]} פעיל, אבל אף אחד לא השתמש בו ב-30 הימים האחרונים. כדאי לכבות אותו עד שיהיה בו צורך.")
    out.sort(key=lambda x: (-x["monthly_saving"], SAVINGS_ORDER[x["kind"]]))
    return {"recommendations": out, "total_monthly_saving": round(sum(x["monthly_saving"] for x in out), 2), "days": round(days, 1),
            "simple_tokens_in": short_in, "simple_tokens_out": short_out}


# --- chargeback: each team's month, with its accounting codes, for the finance system ---
NO_TEAM = "ללא צוות"
CHARGEBACK_FIELDS = ("month", "team", "cost_center", "gl_account", "requests", "tokens_in", "tokens_out", "cost_usd")


def chargeback(c, month):
    """One row per team that used the gateway in the month (accounts without a team together), plus the total.
    Counted like the monthly report, so the totals match it."""
    start = month_start(month)
    end = month_bounds(start)[1]
    codes = {r["name"]: r for r in c.execute("select name, cost_center, gl_account from teams")}
    rows = []
    for r in c.execute("select team, count(*) requests, coalesce(sum(tokens_in), 0) tokens_in, coalesce(sum(tokens_out), 0) tokens_out,"
                       " coalesce(sum(cost), 0) cost from logs where ts >= ? and ts < ? and name != ? group by team"
                       " order by team = '', cost desc", (start, end, TEST_CALLS)):
        t = codes.get(r["team"]) if r["team"] else None
        rows.append({"month": month, "team": r["team"] or NO_TEAM, "cost_center": (t["cost_center"] if t else None) or "",
                     "gl_account": (t["gl_account"] if t else None) or "", "requests": r["requests"], "tokens_in": r["tokens_in"],
                     "tokens_out": r["tokens_out"], "cost_usd": round(r["cost"], 2)})
    total = {"month": month, "team": "TOTAL", "cost_center": "", "gl_account": "",
             **{k: sum(r[k] for r in rows) for k in ("requests", "tokens_in", "tokens_out")},
             "cost_usd": round(sum(r["cost_usd"] for r in rows), 2)}  # the sum of the rounded rows, so the file adds up
    return {"month": month, "rows": rows, "total": total}


def chargeback_csv(data):
    """CSV for accounting import: English snake_case headers, UTF-8 with a byte-order mark (Excel then reads Hebrew team
    names), and a text cell that Excel would run as a formula (= + - @) gets a leading apostrophe."""
    def cell(k, v):
        if k == "cost_usd":
            return f"{v:.2f}"
        return "'" + v if isinstance(v, str) and v and v[0] in "=+-@\t\r" else v
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(CHARGEBACK_FIELDS)
    for r in data["rows"] + [data["total"]]:
        w.writerow([cell(k, r[k]) for k in CHARGEBACK_FIELDS])
    return "﻿" + buf.getvalue()


# --- monthly summary by email to management ---
HE_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
SEC_KINDS_HE = {"suspicious-prompt": "שאלות חשודות", "sensitive-data-masked": "מידע רגיש שהוסתר", "sensitive-data-blocked": "שאלות עם מידע רגיש שנחסמו",
                "sensitive-data-logged": "מידע רגיש שנשלח בלי הסתרה", "dangerous-answer": "תשובות עם פקודה מסוכנת",
                "cross-site-request": "בקשות מאתר זר", "bad-host": "כתובות לא מוכרות", "account-locked": "חשבונות שננעלו",
                "admin-denied": "סיסמת מנהל שגויה מבחוץ", "document-refused": "מסמכים חשודים שלא נקלטו", "document-forced": "מסמכים חשודים שהועלו באישור",
                "document-flagged": "מסמכים חשודים שנשלחו למודל", "answer-masked": "מפתחות שהוסתרו מתשובות", "suspicious-link": "קישורים חשודים בתשובות",
                "prompt-leak": "תשובות שחשפו את הוראות השער", "mcp-tool-refused": "כלי MCP שלא הופעלו", "cost-spike": "הוצאות חריגות",
                "login-throttled": "יותר מדי סיסמאות שגויות מכתובת אחת", "summary-failed": "שליחות סיכום שנכשלו",
                "sensitive-routed-local": "שאלות עם מידע רגיש שנענו במודל המקומי"}
SUMMARY_TRIES = 3  # sent on the summary_day after summary_hour; a failed send is tried again next hour, 3 times at most
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def month_title(month):
    y, m = map(int, month.split("-"))
    return f"{HE_MONTHS[m - 1]} {y}"


def summary_content(c, month):
    """The email: subject, an RTL HTML part and a plain-text part, from the same numbers as the reports page. Every name in
    it (people, teams, models) is escaped: they are typed by admins and could hold markup."""
    r, before = month_report(c, month), month_report(c, last_full_month(month_start(month)))
    start = month_start(month)
    end = month_bounds(start)[1]
    alias_of = {m[1]: a for a, m in ALL_MODELS.items()}
    labels = dict(c.execute("select alias, label from models").fetchall())
    money = lambda v: f"${v or 0:,.2f}"
    total, prev = r["totals"]["cost"], before["totals"]["cost"]
    events = c.execute("select kind, count(*) n from security_events where ts >= ? and ts < ? group by kind order by n desc",
                       (start, end)).fetchall()
    blocked = c.execute("select count(*) from blocked_requests where ts >= ? and ts < ?", (start, end)).fetchone()[0]
    over = [[f"צוות {x['key']}", money(x["cost"]), money(x["budget"])] for x in r["by_team"] if x["key"] and x["budget"] and x["cost"] > x["budget"]] + \
           [[x["key"], money(x["cost"]), money(x["budget"])] for x in r["by_account"] if x["budget"] and x["cost"] > x["budget"]]
    sv = savings(c)
    sections = [
        ("ההוצאה בחודש", None, [
            ["הוצאה כוללת", money(total)],
            ["החודש הקודם", money(prev) + (f" ({(total - prev) / prev * 100:+.0f}%)" if prev else "")],
            ["בקשות", f"{r['totals']['requests']:,}"], ["אנשים ואפליקציות שהשתמשו", str(r["totals"]["people"])]]),
        ("הצוותים שהוציאו הכי הרבה", ["צוות", "בקשות", "הוצאה"],
         [[x["key"] or NO_TEAM, f"{x['requests']:,}", money(x["cost"])] for x in r["by_team"][:5]]),
        ("המשתמשים שהוציאו הכי הרבה", ["שם", "צוות", "הוצאה"],
         [[x["key"], x["team"] or NO_TEAM, money(x["cost"])] for x in r["by_account"][:5]]),
        ("הוצאה לפי מודל", ["מודל", "בקשות", "הוצאה"],
         [[labels.get(alias_of.get(x["key"])) or x["key"], f"{x['requests']:,}", money(x["cost"])] for x in r["by_model"]]),
        ("המלצות לחיסכון", None,
         ([[f"אפשר לחסוך עד {usd(sv['total_monthly_saving'])} בחודש", ""]] if sv["total_monthly_saving"] else []) +
         [[x["text_he"], ""] for x in sv["recommendations"][:3]]),
        ("אבטחה", None, [[SEC_KINDS_HE.get(e["kind"], e["kind"]), str(e["n"])] for e in events] + [["בקשות שנחסמו", str(blocked)]]),
        ("חריגות מהתקציב", ["מי", "הוצאה", "תקציב"], over),
    ]
    org = cfg(c, "org_name")
    subject = f"FireGate · {org + ' · ' if org else ''}סיכום חודשי · {month_title(month)}"
    lead, foot = (f"השימוש בבינה מלאכותית ב{org or 'חברה'} ב{month_title(month)}.",
                  "נשלח אוטומטית מהשער. ההמלצות לחיסכון מבוססות על 30 הימים האחרונים, והחריגות על התקציב הנוכחי.")
    e = html.escape
    cell = "padding:6px 8px;border-bottom:1px solid #e4e4e7;text-align:right;vertical-align:top"
    parts = [f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{e(subject)}</title></head>'
             '<body style="margin:0;padding:24px;background:#f4f4f5;color:#18181b;font-family:Arial,Helvetica,sans-serif;direction:rtl;text-align:right">'
             '<div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:12px;padding:24px">'
             f'<h1 style="font-size:20px;margin:0 0 4px">{e(subject)}</h1><p style="margin:0 0 8px;color:#52525b">{e(lead)}</p>']
    text = [subject, "", lead]
    for title, head, rows in sections:
        parts.append(f'<h2 style="font-size:16px;margin:24px 0 8px">{e(title)}</h2>')
        text += ["", title, "-" * len(title)]
        if not rows:
            parts.append('<p style="margin:0;color:#52525b">אין.</p>')
            text.append("אין.")
            continue
        parts.append('<table role="presentation" style="width:100%;border-collapse:collapse;font-size:14px">')
        if head:
            parts.append("<tr>" + "".join(f'<th style="{cell};color:#52525b">{e(h)}</th>' for h in head) + "</tr>")
            text.append(" | ".join(head))
        for row in rows:
            parts.append("<tr>" + "".join(f'<td style="{cell}">{e(str(v))}</td>' for v in row) + "</tr>")
            text.append(" | ".join(str(v) for v in row if v != ""))
        parts.append("</table>")
    parts.append(f'<p style="margin:24px 0 0;font-size:12px;color:#71717a">{e(foot)}</p></div></body></html>')
    return {"subject": subject, "html": "".join(parts), "text": "\n".join(text + ["", foot]) + "\n"}


def smtp_settings():
    """The mail server for the monthly summary (the smtp_* settings; the password is never sent to a page), or None."""
    host, sender = cfg(None, "smtp_host"), cfg(None, "smtp_from") or cfg(None, "smtp_user")
    if not host or not sender:
        return None
    return {"host": host, "port": cfg(None, "smtp_port"), "user": cfg(None, "smtp_user"), "password": cfg(None, "smtp_password"),
            "from": sender, "tls": cfg(None, "smtp_tls")}


def parse_recipients(raw):
    """Comma-separated email addresses -> list, each checked."""
    out = list(dict.fromkeys(a for a in re.split(r"[,;\s]+", str(raw or "")) if a))
    for a in out:
        if len(a) > 254 or not EMAIL.match(a):
            raise ValueError(f"not a valid email address: {a[:100]}")
    if len(out) > 50:
        raise ValueError("at most 50 recipients")
    return out


def mask_email(addr):
    """d***@example.com: enough for the server log to tell which address, not enough to collect them."""
    name, _, domain = addr.partition("@")
    return name[:1] + "***@" + domain if domain else "***"


def mask_emails(text):
    return _EMAIL.sub(lambda m: mask_email(m[0]), text)


def send_mail(to, subject, text, html_part=None):
    """Send one email through the mail server in the settings. Raises ValueError when none is set, smtplib/OS errors when
    sending fails."""
    mail = smtp_settings()
    if not mail:
        raise ValueError("SMTP is not configured")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, mail["from"], ", ".join(to)
    msg.set_content(text)
    if html_part:
        msg.add_alternative(html_part, subtype="html")
    secure = ssl.create_default_context()
    if mail["tls"] == "ssl":  # port 465: encrypted from the first byte
        server = smtplib.SMTP_SSL(mail["host"], mail["port"], timeout=30, context=secure)
    else:
        server = smtplib.SMTP(mail["host"], mail["port"], timeout=30)
    with server as s:
        if mail["tls"] != "0" and mail["tls"] != "ssl":
            s.starttls(context=secure)
        if mail["user"]:
            s.login(mail["user"], mail["password"])
        s.send_message(msg, from_addr=mail["from"], to_addrs=to)


def send_summary(c, month):
    """Email the month's summary to the saved recipients now. Returns the recipients; raises ValueError when there is no mail
    server or no recipient, smtplib/OS errors when sending fails."""
    if not smtp_settings():
        raise ValueError("SMTP is not configured")
    to = cfg(c, "summary_recipients")
    if not to:
        raise ValueError("no summary recipients")
    content = summary_content(c, month)
    send_mail(to, content["subject"], content["text"], content["html"])
    print(f"monthly summary for {month} sent to {', '.join(mask_email(a) for a in to)}", flush=True)
    return to


def summary_sent(c, month, to, auto):
    """Remember that the month went out (the scheduler then won't send it again), in settings and in the change log."""
    put_setting(c, f"summary_sent_{month}", str(time.time()))
    audit(c, "summary-sent", {"name": "summary", "month": month, "recipients": len(to), "auto": auto})


def summary_status(c):
    sent = sorted((r[0].removeprefix("summary_sent_") for r in c.execute("select key from settings where key like 'summary_sent_%'")),
                  reverse=True)
    return {"recipients": ", ".join(cfg(c, "summary_recipients")), "enabled": cfg(c, "summary_enabled"),
            "smtp_configured": bool(smtp_settings()), "day": cfg(c, "summary_day"), "hour": cfg(c, "summary_hour"), "sent": sent[:12]}


def summary_tick(now=None):
    """Hourly: on the summary_day after summary_hour (1st, 08:00 by default), send last month's summary once. A failure is
    recorded as a security event and tried again next hour, 3 times at most. Returns True (sent), False (failed) or None."""
    now = time.time() if now is None else now
    c = db()
    try:
        lt = localtime(now)
        if lt.tm_mday != cfg(c, "summary_day") or lt.tm_hour < cfg(c, "summary_hour"):
            return None
        month = last_full_month(now)
        tries = int(setting(c, f"summary_tries_{month}", "0") or 0)
        if not cfg(c, "summary_enabled") or setting(c, f"summary_sent_{month}") or tries >= SUMMARY_TRIES:
            return None
        try:
            to = send_summary(c, month)
        except (ValueError, smtplib.SMTPException, OSError) as e:
            with c:
                put_setting(c, f"summary_tries_{month}", str(tries + 1))
                security.event(c, "summary-failed", "", {"month": month, "try": tries + 1,
                                                         "error": mask_emails(f"{type(e).__name__}: {e}")[:300]})
            print(f"monthly summary for {month} failed (try {tries + 1} of {SUMMARY_TRIES}): {type(e).__name__}", flush=True)
            return False
        with c:
            summary_sent(c, month, to, True)
        return True
    finally:
        c.close()


def backup_tick(now=None):
    """Hourly: a scheduled backup (backup_schedule daily / weekly) when the last one is that old. Returns the file or None."""
    now = time.time() if now is None else now
    c = db()
    try:
        every = {"daily": 86400, "weekly": 7 * 86400}.get(cfg(c, "backup_schedule"))
        if not every or now - float(setting(c, "backup_last", "0") or 0) < every - 600:  # 10 minutes' slack for the hourly check
            return None
        path = backup(c, "", cfg(c, "backup_folder"), "scheduled")
        with c:
            put_setting(c, "backup_last", str(now))
            audit(c, "backup", {"name": "backup", "file": os.path.basename(path), "auto": True})
        return path
    finally:
        c.close()


def summary_loop():
    # ponytail: assumes one gateway process; with several, two could send the same month at once (move to a DB lock then)
    while True:
        for tick in (summary_tick, backup_tick):
            try:
                tick()
            except Exception as e:  # noqa: BLE001  one bad hour must not stop next month's summary or backup
                print(f"hourly {tick.__name__} failed: {type(e).__name__}", flush=True)
        time.sleep(3600)


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
    Returns (status, raw response bytes, usage). Raises URLError if unreachable.
    usage also gets "ms" (the whole call) and "ttft" (until the first piece of answer text; the whole call when not streamed).
    The local model server: its own address, through the opener that refuses metadata/link-local addresses and redirects;
    when it reports no token counts they are estimated (about 4 characters a token) and marked "estimated"."""
    url, auth, send = provider_url(provider), provider_auth(provider), urllib.request.urlopen
    if provider == "local":
        if not cfg(None, "local_base_url"):
            raise urllib.error.URLError("no address set for the local model server")
        send = LOCAL_OPENER.open
    req = urllib.request.Request(url, json.dumps(body).encode(), {"content-type": "application/json", **auth})
    t0 = time.monotonic()
    ms = lambda: round((time.monotonic() - t0) * 1000)
    u = new_usage()
    try:
        r = send(req, timeout=300)
    except urllib.error.HTTPError as e:
        with e:
            data = e.read()  # provider error: nothing to charge
        u["ms"] = u["ttft"] = ms()
        return e.code, data, u
    answer = []
    with r:
        if not body.get("stream"):
            data = r.read()
            try:
                read_usage(json.loads(data), provider, u)
            except (ValueError, AttributeError):
                pass
            if provider == "local":
                answer.append(excerpt(data.decode(errors="replace"), False, len(data)))
            u["ms"] = u["ttft"] = ms()
        else:
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
                piece = delta_text(provider, ev)
                if piece:
                    answer.append(piece)
                    u.setdefault("ttft", ms())
                on_line(line, ev)
            data = b"".join(chunks)
            u["ms"] = ms()
            u.setdefault("ttft", u["ms"])
        if provider == "local" and r.status < 400 and not u["in"] and not u["out"]:
            u.update({"in": len(json.dumps(body.get("messages"), ensure_ascii=False)) // 4, "out": len("".join(answer)) // 4,
                      "estimated": True})
        return r.status, data, u


def check_local_url(url):
    """The local model server's base address as the admin typed it, checked like an MCP address except that company
    (private) addresses are the point: http(s) only, no user name or password in it, and a name that resolves to cloud
    metadata, link-local or (without the local_loopback setting) this machine is refused. Every connection checks again, so a
    name that changes its answer later is still caught. "" turns the local server off."""
    url = str(url or "").strip().rstrip("/")
    if not url:
        return ""
    p = urllib.parse.urlsplit(url)
    try:
        port = p.port
    except ValueError:
        port = -1
    if p.scheme not in ("http", "https") or not p.hostname or port == -1 or p.username or p.password or p.query or p.fragment:
        raise ValueError("local model server address must look like http://server:11434/v1")
    try:
        infos = socket.getaddrinfo(p.hostname, port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        return url  # not resolvable from here right now; the connection check will say so
    for *_, sa in infos:
        if mcp.blocked_ip(sa[0], loopback=cfg(None, "local_loopback"), private=True):
            raise ValueError(f"address {sa[0]} is not allowed for the local model server")
    return url


def local_list(url):
    """GET {url}/models on the local server: the model ids it offers (OpenAI format, as Ollama and vLLM answer)."""
    req = urllib.request.Request(url + "/models", headers=provider_auth("local"))
    t0 = time.monotonic()
    try:
        with LOCAL_OPENER.open(req, timeout=10) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}"}
    except (OSError, ValueError) as e:  # OSError: unreachable, refused address, timeout
        return {"ok": False, "error": str(getattr(e, "reason", e))[:300]}
    ids = [str(m.get("id")) for m in (d.get("data") if isinstance(d, dict) else None) or [] if isinstance(m, dict) and m.get("id")]
    return {"ok": True, "models": ids[:200], "ms": round((time.monotonic() - t0) * 1000)}


# --- meaning vectors for document search (OpenAI or Gemini embeddings; Anthropic has none) ---
# provider -> (env var for model, default model, $ per 1M tokens). Checked 2026-10-05.
EMBED_MODELS = {"openai": ("OPENAI_EMBED_MODEL", "text-embedding-3-small", 0.02),
                "gemini": ("GEMINI_EMBED_MODEL", "gemini-embedding-001", 0.15)}


def embed_provider():
    """Which provider computes meaning vectors: the embeddings setting (openai|gemini|off), by default the first one with
    a key. None also when the search_mode setting is "by words" only."""
    choice = cfg(None, "embeddings")
    if cfg(None, "search_mode") == "words":
        return None
    for p in (("openai", "gemini") if choice == "auto" else (choice,)):
        if p in EMBED_MODELS and provider_key(p):
            return p
    return None


def embed_texts(c, texts):
    """Meaning vectors for texts, or None if no provider or the call failed. The cost is logged, charged to nobody."""
    p = embed_provider()
    if not p or not texts:
        return None
    env, default, price = EMBED_MODELS[p]
    model = os.environ.get(env, default)
    url = provider_url(p).rsplit("/chat/completions", 1)[0] + "/embeddings"
    vecs, tokens = [], 0
    try:
        for i in range(0, len(texts), 64):
            req = urllib.request.Request(url, json.dumps({"model": model, "input": [t[:8000] for t in texts[i:i + 64]]}).encode(),
                                         {"content-type": "application/json", **provider_auth(p)})
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
settings.ENCRYPT, settings.DECRYPT = encrypt, decrypt
settings.CHECKS.update(local_url=lambda v: check_local_url(v),
                       model=lambda v: v if v in ALL_MODELS else (_ for _ in ()).throw(ValueError("unknown model")),
                       enabled_model=lambda v: v if v in MODELS else (_ for _ in ()).throw(ValueError("model is off or unknown")))
sources.CFG = lambda key: cfg(None, key)


# --- MCP knowledge sources ---
MCP_RESULT_CHARS = 3000  # per source per question
MCP_MAX_RESOURCES = 300


def mcp_config(row):
    return load_config(row["config"])


def load_config(raw):
    """A source's settings (stored encrypted: they hold the MCP server's token)."""
    try:
        conf = json.loads(decrypt(raw) or "{}")
        return conf if isinstance(conf, dict) else {}
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
        conf = mcp_config(row)
        tool, arg = str(conf.get("tool") or ""), str(conf.get("arg") or "query")
        if conf.get("mode") != "search" or not MCP_NAME.match(tool) or not MCP_NAME.match(arg):
            continue
        try:
            client = mcp.Client(row["path"], conf.get("token", ""))
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


# --- speed: how long answers take, per model and per provider ---
# slow alert: last hour's p95 above slow_factor x the 7 days before it, with at least slow_min answers in the hour (2x, 10).
# "prefer the fast model" trusts a model's median over the last fast_window_hours only from fast_min answers (24h, 20).


def pct(values, p):
    """Nearest-rank percentile of a sorted list; None when empty."""
    return values[max(0, math.ceil(p * len(values)) - 1)] if values else None


def speed_summary(items):
    """items: (latency ms, time to first token ms, status). Percentiles count answers only; errors and timeouts are rates."""
    good = [(ms, ttft) for ms, ttft, st in items if not st or st < 400]
    total, first = sorted(ms for ms, _ in good), sorted(ms if ttft is None else ttft for ms, ttft in good)
    n = len(items)
    errors, timeouts = sum(1 for *_, st in items if st and st >= 400), sum(1 for *_, st in items if st in (408, 504))
    return {"requests": n, "answers": len(good), "p50": pct(total, .5), "p95": pct(total, .95), "ttft_p50": pct(first, .5), "ttft_p95": pct(first, .95),
            "errors": errors, "error_rate": round(errors / n, 4) if n else 0, "timeouts": timeouts,
            "timeout_rate": round(timeouts / n, 4) if n else 0}


def latency(c, now=None):
    """Speed per model and per provider over the last 24 hours and 7 days, the median per provider for each of the last 48
    hours, and slow alerts (a model whose last-hour p95 is over slow_factor x its p95 in the 7 days before that hour).
    Test calls and document indexing don't count."""
    now = time.time() if now is None else now
    slow_factor, slow_min = cfg(c, "slow_factor"), cfg(c, "slow_min")
    info = {}  # the logs keep the provider's model name; models in use win over archived ones with the same name
    for r in c.execute("select alias, label, provider, model from models order by archived is not null, created"):
        info.setdefault(r["model"], {"alias": r["alias"], "label": r["label"] or r["alias"], "provider": r["provider"]})
    week, base_from = now - 7 * 86400, now - 7 * 86400 - 3600
    by_model, by_provider, hours = {}, {}, {}
    for ts, model, ms, ttft, st in c.execute(
            "select ts, model, latency_ms, ttft_ms, status from logs where ts >= ? and latency_ms is not null and name not like '(%'",
            (base_from,)):
        if model not in info:
            continue
        item, p = (ms, ttft, st), info[model]["provider"]
        for groups, key in ((by_model, model), (by_provider, p)):
            g = groups.setdefault(key, {"hour": [], "day": [], "week": [], "base": []})
            if ts >= now - 3600:
                g["hour"].append(item)
            else:
                g["base"].append(item)
            if ts >= now - 86400:
                g["day"].append(item)
            if ts >= week:
                g["week"].append(item)
        if ts >= now - 48 * 3600 and (not st or st < 400):
            hours.setdefault((int(ts // 3600) * 3600, p), []).append(ms)
    models, alerts = [], []
    for model, g in by_model.items():
        hour, base = speed_summary(g["hour"]), speed_summary(g["base"])
        slow = hour["answers"] >= slow_min and bool(base["p95"]) and hour["p95"] > slow_factor * base["p95"]
        models.append({"model": model, **info[model], "day": speed_summary(g["day"]), "week": speed_summary(g["week"]),
                       "hour": hour, "slow": slow})
        if slow:
            alerts.append({"model": model, **info[model], "hour_p95": hour["p95"], "week_p95": base["p95"], "requests": hour["answers"]})
    models.sort(key=lambda m: (-m["day"]["requests"], m["label"]))
    return {"models": models, "alerts": alerts, "slow_factor": slow_factor, "slow_min": slow_min,
            "providers": [{"provider": p, "day": speed_summary(g["day"]), "week": speed_summary(g["week"])}
                          for p, g in sorted(by_provider.items())],
            "hourly": [{"hour": h, "provider": p, "p50": pct(sorted(v), .5), "requests": len(v)} for (h, p), v in sorted(hours.items())]}


def fastest_like(c, alias, allowed, now=None):
    """Among alias and the allowed models priced like it (within fast_price_range either way, any provider), the one with
    the lowest median over the last fast_window_hours, counting only models with fast_min answers or more; alias when none."""
    now = time.time() if now is None else now
    price, spread, least = model_price(alias), cfg(c, "fast_price_range"), cfg(c, "fast_min")
    tier = {MODELS[a][1]: a for a in allowed if a in MODELS and (a == alias or price / spread <= model_price(a) <= price * spread)}
    # ponytail: reads the last day's speed on every automatic choice; cache it for a minute if chat traffic gets heavy
    times = {}
    for model, ms in c.execute(f"select model, latency_ms from logs where ts >= ? and model in ({','.join('?' * len(tier))})"
                               " and latency_ms is not null and (status is null or status < 400) and name not like '(%'",
                               (now - cfg(c, "fast_window_hours") * 3600, *tier)):
        times.setdefault(model, []).append(ms)
    medians = {tier[m]: pct(sorted(v), .5) for m, v in times.items() if len(v) >= least}
    return min(medians, key=medians.get) if medians else alias


def fallback_for(alias, path=None, allowed=None):
    """The backup model for alias, if it is on, (for app calls) speaks the same request format, and is in allowed (the
    team's model list; None = no team limit). A backup the team may not use means no backup."""
    fb = MODEL_EXTRA.get(alias, {}).get("fallback") if cfg(None, "fallback_enabled") else None
    if fb and fb != alias and fb in MODELS and (path is None or PROVIDERS[MODELS[fb][0]][0] == path) and (allowed is None or fb in allowed):
        return fb
    return None


_HEAVY = __import__("re").compile(
    r"```|\b(code|function|debug|refactor|analy[sz]e|compare|strategy|architecture|contract|legal|step by step|why)\b"
    r"|קוד|פונקצי|באג|נתח|ניתוח|השווה|השוואה|אסטרטגי|ארכיטקטור|חוזה|משפטי|שלב אחר שלב|למה|תכנן|תוכנית", __import__("re").I)


def route_auto(c, acct, messages):
    """Pick the cheap or the strong model for one question. Returns (alias, reason) or (None, error)."""
    cheap, strong = cfg(c, "auto_cheap"), cfg(c, "auto_strong")
    allowed = [m for m in effective_models(c, acct) if m in MODELS]
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
            reason = reason if a == want else f"{reason} (המודל המתאים לא זמין לך)"
            fast = fastest_like(c, a, allowed) if cfg(c, "auto_prefer_fast") else a
            return (a, reason) if fast == a else (fast, f"{reason} (המהיר מבין המתאימים)")
    return None, "no model available for automatic choice"


def delta_text(provider, ev):
    """The text piece inside one stream event, if any."""
    if not isinstance(ev, dict):
        return None
    if provider == "anthropic":
        return (ev.get("delta") or {}).get("text") if ev.get("type") == "content_block_delta" else None
    choices = ev.get("choices") or []
    return (choices[0].get("delta") or {}).get("content") if choices else None


# --- the settings screen: read, change (all or nothing), reset, test, export/import, per-team values, backup, updates ---
UPDATE_URL = "https://api.github.com/repos/tomerdamari/firegate/releases/latest"
RECOUNT = {"budget_reset_day", "timezone"}  # these move the month boundaries: this month's spending is counted again
STARTUP = {}  # values of the settings that apply only after a restart, as the process started with them


class SettingsInvalid(ValueError):
    def __init__(self, errors):
        super().__init__("invalid settings")
        self.errors = errors


def check_changes(changes, team=False):
    """Every change checked before anything is written: {key: clean value}, or SettingsInvalid with a reason per key.
    A value set in the server's environment can't be changed here; team values (None = like the global one) only for
    settings that allow them."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("no changes")
    errors, out = {}, {}
    for k, v in changes.items():
        d = settings.BY_KEY.get(k)
        if not d:
            errors[k] = {"code": "unknown"}
        elif d["soon"]:
            errors[k] = {"code": "soon"}
        elif team and not d["team"]:
            errors[k] = {"code": "not_team"}
        elif not team and settings.env_value(d) is not None:
            errors[k] = {"code": "env", "env": d["env"]}
        elif team and v is None:
            out[k] = None
        else:
            try:
                out[k] = settings.validate(d, v)
            except settings.Invalid as e:
                errors[k] = e.info
    if errors:
        raise SettingsInvalid(errors)
    return out


def save_settings(c, changes):
    """Check all, then write all (inside the caller's transaction), one change-log row per setting that really changed.
    A secret is logged only as "changed". Returns the changed keys."""
    done = []
    for k, v in check_changes(changes).items():
        d, old = settings.BY_KEY[k], settings.lookup(k)[0]
        if old == v:
            continue
        put_setting(c, k, settings.to_db(d, v))
        audit(c, "setting", {"name": k, "new": "changed"} if d["type"] == "secret" else {"name": k, "old": old, "new": v})
        done.append(k)
    settings.refresh(c)
    if RECOUNT & set(done):
        recount_spent(c)
    return done


def reset_setting(c, key):
    """Back to the default: the saved value becomes empty (NULL); nothing is deleted."""
    d = settings.BY_KEY.get(key)
    if not d or d["soon"]:
        raise SettingsInvalid({key: {"code": "unknown"}})
    if settings.env_value(d) is not None:
        raise SettingsInvalid({key: {"code": "env", "env": d["env"]}})
    old, source = settings.lookup(key)
    if source != "db":
        return False
    put_setting(c, key, None)
    audit(c, "setting", {"name": key, "new": "cleared"} if d["type"] == "secret" else {"name": key, "old": old, "new": d["default"], "reset": True})
    settings.refresh(c)
    if key in RECOUNT:
        recount_spent(c)
    return True


def save_team_settings(c, team, changes):
    """A team's own values (None = like the global setting again). Stored as NULL, never deleted."""
    if not c.execute("select 1 from teams where name = ? and archived is null", (team,)).fetchone():
        raise ValueError(f"team '{team}' does not exist")
    current = settings.team_overrides()
    for k, v in check_changes(changes, team=True).items():
        old = current.get((team, k))
        if old == v:
            continue
        c.execute("insert into team_settings values (?, ?, ?) on conflict(team, key) do update set value = excluded.value",
                  (team, k, None if v is None else settings.to_db(settings.BY_KEY[k], v)))
        audit(c, "team-setting", {"name": team, "key": k, "old": old, "new": v})
    settings.refresh(c)


def live_team_overrides(c):
    teams = {r[0] for r in c.execute("select name from teams where archived is null")}
    out = {}
    for (team, k), v in settings.team_overrides().items():
        if team in teams:
            out.setdefault(team, {})[k] = v
    return out


@functools.cache
def timezones():
    try:
        return sorted(zoneinfo.available_timezones())
    except OSError:
        return []


def system_info(c):
    key_env = bool(os.environ.get("FIREGATE_DATA_KEY", "").strip())
    folder = os.path.join(os.path.dirname(os.path.abspath(DB)), cfg(c, "backup_folder"))
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".db")] if os.path.isdir(folder) else []
    return {"version": VERSION, "db_path": os.path.abspath(DB), "db_size": os.path.getsize(DB) if os.path.exists(DB) else 0,
            "port": int(os.environ.get("PORT") or 8080), "key_source": "env" if key_env else "file",
            "key_file": None if key_env else key_path(DB), "backup_folder": folder, "backups": len(files),
            "last_backup": max(map(os.path.getmtime, files)) if files else None,
            "timezone_ok": not cfg(c, "timezone") or tzinfo() is not None}


def settings_view(c):
    """Everything the settings screen shows. Secrets never: only whether one is set, where from, and the last check."""
    models = [{"value": a, "he": label or a, "en": label or a}
              for a, label in c.execute("select alias, label from models where archived is null order by created, alias")]
    zones = [{"value": "", "he": "השעון של השרת", "en": "The server's clock"}] + [{"value": z, "he": z, "en": z} for z in timezones()]
    counts = collections.Counter(k for team in live_team_overrides(c).values() for k in team)
    out = []
    for d in settings.REGISTRY:
        v, source = settings.lookup(d["key"])
        item = settings.public(d, v, source)
        if d["type"] in ("model", "models"):
            item["options"] = models
        elif d["type"] == "timezone":
            item["options"] = zones
        if d["type"] == "secret":
            tested = setting(c, "tested:" + d["key"])
            item["value"]["tested"] = json.loads(tested) if tested else None
        out.append(item)
    return {"sections": [{"id": i, "he": he, "en": en} for i, he, en in settings.SECTIONS], "settings": out,
            "team_overrides": dict(counts), "system": system_info(c),
            "restart_pending": [d["key"] for d in settings.REGISTRY
                                if d["applies"] == "restart" and settings.lookup(d["key"])[0] != STARTUP.get(d["key"])]}


def export_settings():
    """The values saved on the screen, without secrets (and without what the server's environment sets)."""
    out = {}
    for d in settings.REGISTRY:
        v, source = settings.lookup(d["key"])
        if source == "db" and d["type"] != "secret" and not d["soon"]:
            out[d["key"]] = v
    return {"firegate_settings": 1, "version": VERSION, "exported": time.strftime("%Y-%m-%dT%H:%M:%S"), "settings": out}


def import_settings(c, body):
    """dry_run: what would change, what is skipped and why, and what is invalid. Otherwise apply (all or nothing)."""
    data = body.get("settings")
    if isinstance(data, dict) and isinstance(data.get("settings"), dict):
        data = data["settings"]  # the whole exported file
    if not isinstance(data, dict):
        raise ValueError("not a settings file")
    skipped, take = {}, {}
    for k, v in data.items():
        d = settings.BY_KEY.get(k)
        reason = ("unknown" if not d else "secret" if d["type"] == "secret" else "soon" if d["soon"]
                  else "env" if settings.env_value(d) is not None else None)
        if reason:
            skipped[k] = reason
        else:
            take[k] = v
    try:
        clean, errors = (check_changes(take) if take else {}), {}
    except SettingsInvalid as e:
        clean, errors = {}, e.errors
    diff = [{"key": k, "old": settings.lookup(k)[0], "new": v} for k, v in clean.items() if settings.lookup(k)[0] != v]
    if body.get("dry_run") or errors:
        return (400 if errors and not body.get("dry_run") else 200), {"diff": diff, "skipped": skipped, "errors": errors}
    changed = save_settings(c, {x["key"]: x["new"] for x in diff}) if diff else []
    audit(c, "settings-import", {"name": "settings", "changed": len(changed), "skipped": len(skipped)})
    return 200, {"ok": True, "changed": changed, "skipped": skipped}


def update_check():
    """The newest FireGate release on GitHub, compared with this one. Only when the admin asks; offline is an answer too."""
    req = urllib.request.Request(UPDATE_URL, headers={"accept": "application/vnd.github+json", "user-agent": "FireGate/" + VERSION})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "current": VERSION, "error": f"HTTP {e.code}"}
    except (OSError, ValueError):
        return {"ok": False, "current": VERSION, "error": "offline"}
    latest = str(d.get("tag_name") or "").lstrip("vV")
    ver = lambda v: tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    return {"ok": True, "current": VERSION, "latest": latest, "newer": bool(latest) and ver(latest) > ver(VERSION),
            "url": d.get("html_url"), "published": d.get("published_at")}


SETTINGS_POSTS = {"/admin/api/settings", "/admin/api/settings/test", "/admin/api/settings/reset", "/admin/api/settings/import",
                  "/admin/api/backup", "/admin/api/teams/settings"}


class TooLarge(Exception):
    pass


def trusted_proxy(ip):
    try:
        ip = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(ip in net for net in trusted_networks() if net.version == ip.version)


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

    def query(self, key):
        """One value from the address's query string, or None."""
        return (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get(key) or [None])[0]

    def json_body(self, path):
        n = int(self.headers.get("content-length") or 0)
        big = path == "/admin/api/sources/upload" or path in PROVIDER_PATHS
        if n > cfg(None, "max_body" if big else "max_request_body") * MB:
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
                       model if isinstance(model, str) else None, self.rid, encrypt(redact_text(text)[:200]) if text and self.keep_text(c) else None))
        self.reply(status, {"error": message, "code": reason})

    @staticmethod
    def keep_text(c):
        """False when the log_content setting says to keep data only, no question or answer text."""
        return cfg(c, "log_content") != "metadata"

    def screen(self, c, acct, text, model):
        """The injection policy for the newest question. True if the request may continue; otherwise it was refused."""
        found = security.scan(text)
        blocked = bool(security.ATTACKS & set(found)) and policy(c, acct["team"])[0] == "block"
        if found:
            with c:
                self.event(c, "suspicious-prompt", acct["name"], {"found": found, "action": "blocked" if blocked else "logged",
                                                                  **({"excerpt": encrypt(redact_text(text)[:200])} if self.keep_text(c) else {})})
        if blocked:
            self.refuse(c, acct, 403, "request blocked: possible prompt injection or jailbreak", "policy-injection", model, text)
        return not blocked

    local_route = None  # set when sensitive data was sent unmasked to the local model: the masked copy, for the log

    def sensitive(self, c, acct, original, masked_obj, count, model, text, path="/v1/chat/completions"):
        """The sensitive-data policy. Returns (what to send on: masked or original, model alias), or (None, model) if refused.
        local: the question goes unmasked to a model on the company's own server that the account may use (the model asked
        for, if it is one), never to an outside provider, backups included. Apps calling the Anthropic format can't be
        moved to it, and without such a model the question is masked."""
        if not count:
            return masked_obj, model
        mode = policy(c, acct["team"])[1]
        if mode == "local":
            local = local_models(c, acct) if path == "/v1/chat/completions" else []
            if local:
                target = model if model in local else local[0]
                with c:
                    self.event(c, "sensitive-routed-local", acct["name"], {"count": count, "model": MODELS[target][1]})
                self.local_route = masked_obj
                return original, target
            mode = "mask"
        kind = {"mask": "sensitive-data-masked", "block": "sensitive-data-blocked", "log": "sensitive-data-logged"}[mode]
        with c:
            self.event(c, kind, acct["name"], {"count": count})
        if mode == "block":
            self.refuse(c, acct, 403, "request blocked: sensitive data", "policy-sensitive", model, text)
            return None, model
        return (masked_obj if mode == "mask" else original), model

    def backups(self, c, acct):
        """Models a backup may come from: the team's list, or only local models when sensitive data went unmasked."""
        return local_models(c, acct) if self.local_route else team_models(c, acct["team"])

    def host_ok(self):
        host = (self.headers.get("host") or "").lower()
        host = host[1:host.find("]")] if host.startswith("[") else host.rsplit(":", 1)[0]
        if host == "localhost" or host in FIXED_HOSTS or host in cfg(None, "allowed_hosts"):
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
        if public_deploy():
            return False
        try:
            return ipaddress.ip_address(self.client_ip()).is_private
        except ValueError:
            return False

    def open_ok(self):
        return open_access() and self.inside()

    def admin_ok(self):
        inside = self.inside()
        given = self.headers.get("x-admin-password", "").encode()
        if inside:
            return True
        ip, limit, minutes, password = self.client_ip(), cfg(None, "login_ip_limit"), cfg(None, "login_ip_minutes"), cfg(None, "admin_password")
        if given and login_fails(ip) >= limit:  # guessing the admin password counts with wrong chat passwords
            self.reply(429, {"error": f"too many wrong passwords from this address, try again in {minutes} minutes"})
            return False
        if password and secrets.compare_digest(given, password.encode()):
            return True
        if given:  # a wrong password from outside is worth knowing about; a page load without one is not
            with db() as c:
                self.event(c, "admin-denied", "", {"ip": ip, "path": self.path.split("?")[0]})
                if login_fails(ip, add=True) == limit:
                    self.event(c, "login-throttled", "", {"ip": ip, "minutes": minutes})
        self.reply(401, {"error": "admin is open only from the office network" if not password else "wrong admin password"})
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
        if path in PAGES or path == "/":
            file, ctype = PAGES[path] if path != "/" else ("chat.html" if cfg(None, "home_page") == "chat" else "admin.html", "text/html")
            with open(os.path.join(HERE, file), "rb") as f:
                data, text = f.read(), ctype.startswith("text/")
            if ctype == "text/html" and cfg(None, "default_language") == "en":  # i18n.js reads it when the visitor chose no language
                data = data.replace(b'<html lang="he" dir="rtl">', b'<html lang="he" dir="rtl" data-default-lang="en">', 1)
            return self.send_raw(200, data, ctype + ("; charset=utf-8" if text else ""),
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

    def call_with_backup(self, alias, build, on_line, started, path=None, allowed=None):
        """Call alias; if the provider fails before any answer was sent, try its backup model once (only one the team may use).
        Returns (alias that answered, status, raw data, usage, note)."""
        note, last = "", None
        for a in (alias, fallback_for(alias, path, allowed)):
            if not a:
                continue
            self.current_alias = a
            t0 = time.monotonic()
            try:
                status, data, u = upstream(MODELS[a][0], build(a), on_line)
            except (urllib.error.URLError, TimeoutError) as e:  # TimeoutError: the provider stopped answering mid-way
                reason = getattr(e, "reason", e)
                status = 504 if isinstance(reason, TimeoutError) else 502
                data, u = json.dumps({"error": f"provider unreachable: {reason or 'timed out'}"}).encode(), new_usage()
                u["ms"] = u["ttft"] = round((time.monotonic() - t0) * 1000)
            u["status"] = status
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
        if isinstance(body.get("messages"), list) and len(body["messages"]) > cfg(c, "max_messages"):
            return self.refuse(c, acct, 400, "too many messages", "too-many-messages", alias)
        alias = budget_switch(c, acct, alias, path)
        err = authorize(c, acct, alias)
        if err:
            return self.refuse(c, acct, *err, alias, question)
        provider = MODELS[alias][0]
        if PROVIDERS[provider][0] != path:
            return self.reply(400, {"error": f"model '{alias}' must be called via {PROVIDERS[provider][0]}"})
        if not self.screen(c, acct, question, alias):
            return
        clean = redact(body, redactor(acct["team"]))  # masked before anything leaves for the provider; the log keeps the same masked version
        body, alias = self.sensitive(c, acct, body, clean, masked(json.dumps(body, ensure_ascii=False), json.dumps(clean, ensure_ascii=False)),
                                     alias, question, path)
        if body is None:
            return
        most = cfg(c, "max_output_tokens")  # 0: by model, no clamp
        for k in ("max_tokens", "max_completion_tokens", "max_output_tokens"):
            if most and isinstance(body.get(k), (int, float)) and body[k] > most:
                body[k] = most
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
            if isinstance(ev, dict) and cfg(None, "mask_answer_secrets"):  # keys in the answer are masked event by event (one split across events gets through)
                clean = redact(ev, mask_answer)
                if clean != ev:
                    hidden[0] += 1
                    line = b"data: " + json.dumps(clean, ensure_ascii=False).encode() + b"\n"
            sent.append(line)
            self.wfile.write(line)
            self.wfile.flush()

        used_alias, status, data, u, note = self.call_with_backup(alias, build, on_line, started, path, self.backups(c, acct))
        logged = json.dumps(self.local_route or body, ensure_ascii=False)  # sent to our own server unmasked: the log keeps it masked
        if not started and status >= 400 and not u["in"] and not u["out"] and b"provider unreachable" in data:
            charge(c, acct, used_alias, u, logged, data.decode(errors="replace"), note, self.rid)  # $0, but counts in the error rate
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
        charge(c, acct, used_alias, u, logged, text, note, self.rid)
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
            open_ok = self.open_ok()
            return self.reply(200, {"open": open_ok, "org_name": cfg(c, "org_name"),
                                    "default_person": ensure_chat_default_user(c) if open_ok else ""})
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
            mine = [m for m in effective_models(c, acct) if m in MODELS]  # the team's model list narrows the person's
            return self.reply(200, {"name": acct["name"], "team": acct["team"], "models": mine,
                                    "model_labels": {m: labels.get(m) or m for m in mine}, "default_model": default_model(c),
                                    "auto": cfg(c, "auto_enabled") and cfg(c, "auto_cheap") in mine, "org_name": cfg(c, "org_name"),
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
            mask = redactor(acct["team"])
            with c:
                owner = c.execute("select name from conversations where id = ?", (cid,)).fetchone()
                if owner and owner["name"] != acct["name"]:
                    return self.reply(404, {"error": "not found"})
                c.execute("insert or replace into conversations(id, name, title, updated, messages) values (?,?,?,?,?)",
                          (cid, acct["name"], encrypt(mask(str(body.get("title") or ""))[:100]), time.time(),
                           encrypt(json.dumps(redact(messages, mask), ensure_ascii=False))))
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
        limit, minutes, lock_after, lock_minutes = (cfg(c, k) for k in ("login_ip_limit", "login_ip_minutes", "lock_after", "lock_minutes"))
        # guessing across many names from one address: that address waits, whatever name it tries next
        if login_fails(ip) >= limit:
            return self.reply(429, {"error": f"too many wrong passwords from this address, try again in {minutes} minutes"})
        if acct and acct["locked_until"] > now:
            return self.reply(429, {"error": f"too many wrong passwords, try again in {lock_minutes} minutes"})
        # unknown names still pay the password-hash cost, so response time doesn't reveal which names exist
        if not check_password(pw, acct["pw_hash"] if acct and acct["pw_hash"] else DUMMY_HASH) or not acct:
            if login_fails(ip, add=True) == limit:
                with c:
                    self.event(c, "login-throttled", "", {"ip": ip, "minutes": minutes})
            if acct:
                with c:
                    failed = acct["failed"] + 1
                    c.execute("update accounts set failed = ?, locked_until = ? where name = ?",
                              (0 if failed >= lock_after else failed, now + lock_minutes * 60 if failed >= lock_after else 0, name))
                    if failed >= lock_after:
                        self.event(c, "account-locked", name, {"ip": ip, "minutes": lock_minutes})
            return self.reply(401, {"error": "wrong name or password"})
        with c:
            c.execute("update accounts set failed = 0 where name = ?", (name,))
        self.start_session(c, name)

    def start_session(self, c, name):
        token, now, hours = secrets.token_urlsafe(32), time.time(), cfg(c, "session_hours")
        with c:
            c.execute("delete from sessions where expires < ?", (now,))
            c.execute("insert into sessions values (?,?,?)", (sha(token), name, now + hours * 3600))
        self.reply(200, {"name": name}, [self.cookie(token, hours * 3600)])

    def chat(self, c, acct, body):
        alias, messages = body.get("model"), body.get("messages")
        if not isinstance(messages, list) or not messages or not all(
                isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) for m in messages):
            raise ValueError("messages must be a non-empty list of {role: user|assistant, content: text}")
        route = ""
        wanted = body.get("sources") or []
        if alias == "auto":  # automatic choice: cheap model for simple questions, strong one for heavy work
            if not cfg(c, "auto_enabled"):
                return self.reply(403, {"error": "automatic model choice is turned off"})
            alias, route = route_auto(c, acct, messages)
            if not alias:
                return self.reply(403, {"error": route})
        last = messages[-1]["content"]
        if len(messages) > cfg(c, "max_messages"):
            return self.refuse(c, acct, 400, "too many messages", "too-many-messages", alias)
        switched = budget_switch(c, acct, alias)
        if switched != alias:
            alias, route = switched, "התקציב נגמר: עבר למודל הזול"
        err = authorize(c, acct, alias)
        if err:
            return self.refuse(c, acct, *err, alias, last)
        if not self.screen(c, acct, last if messages[-1]["role"] == "user" else "", alias):
            return
        original = [{"role": m["role"], "content": m["content"]} for m in messages]
        clean = redact(original, redactor(acct["team"]))
        messages, alias = self.sensitive(c, acct, original, clean, masked(last, clean[-1]["content"]), alias, last)
        if messages is None:
            return
        if self.local_route:
            route = "מידע רגיש: נענה במודל המקומי"
        if not inflight_enter(acct["name"]):
            return self.refuse(c, acct, 429, "too many requests in progress", "concurrency", alias, last)
        try:
            self.chat_forward(c, acct, alias, route, messages, body.get("sources") or [])
        finally:
            inflight_leave(acct["name"])

    def screen_hits(self, c, acct, hits):
        """Retrieved passages are data handed to the model: a passage with browser code is always left out, one that
        tries to give the model instructions is left out under the block policy (and only logged otherwise)."""
        out, block = [], policy(c, acct["team"])[0] == "block"
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
                up["max_tokens"] = cfg(c, "max_output_tokens") or 32000  # 0 = by model; Claude needs a number
                # provider-side cache: the conversation so far is re-read at about a tenth of the input price next turn
                ttl = cfg(c, "chat_cache")
                if ttl != "off":
                    up["cache_control"] = {"type": "ephemeral", **({"ttl": "1h"} if ttl == "1h" else {})}
                if system:
                    up["system"] = system
            else:  # OpenAI and Gemini cache repeated prefixes on their own
                up["stream_options"] = {"include_usage": True}
                if system:
                    up["messages"] = [{"role": "system", "content": system}, *messages]
            return up
        started, text, masker, hide_keys = [], [], AnswerMasker(), cfg(c, "mask_answer_secrets")
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
                write(masker.feed(piece) if hide_keys else piece)  # keys in the answer are masked before they reach the employee

        used_alias, status, data, u, note = self.call_with_backup(alias, build, on_line, started, None, self.backups(c, acct))
        answer = ""
        if started:
            write(masker.flush())
            answer = "".join(text)
            links = security.bad_links(answer)
            found = security.scan(answer)  # the events are recorded either way; the warnings to the employee are settings
            warning = security.answer_warning(found if cfg(c, "warn_dangerous") else [], links if cfg(c, "warn_links") else [])
            write(warning)
            self.answer_events(c, acct, used_alias, answer, masker.count, links)
            # the gateway's own instructions repeated word for word: kept out of the log, and flagged
            answer, leaks = leaked("".join(text), sources.HEADER) if system else ("".join(text), 0)
            if leaks:
                with c:
                    self.event(c, "prompt-leak", acct["name"], {"model": MODELS[used_alias][1], "count": leaks})
        shown = self.local_route or messages  # sent to our own server unmasked: the log keeps it masked
        logged = {"sources": used, "messages": shown} if used else shown
        note = "; ".join(x for x in ("sensitive: local" if self.local_route else f"auto: {route}" if route else "", note) if x)
        charge(c, acct, used_alias, u, json.dumps(logged, ensure_ascii=False),
               answer if started else data.decode(errors="replace"), note, self.rid)
        if not started:
            self.reply(502 if status < 400 else status, {"error": "provider error", "detail": data.decode(errors="replace")[:500]})

    def test_model(self, c, row):
        """Send a 5-token question to the provider and report whether the key and model id work."""
        if row["provider"] == "local":
            if not cfg(c, "local_base_url"):
                return {"ok": False, "error": "no address set for the local model server"}
        elif not provider_key(row["provider"]):
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
                              "projected": projected, "recommended": recommended, "cost_center": t["cost_center"] or "",
                              "gl_account": t["gl_account"] or "", "models": team_models(c, t["name"])})
            model_info = {r["alias"]: {"provider": r["provider"], "model": r["model"], "price_in": r["price_in"], "price_out": r["price_out"],
                                       "label": r["label"], "enabled": bool(r["enabled"])}
                          for r in c.execute("select * from models where archived is null order by created, alias")}
            return self.reply(200, {"models": list(model_info), "model_info": model_info, "default_model": default_model(c), "soft_limit": cfg(c, "soft_limit") / 100,
                                    "accounts": accounts, "teams": teams})
        if path == "/admin/api/logs":
            # ponytail: last 200 only, add paging/search when someone needs older rows in the UI
            rows = c.execute("select ts, name, team, model, tokens_in, tokens_out, cost, request, response, request_id from logs"
                             " order by ts desc limit 200")
            return self.reply(200, [{**dict(r), "request": decrypt(r["request"]) or "", "response": decrypt(r["response"]) or ""} for r in rows])
        if path == "/admin/api/usage":
            rows = c.execute("select name, team, model, count(*) requests, sum(tokens_in) tokens_in, sum(tokens_out) tokens_out,"
                             " sum(cost) cost from logs where ts >= ? group by name, model order by cost desc", (month_bounds()[0],))
            return self.reply(200, [dict(r) for r in rows])
        if path == "/admin/api/activity":
            start, end = month_bounds()
            prev = month_bounds(start - 1)[0]
            first = month_bounds(month_bounds(prev - 1)[0] - 1)[0]  # three months back, for the monthly team totals
            lt = sql_local()
            # day of the budget month: 1 on the reset day
            day = lambda lo, hi: [dict(r) for r in c.execute(
                "select cast(julianday(ts, 'unixepoch', ?) - julianday(?, 'unixepoch', ?) as int) + 1 day, sum(cost) cost from logs"
                " where ts >= ? and ts < ? group by day order by day", (lt, lo, lt, lo, hi))]
            return self.reply(200, {
                "heat": [dict(r) for r in c.execute(
                    "select cast(strftime('%w', ts, 'unixepoch', ?) as int) wd, cast(strftime('%H', ts, 'unixepoch', ?) as int) hour,"
                    " count(*) requests from logs where ts >= ? group by wd, hour", (lt, lt, time.time() - 28 * 86400))],
                "this_month": day(start, time.time() + 1), "last_month": day(prev, start),
                "days_in_month": round((end - start) / 86400), "reset_day": cfg(c, "budget_reset_day"),
                # the budget month's name: moving back reset_day - 1 days lands on the 1st of the month it is named after
                "months": [dict(r) for r in c.execute(
                    "select strftime('%Y-%m', ts, 'unixepoch', ?, ?) month, coalesce(nullif(team, ''), 'בלי צוות') team, sum(cost) cost"
                    " from logs where ts >= ? group by month, team order by month", (lt, f"-{cfg(c, 'budget_reset_day') - 1} days", first))]})
        if path == "/admin/api/daily":
            rows = c.execute("select date(ts, 'unixepoch', ?) day, sum(cost) cost, count(*) requests from logs"
                             " where ts >= ? group by day order by day", (sql_local(), time.time() - 30 * 86400))
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
                conf = mcp_config(s)
                public = {k: v for k, v in conf.items() if k != "token"}
                out.append({**{k: s[k] for k in s.keys() if k != "config"}, "teams": [t for t in s["teams"].split(",") if t],
                            "docs": docs, "mcp": {**public, "has_token": bool(conf.get("token"))} if s["kind"] == "mcp" else None})
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
            providers = [p for p in PROVIDERS if provider_key(p)]
            hosts, password = FIXED_HOSTS | set(cfg(c, "allowed_hosts")), cfg(c, "admin_password")
            checks = [
                {"ok": bool(hosts), "text": "חיבור מוצפן (HTTPS) עם דומיין" if hosts else
                 "אין דומיין, ולכן החיבור לא מוצפן. השאלות והסיסמאות עוברות ברשת כטקסט גלוי. מתאים לרשת המשרד בלבד."},
                {"ok": not password or len(password) >= 16, "text": "מסך הניהול סגור מבחוץ" if not password else
                 ("סיסמת המנהל לגישה מבחוץ חזקה" if len(password) >= 16 else "סיסמת המנהל לגישה מבחוץ קצרה מ-16 תווים")},
                {"ok": open_keys == 0, "text": "לכל מפתחות ה-API יש הגבלת קצב" if not open_keys else
                 ("מפתח API אחד" if open_keys == 1 else f"{open_keys} מפתחות API") + " בלי הגבלת קצב. מפתח שדלף יכול לרוקן תקציב מהר."},
                {"ok": not open_access(), "text": "כניסה לצ'אט עם סיסמה" if not open_access() else
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
            return self.reply(200, month_report(c, self.query("month") or month_of(time.time())))
        if path == "/admin/api/savings":
            return self.reply(200, savings(c))
        if path == "/admin/api/latency":
            return self.reply(200, latency(c))
        if path == "/admin/api/chargeback":  # ?month=2026-09&format=json|csv
            month, fmt = self.query("month") or month_of(time.time()), self.query("format") or "json"
            if fmt not in ("json", "csv"):
                raise ValueError("format must be csv or json")
            data = chargeback(c, month)  # checks the month, which then goes into the file name
            if fmt == "json":
                return self.reply(200, data)
            return self.send_raw(200, chargeback_csv(data).encode(), "text/csv; charset=utf-8",
                                 [("content-disposition", f'attachment; filename="firegate-chargeback-{month}.csv"')])
        if path == "/admin/api/summary":  # preview of the monthly email; default: the last full month
            month = self.query("month") or last_full_month()
            return self.reply(200, {"month": month, **summary_content(c, month)})
        if path == "/admin/api/summary/settings":
            return self.reply(200, summary_status(c))
        if path == "/admin/api/models/daily":
            rows = c.execute("select date(ts, 'unixepoch', ?) day, model, count(*) requests, sum(cost) cost from logs"
                             " where ts >= ? and name != '(בדיקת מודל)' group by day, model order by day", (sql_local(), time.time() - 30 * 86400))
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
            local_url = cfg(c, "local_base_url")
            providers = {p: bool(provider_key(p)) for p in PROVIDERS}
            providers["local"] = bool(local_url)  # the key is optional there: "connected" means an address is set
            auto = {"enabled": cfg(c, "auto_enabled"), "cheap": cfg(c, "auto_cheap"), "strong": cfg(c, "auto_strong"),
                    "prefer_fast": cfg(c, "auto_prefer_fast"),
                    "count": c.execute("select count(*) from logs where ts >= ? and note like 'auto:%'", (start,)).fetchone()[0]}
            return self.reply(200, {"models": rows, "default_model": default_model(c), "providers": providers,
                                    "cache_saved": round(saved, 6), "auto": auto,
                                    "local": {"url": local_url, "has_key": bool(provider_key("local")), "loopback": cfg(c, "local_loopback")}})
        if path == "/admin/api/settings":
            return self.reply(200, settings_view(c))
        if path == "/admin/api/settings/export":
            return self.reply(200, export_settings())
        if path == "/admin/api/teams/settings":
            return self.reply(200, {"teams": live_team_overrides(c)})
        if path == "/admin/api/update-check":
            return self.reply(200, update_check())
        if path == "/admin/api/archive":
            return self.reply(200, archive_list(c))
        if path == "/admin/api/audit":
            rows = c.execute("select ts, action, detail from audit order by ts desc limit 100")
            return self.reply(200, [{"ts": r["ts"], "action": r["action"], "detail": json.loads(r["detail"])} for r in rows])
        if path == "/admin/api/account":  # one person's page: everything they did, archived people too
            name = (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("name") or [""])[0]
            a = c.execute("select * from accounts where name = ?", (name,)).fetchone()
            if not a:
                return self.reply(404, {"error": "not found"})
            return self.reply(200, account_page(c, a))
        self.reply(404, {"error": "not found"})

    def settings_post(self, c, path, body):
        """Returns (http status, reply body)."""
        if path == "/admin/api/settings":
            return 200, {"ok": True, "changed": save_settings(c, body.get("changes"))}
        if path == "/admin/api/settings/reset":
            return 200, {"ok": True, "changed": reset_setting(c, str(body.get("key")))}
        if path == "/admin/api/settings/import":
            return import_settings(c, body)
        if path == "/admin/api/teams/settings":
            save_team_settings(c, str(body.get("name") or ""), body.get("settings"))
            return 200, {"ok": True}
        if path == "/admin/api/backup":
            file = backup(c, "", cfg(c, "backup_folder"), "manual")
            put_setting(c, "backup_last", str(time.time()))
            audit(c, "backup", {"name": "backup", "file": os.path.basename(file), "auto": False})
            return 200, {"ok": True, "file": os.path.basename(file), "folder": os.path.dirname(file)}
        # settings/test: a connection check with the value in effect (secrets are tested, never shown)
        key = str(body.get("key") or "")
        provider = key.split("_")[0]
        if key in ("anthropic_api_key", "anthropic_url", "openai_api_key", "openai_url", "gemini_api_key", "gemini_url"):
            row = c.execute("select * from models where provider = ? and archived is null order by enabled desc, created limit 1",
                            (provider,)).fetchone()
            result = self.test_model(c, row) if row else {"ok": False, "error": "no model for this provider"}
        elif key in ("local_base_url", "local_api_key"):
            url = cfg(c, "local_base_url")
            result = local_list(url) if url else {"ok": False, "error": "no address set for the local model server"}
        elif key.startswith("smtp_"):
            to = str(body.get("to") or "").strip()
            if not EMAIL.match(to):
                raise ValueError(f"not a valid email address: {to[:100]}")
            try:
                send_mail([to], "FireGate · בדיקת שרת הדואר", "זו הודעת בדיקה מ-FireGate: שרת הדואר מוגדר נכון.\n"
                          "This is a test message from FireGate: the mail server is set up correctly.\n")
                result = {"ok": True}
            except (ValueError, smtplib.SMTPException, OSError) as e:
                result = {"ok": False, "error": mask_emails(f"{type(e).__name__}: {e}")[:300]}
        else:
            raise ValueError("this setting can't be tested")
        put_setting(c, "tested:" + key, json.dumps({"ts": time.time(), "ok": bool(result.get("ok"))}))
        return 200, result

    def admin_post(self, path, body):
        c = db()
        if path in SETTINGS_POSTS:
            try:
                with c:
                    status, result = self.settings_post(c, path, body)
            except SettingsInvalid as e:
                return self.reply(400, {"error": "invalid settings", "errors": e.errors})
            refresh_models(c)
            return self.reply(status, result)
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
        if path == "/admin/api/teams":  # create or update; fields left out of the request keep their value
            not_archived(c, "team", name)
            budget = float(body.get("budget") or 0)
            if budget < 0:
                raise ValueError("budget must be >= 0")
            fields = {"budget": budget}
            for k in ("cost_center", "gl_account"):
                if k in body:
                    fields[k] = str(body[k] or "").strip()[:64] or None
            if "models" in body:  # empty list = the team sets no limit
                models = [str(m) for m in body.get("models") or []]
                if any(m not in ALL_MODELS for m in models):
                    raise ValueError("pick known models for the team")
                fields["models"] = ",".join(models) or None
            old = c.execute("select * from teams where name = ?", (name,)).fetchone()
            c.execute(f"insert into teams(name, month, {', '.join(fields)}) values (?, ?, {', '.join('?' * len(fields))})"
                      f" on conflict(name) do update set {', '.join(f'{k} = excluded.{k}' for k in fields)}",
                      (name, month_of(time.time()), *fields.values()))
            changed = {k: v for k, v in fields.items() if k != "budget" and (old[k] if old else None) != v}
            audit(c, "team-save", {"name": name, "budget": budget, **({"old_budget": old["budget"]} if old else {}), **changed})
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
            if not enabled and cfg(c, "default_model") == name:
                raise ValueError("this is the default model; choose another default before turning it off")
            changes = {k: [old[k], v] for k, v in (("provider", provider), ("model", model), ("price_in", price_in),
                                                     ("price_out", price_out), ("price_cached", price_cached), ("fallback", fallback),
                                                     ("enabled", enabled)) if old and old[k] != v}
            audit(c, "model-save", {"name": name, "model": model, "provider": provider, "price_in": price_in, "price_out": price_out,
                                    "enabled": bool(enabled), **({"changes": changes} if changes else {"new": not old})})
            return (200, {"ok": True})
        if path == "/admin/api/security/policy":  # name is "policy"
            inj, sens = str(body.get("injection", "")), str(body.get("sensitive", ""))
            if inj not in ("block", "log") or sens not in SENSITIVE_POLICIES:
                raise ValueError("unknown security policy")
            old = policy(c)
            for k, v in (("policy_injection", inj), ("policy_sensitive", sens)):
                c.execute("insert into settings values (?, ?) on conflict(key) do update set value = excluded.value", (k, v))
            audit(c, "security-policy", {"name": "policy", "injection": inj, "sensitive": sens, "old": list(old)})
            return (200, {"ok": True})
        if path == "/admin/api/summary/settings":  # monthly summary email; name is "summary"
            to, enabled = parse_recipients(body.get("recipients")), bool(body.get("enabled"))
            if enabled and not to:
                raise ValueError("no summary recipients")
            put_setting(c, "summary_recipients", ", ".join(to))
            put_setting(c, "summary_enabled", "1" if enabled else "0")
            audit(c, "summary-settings", {"name": "summary", "enabled": enabled, "recipients": to})
            return (200, {"ok": True})
        if path == "/admin/api/summary/send":  # send now; name is "summary"
            month = str(body.get("month") or last_full_month())
            month_start(month)
            try:
                to = send_summary(c, month)  # before any write here, so the database isn't held while the mail server talks
            except (smtplib.SMTPException, OSError) as e:
                return (502, {"error": "sending failed: " + mask_emails(f"{type(e).__name__}: {e}")[:300]})
            summary_sent(c, month, to, False)
            return (200, {"ok": True, "sent": len(to)})
        if path == "/admin/api/models/auto":  # automatic choice settings; name is "auto"
            cheap, strong = str(body.get("cheap", "")), str(body.get("strong", ""))
            if cheap not in ALL_MODELS or strong not in ALL_MODELS:
                raise ValueError("pick existing models for automatic choice")
            for k, v in (("auto_enabled", "1" if body.get("enabled") else "0"), ("auto_cheap", cheap), ("auto_strong", strong),
                         ("auto_prefer_fast", "1" if body.get("prefer_fast") else "0")):
                c.execute("insert into settings values (?, ?) on conflict(key) do update set value = excluded.value", (k, v))
            audit(c, "model-auto", {"name": "auto", "enabled": bool(body.get("enabled")), "cheap": cheap, "strong": strong,
                                    "prefer_fast": bool(body.get("prefer_fast"))})
            return (200, {"ok": True})
        if path == "/admin/api/local":  # the local model server's address; name is "local"
            url, old = check_local_url(body.get("url")), cfg(c, "local_base_url")
            put_setting(c, "local_base_url", url)
            audit(c, "local-server", {"name": "local", "url": url, "old": old})
            return (200, {"ok": True, "url": url})
        if path == "/admin/api/local/test":  # the models the server offers; the typed address, else the saved one
            url = check_local_url(body.get("url") or cfg(c, "local_base_url"))
            return (200, local_list(url) if url else {"ok": False, "error": "no address set for the local model server"})
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
            # what the request leaves out comes from the defaults for a new user
            defaults = {"rpm": cfg(c, "new_user_rpm"), "daily_tokens": cfg(c, "new_user_daily_tokens"),
                        "models": cfg(c, "new_user_models") or [default_model(c)]}
            if cfg(c, "new_user_budget") is not None:
                defaults["budget"] = cfg(c, "new_user_budget")
            fields = account_fields(c, {**defaults, **body}, partial=False)
            pw = body.get("password")
            if not pw and not body.get("api_key"):
                raise ValueError("give a password (chat login) or an API key, or both")
            try:
                c.execute("insert into accounts(name, team, models, budget, rpm, month, pw_hash, daily_tokens, key_expires)"
                          " values (?,?,?,?,?,?,?,?,?)",
                          (name, fields.get("team", ""), fields["models"], fields["budget"], fields.get("rpm", 0),
                           month_of(time.time()), hash_password(check_new_password(pw)) if pw else None,
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
    STARTUP.update((d["key"], settings.lookup(d["key"])[0]) for d in settings.REGISTRY if d["applies"] == "restart")
    if os.environ.get("SEED_DEMO", "").strip().lower() in ("1", "true", "yes", "on"):
        # demo hosting whose disk resets on restart: start every time with sample data
        import seed_demo  # noqa: F401  (fills an empty database; leaves a filled one alone)
    threading.Thread(target=summary_loop, daemon=True).start()  # the monthly summary email (only sends when turned on)
    port = int(os.environ.get("PORT", 8080))
    print(f"gateway listening on :{port}", flush=True)
    ThreadingHTTPServer(("", port), Handler).serve_forever()
