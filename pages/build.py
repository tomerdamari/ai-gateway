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
                                              "models/daily", "sources/status")}
months = get("/admin/api/report")["months"]
for m in months:
    admin["report?month=" + m] = get("/admin/api/report?month=" + m)
admin["report_default"] = months[0]

people = get("/api/people")
me, conversations, items = {}, {}, {}
for p in people:
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    post("/api/as", {"name": p["name"]}, o)
    me[p["name"]] = get("/api/me", o)
    conversations[p["name"]] = get("/api/conversations", o)
    items[p["name"]] = {c["id"]: get("/api/conversations/" + c["id"], o) for c in conversations[p["name"]]}
srv.shutdown()

data = {"admin": admin, "people": people, "me": me, "conversations": conversations, "conversation_items": items}

# ---- write the site: relative paths (Pages serves under /<repo>/), recorded data, the mock ----
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
shutil.copytree(os.path.join(ROOT, "fonts"), os.path.join(OUT, "fonts"))
links = [('href="/style.css"', 'href="style.css"'), ('href="/admin"', 'href="admin.html"'), ('href="/docs"', 'href="docs.html"'),
         ('href="/"', 'href="index.html"'), ('src="/ui.js"', 'src="ui.js"'), ('src="/admin.js"', 'src="admin.js"'),
         ('src="/chat.js"', 'src="chat.js"')]
for src, dst in (("chat.html", "index.html"), ("admin.html", "admin.html"), ("docs.html", "docs.html")):
    html = open(os.path.join(ROOT, src), encoding="utf-8").read()
    for a, b in links:
        html = html.replace(a, b)
    html = html.replace('<script src="ui.js"></script>', '<script src="data.js"></script>\n<script src="mock.js"></script>\n<script src="ui.js"></script>')
    if src == "docs.html":
        html = html.replace("</body>", '<script src="mock.js" defer></script>\n</body>').replace('<script src="mock.js" defer>', '<script>window.DEMO={admin:{},people:[],me:{},conversations:{},conversation_items:{}}</script>\n<script src="mock.js" defer>')
    open(os.path.join(OUT, dst), "w", encoding="utf-8").write(html)
for name in ("ui.js", "admin.js", "chat.js"):
    js = open(os.path.join(ROOT, name), encoding="utf-8").read().replace('location.href = "/"', 'location.href = "index.html"')
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(js)
css = open(os.path.join(ROOT, "style.css"), encoding="utf-8").read().replace('url("/fonts/', 'url("fonts/')
css += """
/* demo note (static build only) */
.demo-bar { position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 60; max-width: calc(100vw - 120px);
  background: #fff4d6; color: #3d2e00; border: 1px solid #f0d98a; border-radius: 999px; padding: .35rem 1rem; font-size: .78rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, .12); text-align: center; }
.demo-bar a { color: #1d4d93; font-weight: 600; }
@media (max-width: 767px) { .demo-bar { top: auto; bottom: 8px; max-width: calc(100vw - 24px); } }
"""
open(os.path.join(OUT, "style.css"), "w", encoding="utf-8").write(css)
shutil.copy(os.path.join(ROOT, "pages", "mock.js"), os.path.join(OUT, "mock.js"))
with open(os.path.join(OUT, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.DEMO = " + json.dumps(data, ensure_ascii=False) + ";\n")
open(os.path.join(OUT, ".nojekyll"), "w").close()  # serve files as they are
size = sum(os.path.getsize(os.path.join(d, n)) for d, _, ns in os.walk(OUT) for n in ns)
print(f"built {OUT}: {len(people)} demo users, {len(months)} report months, {size // 1024} KB")
