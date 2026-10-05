// Demo build for static hosting (GitHub Pages): answers the gateway's API from recorded sample data in the browser.
// Nothing is saved and no AI provider is called. Loaded before the page scripts; requires window.DEMO (data.js).
(() => {
  const D = window.DEMO;
  const json = (obj, status = 200, headers = {}) =>
    new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...headers } });
  const who = () => { try { return sessionStorage.getItem("demo-who") || ""; } catch { return ""; } };
  const setWho = n => { try { sessionStorage.setItem("demo-who", n); } catch {} };
  // a change "succeeds" but nothing is stored: every success notice right after one says so
  let lastWrite = 0;
  const notSaved = () => { lastWrite = Date.now(); };

  // a canned streamed answer so the chat feels real
  function chatAnswer(body) {
    const me = D.me[who()] || {};
    const auto = body.model === "auto";
    const q = ((body.messages || []).slice(-1)[0] || {}).content || "";
    const heavy = q.length > 1200 || /קוד|נתח|השווה|code|analy/i.test(q);
    const used = auto ? (heavy ? "smart" : "fast") : body.model;
    const label = (me.model_labels || {})[used] || used;
    const route = auto ? (heavy ? "קוד, ניתוח או השוואה" : "שאלה קצרה ופשוטה") : "";
    const docs = (body.sources || []).length ? [`${body.sources[0]} / דוגמה`] : [];
    let text = "זו תשובת הדגמה: בגרסה הזו אין חיבור לספקי בינה מלאכותית.\n\n" +
      "בהתקנה אמיתית השער היה בודק את התקציב שלך, מסתיר מידע רגיש, " + (docs.length ? "מחפש במסמכים שבחרת, " : "") +
      `ושולח את השאלה ל-**${label}**` + (auto ? ` (נבחר אוטומטית: ${route})` : "") + ".\n\nלהתקנה: github.com/tomerdamari/firegate";
    const t = s => (typeof I18N !== "undefined" ? I18N.t(s) : s);
    if (typeof I18N !== "undefined" && I18N.lang === "en") text = "This is a demo answer: this version is not connected to any AI provider.\n\n" +
      "In a real install the gateway would check your budget, hide sensitive data, " + (docs.length ? "search the documents you picked, " : "") +
      `and send the question to **${t(label)}**` + (auto ? ` (picked automatically: ${t(route)})` : "") + ".\n\nTo install: github.com/tomerdamari/firegate";
    const enc = new TextEncoder(), parts = text.match(/.{1,12}/gs);
    const stream = new ReadableStream({
      async pull(ctrl) {
        const p = parts.shift();
        if (p === undefined) return ctrl.close();
        await new Promise(r => setTimeout(r, 35));
        ctrl.enqueue(enc.encode(p));
      },
    });
    return new Response(stream, { status: 200, headers: { "content-type": "text/plain; charset=utf-8",
      "x-model-used": used, "x-model-label": encodeURIComponent(label), "x-route": encodeURIComponent(route),
      "x-sources": encodeURIComponent(JSON.stringify(docs)) } });
  }

  function route(url, init) {
    const u = new URL(url, location.href), path = u.pathname.replace(/^.*?\/(admin\/api|api)\//, "/$1/");
    const method = (init && init.method) || "GET";
    const body = init && init.body ? JSON.parse(init.body) : {};
    if (path.startsWith("/admin/api/")) {
      const key = path.slice(11);
      if (method === "GET") {
        if (key === "report") {
          const m = u.searchParams.get("month") || D.admin.report_default;
          return json(D.admin["report?month=" + m] || D.admin["report?month=" + D.admin.report_default]);
        }
        if (key === "account") {
          const page = D.admin["account?name=" + u.searchParams.get("name")];
          return page ? json(page) : json({ error: "not found" }, 404);
        }
        return key in D.admin ? json(D.admin[key]) : json({ error: "not found" }, 404);
      }
      if (key === "models/test") return json({ ok: false, error: "no API key for this provider in .env" });
      if (key === "sources/mcp-test") return json({ ok: false, error: "זו תצוגת הדגמה, אין חיבור לשרתים" });
      if (key === "accounts" || key === "accounts/key") { notSaved(); return json({ ok: true, key: "gw-demo-key-not-real" }); }
      notSaved();
      return json({ ok: true });
    }
    if (path === "/api/config") return json({ open: true });
    if (path === "/api/people") return json(D.people);
    if (path === "/api/as" || path === "/api/login") {
      if (!D.me[body.name]) return json({ error: "no such user" }, 404);
      setWho(body.name);
      return json({ name: body.name });
    }
    if (path === "/api/logout") { setWho(""); return json({ ok: true }); }
    const me = D.me[who()];
    if (!me) return json({ error: "not logged in" }, 401);
    if (path === "/api/me") return json(me);
    if (path === "/api/conversations" && method === "GET") return json(D.conversations[who()] || []);
    if (path === "/api/conversations/archived") return json((D.archived_conversations || {})[who()] || []);
    if (path.startsWith("/api/conversations/") && method === "GET") {
      const item = (D.conversation_items[who()] || {})[path.split("/").pop()];
      return item ? json(item) : json({ error: "not found" }, 404);
    }
    if (path === "/api/conversations") return json({ id: body.id || "demo-" + Date.now() });
    if (path === "/api/chat") return chatAnswer(body);
    if (path === "/api/password") { notSaved(); return json({ ok: true }); }
    return json({ ok: true });
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = (url, init) => {
    const s = String(url);
    return /\/(admin\/api|api)\//.test(s) ? Promise.resolve(route(s, init)) : realFetch(url, init);
  };

  // success notices after a change say that nothing was stored
  addEventListener("DOMContentLoaded", () => {
    if (typeof UI !== "undefined") {  // ui.js declares "const UI": a global, but not a property of window
      const toast = UI.toast;
      UI.toast = (text, opts = {}) => toast(Date.now() - lastWrite < 5000 && opts.kind !== "bad"
        ? `${text} (בהדגמה: לא נשמר באמת)` : text, { ...opts, action: undefined });
    }
  });
})();
