"""Build the static demo for GitHub Pages into pages/site/.

Runs the real gateway on a temporary database filled with sample data, records every answer the pages need,
and writes the HTML/CSS/JS with that recording plus mock.js, which plays the server inside the browser.
Run: python pages/build.py
"""
import http.cookiejar
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "pages", "site")
tmp = tempfile.mkdtemp()
os.environ.update(GATEWAY_DB=os.path.join(tmp, "demo.db"), SEED_SOURCES_DIR=os.path.join(tmp, "it"), OPEN_ACCESS="1",
                  ADMIN_PASSWORD="", PUBLIC_DEPLOY="", ANTHROPIC_API_KEY="", OPENAI_API_KEY="", GEMINI_API_KEY="",
                  DEMO_PASSWORD="demo-pass-1")
sys.path.insert(0, ROOT)
import gateway  # noqa: E402  (environment first)
import seed_demo  # noqa: E402,F401  (fills the temporary database)

gateway.Handler.log_message = lambda *a: None
srv = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"


def get(path, opener=None):
    return json.loads((opener or urllib.request.build_opener()).open(base + path).read())


def post(path, body, opener):
    req = urllib.request.Request(base + path, json.dumps(body).encode(), {"content-type": "application/json"})
    return json.loads(opener.open(req).read())


admin = {k: get("/admin/api/" + k) for k in ("overview", "usage", "daily", "logs", "audit", "sources", "security", "models",
                                              "models/daily", "sources/status", "activity", "audit/verify", "archive",
                                              "savings", "summary/settings", "latency")}
months = get("/admin/api/report")["months"]
for m in months:  # the pages ask these per month: the report, the chargeback table, the summary email preview
    for key in ("report", "chargeback", "summary"):
        admin[f"{key}?month={m}"] = get(f"/admin/api/{key}?month={m}")
admin["report_default"] = months[0]
# one page per person, archived people too; the demo keeps their 30 latest requests to hold data.js down
for name in [a["name"] for a in admin["overview"]["accounts"]] + [a["name"] for a in admin["archive"].get("accounts", [])]:
    page = get("/admin/api/account?name=" + urllib.parse.quote(name))
    page["requests"] = page["requests"][:30]
    admin["account?name=" + name] = page

people = get("/api/people")
me, conversations, archived, items = {}, {}, {}, {}
for p in people:
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    post("/api/as", {"name": p["name"]}, o)
    me[p["name"]] = get("/api/me", o)
    conversations[p["name"]] = get("/api/conversations", o)
    archived[p["name"]] = get("/api/conversations/archived", o)
    items[p["name"]] = {c["id"]: get("/api/conversations/" + c["id"], o) for c in conversations[p["name"]] + archived[p["name"]]}
srv.shutdown()

data = {"admin": admin, "people": people, "me": me, "conversations": conversations, "archived_conversations": archived,
        "conversation_items": items}

# ---- write the site: relative paths (Pages serves under /<repo>/), recorded data, the mock ----
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
shutil.copytree(os.path.join(ROOT, "fonts"), os.path.join(OUT, "fonts"))
links = [('href="/#', 'href="index.html#'), ('src="/en-admin.js"', 'src="en-admin.js"'), ('src="/en-chat.js"', 'src="en-chat.js"'), ('src="/en-docs.js"', 'src="en-docs.js"'), ('src="/i18n.js"', 'src="i18n.js"'), ('src="/docs.js"', 'src="docs.js"'), ('href="/logo.svg"', 'href="logo.svg"'), ('src="/logo.svg"', 'src="logo.svg"'), ('href="/style.css"', 'href="style.css"'), ('href="/admin"', 'href="index.html"'), ('href="/docs"', 'href="docs.html"'),
         ('href="/chat"', 'href="chat.html"'), ('action="/chat"', 'action="chat.html"'), ('href="/"', 'href="index.html"'), ('src="/ui.js"', 'src="ui.js"'),
         ('src="/admin.js"', 'src="admin.js"'), ('src="/chat.js"', 'src="chat.js"')]
for src, dst in (("admin.html", "index.html"), ("admin.html", "admin.html"), ("chat.html", "chat.html"), ("docs.html", "docs.html")):
    html = open(os.path.join(ROOT, src), encoding="utf-8").read()
    for a, b in links:
        html = html.replace(a, b)
    html = html.replace('<script src="ui.js"></script>', '<script src="data.js"></script>\n<script src="mock.js"></script>\n<script src="ui.js"></script>')
    open(os.path.join(OUT, dst), "w", encoding="utf-8").write(html)
for name in ("ui.js", "admin.js", "chat.js", "docs.js", "en-admin.js", "en-chat.js", "en-docs.js", "i18n.js"):
    js = open(os.path.join(ROOT, name), encoding="utf-8").read().replace('location.href = "/chat"', 'location.href = "chat.html"')
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(js)
css = open(os.path.join(ROOT, "style.css"), encoding="utf-8").read().replace('url("/fonts/', 'url("fonts/')
open(os.path.join(OUT, "style.css"), "w", encoding="utf-8").write(css)
shutil.copy(os.path.join(ROOT, "pages", "mock.js"), os.path.join(OUT, "mock.js"))
shutil.copy(os.path.join(ROOT, "logo.svg"), os.path.join(OUT, "logo.svg"))
with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.DEMO = " + json.dumps(data, ensure_ascii=False) + ";\n")
open(os.path.join(OUT, ".nojekyll"), "w").close()  # serve files as they are
size = sum(os.path.getsize(os.path.join(d, n)) for d, _, ns in os.walk(OUT) for n in ns)
print(f"built {OUT}: {len(people)} demo users, {len(months)} report months, {size // 1024} KB")
