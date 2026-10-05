const $ = id => document.getElementById(id);
function icon(name) {
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg"), use = document.createElementNS(ns, "use");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  use.setAttribute("href", "#i-" + name);
  svg.append(use);
  return svg;
}
function el(tag, props = {}, ...kids) {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids.filter(k => k !== null && k !== undefined));
  return e;
}
const money = v => "$" + (v >= 1 ? v.toFixed(2) : v.toFixed(4));
const modelNames = { "fast": "Claude מהיר", "smart": "Claude חכם", "gpt-fast": "GPT מהיר", "gpt-smart": "GPT חכם",
  "gemini-fast": "Gemini מהיר", "gemini-smart": "Gemini חכם" };
const errors = {
  "personal monthly budget exhausted": "התקציב החודשי שלך נגמר. הוא יתחדש ב-1 לחודש, או שאפשר לבקש הגדלה מהמנהל.",
  "team monthly budget exhausted": "התקציב החודשי של הצוות שלך נגמר. הוא יתחדש ב-1 לחודש, או שאפשר לבקש הגדלה מהמנהל.",
  "request blocked: possible prompt injection or jailbreak": "השאלה נחסמה כי היא נראית כמו ניסיון לעקוף את ההוראות של המודל. אם זו טעות, פנו למנהל המערכת.",
  "request blocked: sensitive data": "השאלה נחסמה כי יש בה מידע רגיש (כמו תעודת זהות, כרטיס אשראי, טלפון או מפתח גישה). הסירו אותו ונסו שוב.",
  "daily token quota reached": "נגמרה המכסה היומית שלך. היא תתחדש מחר, או שאפשר לבקש הגדלה מהמנהל.",
  "too many requests in progress": "כבר יש לך כמה שאלות שרצות במקביל. חכו שהן יסתיימו ונסו שוב.",
  "too many messages": "השיחה ארוכה מדי. פתחו שיחה חדשה.",
  "request too large": "השאלה ארוכה מדי. קצרו אותה ונסו שוב.",
};

let me = null, conv = { id: null, title: "", messages: [] }, controller = null, openMode = false, showArchived = false;

async function call(path, body) {
  const r = await fetch(path, { method: body ? "POST" : "GET", headers: { "content-type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (r.status === 401 && path !== "/api/login") { showLogin(); throw new Error("not logged in"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errors[data.error] || data.error || "שגיאה " + r.status);
  return data;
}

function showLogin() {
  if (openMode) return showPicker();
  $("loginView").hidden = false; $("appView").hidden = true; $("lName").focus();
}

// open access (office network): no login screen, people pick their own name in the side menu
async function boot() {
  try { openMode = (await call("/api/config")).open; } catch {}
  $("pwLinks").hidden = openMode;
  $("whoPick").hidden = !openMode;
  if (openMode) {
    const people = await call("/api/people");
    const options = () => [el("option", { value: "", textContent: "בחרו את השם שלכם" }),
      ...people.map(p => el("option", { value: p.name, textContent: p.team ? `${p.name} · ${p.team}` : p.name }))];
    $("who").replaceChildren(...options());
    $("who2").replaceChildren(...options());
    let saved = "";
    try { saved = localStorage.getItem("who") || ""; } catch {}
    const meNow = await fetch("/api/me").then(r => r.ok ? r.json() : null).catch(() => null);
    if (!meNow && saved && people.some(p => p.name === saved)) await becomeUser(saved);
  }
  start();
}
async function becomeUser(name) {
  await call("/api/as", { name });
  try { localStorage.setItem("who", name); } catch {}
  chosen = null;
  conv = { id: null, title: "", messages: [] };
}
function showPicker() {
  me = null;
  $("loginView").hidden = true; $("appView").hidden = false;
  $("who").value = "";
  $("sideFoot").hidden = true;
  $("welcomeTitle").textContent = "ברוכים הבאים";
  $("welcomeText").textContent = "בחרו את השם שלכם כדי להתחיל. ההוצאה נרשמת על השם והצוות שבחרתם.";
  $("welcomePick").hidden = false;
  $("who2").value = "";
  $("welcome").hidden = false;
  $("thread").replaceChildren();
  $("input").disabled = $("send").disabled = true;
  $("convs").replaceChildren();
  $("topWho").textContent = "";
}
$("who2").onchange = () => { $("who").value = $("who2").value; $("who").onchange(); };
$("who").onchange = async () => {
  if (!$("who").value) return;
  await becomeUser($("who").value);
  $("sidebar").classList.remove("open");
  start();
};

async function start() {
  try { me = await call("/api/me"); } catch { return; }
  $("loginView").hidden = true; $("appView").hidden = false;
  $("sideFoot").hidden = false;
  $("welcomePick").hidden = true;
  $("input").disabled = $("send").disabled = false;
  $("welcomeTitle").textContent = `שלום ${me.name.split(" ")[0]}, במה אפשר לעזור?`;
  $("welcomeText").textContent = "השאלות נשמרות ומתועדות. מספרי תעודת זהות, כרטיסי אשראי ומפתחות גישה מוסתרים אוטומטית לפני שהם נשלחים.";
  if (openMode) $("who").value = me.name;
  $("topWho").textContent = me.team ? `${me.name} · צוות ${me.team}` : me.name;
  renderThread();
  $("meName").textContent = me.name;
  $("meTeam").textContent = me.team ? "צוות " + me.team : "";
  const current = $("model").value;
  Object.assign(modelNames, me.model_labels || {}, { auto: "אוטומטי" });
  // "automatic": the gateway picks the cheap or the strong model per question
  $("model").replaceChildren(...(me.auto ? [el("option", { value: "auto", textContent: "אוטומטי: זול או חזק לפי השאלה" })] : []),
    ...me.models.map(m => el("option", { value: m, textContent: modelNames[m] || m })));
  try { $("model").value = current || localStorage.getItem("model") || (me.auto ? "auto" : me.default_model); } catch {}
  // a remembered model may have been turned off since: fall back to the default, then to the first allowed
  if (!$("model").value) $("model").value = me.models.includes(me.default_model) ? me.default_model : me.models[0];
  renderBudget();
  renderPicker();
  if (!me.models.length) {  // every model this person may use is turned off
    $("input").disabled = $("send").disabled = true;
    $("welcomeTitle").textContent = "אין כרגע מודל זמין";
    $("welcomeText").textContent = "המודלים שמותרים לך כבויים כרגע. פנו למנהל המערכת.";
  }
  loadConvs();
  $("input").focus();
  autosize();  // a question passed in ?q= was measured while the screen was still hidden
}

function meter(label, spent, budget) {
  const pct = budget ? Math.min(spent / budget, 1) : 0;
  const lv = !budget ? "" : pct >= 1 ? "bad" : pct >= 0.8 ? "warn" : "";
  return el("div", { className: "meter " + lv },
    el("div", { className: "label" }, el("span", { textContent: label }), el("span", { className: "num", textContent: budget ? `${money(spent)} / ${money(budget)}` : money(spent) })),
    el("div", { className: "track" }, el("div", { className: "fill", style: `width:${pct * 100}%` })));
}
function renderBudget() {
  $("meBudget").replaceChildren(meter("תקציב אישי החודש", me.spent, me.budget),
    me.team && me.team_budget ? meter("תקציב הצוות", me.team_spent, me.team_budget) : "");
  const left = Math.max(me.budget - me.spent, 0);
  $("budgetHint").textContent = `נשאר לך החודש ${money(left)}` + (me.budget && left / me.budget < 0.2 ? " · התקציב עומד להיגמר" : "");
}

// the side list: saved chats, or (after "ארכיון") the chats moved to the archive, each with a restore button.
// Nothing is deleted; continuing an archived chat brings it back to the list.
async function loadConvs() {
  const list = await call(showArchived ? "/api/conversations/archived" : "/api/conversations");
  $("convsTitle").textContent = showArchived ? "ארכיון שיחות" : "שיחות";
  $("archiveToggle").textContent = showArchived ? "חזרה לשיחות" : "ארכיון";
  $("convs").replaceChildren(...list.map(c => el("div", { className: "conv" + (c.id === conv.id ? " on" : "") },
    el("button", { className: "open", textContent: c.title || "שיחה", title: c.title, onclick: () => openConv(c.id) }),
    showArchived
      ? el("button", { className: "del keep", title: "שחזור השיחה", ariaLabel: `שחזור השיחה "${c.title || "שיחה"}"`, onclick: async () => {
          await call("/api/conversations/restore", { id: c.id });
          loadConvs();
        } }, icon("restore"))
      : el("button", { className: "del", title: "העברה לארכיון", ariaLabel: `העברת השיחה "${c.title || "שיחה"}" לארכיון`, onclick: async () => {
          if (!await UI.confirm({ title: "להעביר את השיחה לארכיון?", body: "השיחה תוסתר מהרשימה שלך. אפשר לשחזר אותה מהארכיון שבתפריט.", ok: "העברה לארכיון" })) return;
          await call("/api/conversations/archive", { id: c.id });
          if (c.id === conv.id) newChat(); else loadConvs();
        } }, icon("archive")))));
  if (!list.length) $("convs").append(el("p", { className: "muted small", style: "padding:8px 10px",
    textContent: showArchived ? "אין שיחות בארכיון" : "עוד אין שיחות" }));
}
$("archiveToggle").onclick = () => { showArchived = !showArchived; loadConvs(); };

async function openConv(id) {
  const c = await call("/api/conversations/" + id);
  conv = { id: c.id, title: c.title, messages: c.messages };
  renderThread();
  loadConvs();
  $("sidebar").classList.remove("open");
}

function newChat() {
  if (controller) controller.abort();
  conv = { id: null, title: "", messages: [] };
  renderThread();
  loadConvs();
  $("input").focus();
  autosize();  // a question passed in ?q= was measured while the screen was still hidden
}

// light formatting: ``` code blocks, **bold**, `code`; everything inserted as text, never as HTML
function formatted(text) {
  const box = el("div");
  text.split("```").forEach((part, i) => {
    if (i % 2) {
      box.append(el("pre", { textContent: part.replace(/^[^\n]*\n/, "") }));
      return;
    }
    part.split(/\n{2,}/).filter(p => p.trim()).forEach(p => {
      const para = el("p", { dir: "auto" });
      p.split(/(\*\*[^*]+\*\*|`[^`\n]+`)/).forEach(tok => {
        if (tok.startsWith("**") && tok.endsWith("**") && tok.length > 4) para.append(el("b", { textContent: tok.slice(2, -2) }));
        else if (tok.startsWith("`") && tok.endsWith("`") && tok.length > 2) para.append(el("code", { textContent: tok.slice(1, -1) }));
        else para.append(tok);
      });
      box.append(para);
    });
  });
  return box;
}

// company document sources the user can switch on; the choice is remembered in this browser
let chosen = null;
function renderPicker() {
  try { chosen = chosen || JSON.parse(localStorage.getItem("sources")); } catch {}
  const names = me.sources.map(x => x.name);
  if (!Array.isArray(chosen)) chosen = names;  // first time: all on
  $("picker").hidden = !names.length;
  $("picker").replaceChildren("חיפוש במסמכים:", ...me.sources.map(src => el("button", {
    type: "button", className: "chip", textContent: src.name, title: src.description,
    ariaPressed: String(chosen.includes(src.name)),
    onclick: () => {
      chosen = chosen.includes(src.name) ? chosen.filter(n => n !== src.name) : [...chosen, src.name];
      try { localStorage.setItem("sources", JSON.stringify(chosen)); } catch {}
      renderPicker();
    } })));
}
function usedEl(list) {
  return list && list.length ? el("div", { className: "used" }, "מבוסס על:", ...list.map(u => el("span", { className: "badge", textContent: u }))) : null;
}

// who answered, and why that model (automatic choice or a backup when the first one was down)
function metaText(m) {
  return (m.label || modelNames[m.model] || m.model || "") + (m.route ? ` · ${m.route}` : "");
}

function messageEl(m) {
  if (m.role === "user") return el("div", { className: "msg user", dir: "auto", textContent: m.content });
  return el("div", { className: "msg assistant" }, el("div", { className: "meta", textContent: metaText(m) }),
    formatted(m.content), usedEl(m.sources));
}

function renderThread() {
  $("welcome").hidden = conv.messages.length > 0;
  $("convTitle").textContent = conv.title || "שיחה חדשה";
  $("thread").replaceChildren(...conv.messages.map(messageEl));
  $("scroll").scrollTop = $("scroll").scrollHeight;
}

async function send() {
  const text = $("input").value.trim();
  if (!text || controller) return;
  const model = $("model").value;
  try { localStorage.setItem("model", model); } catch {}
  conv.messages.push({ role: "user", content: text });
  if (!conv.title) conv.title = text.slice(0, 50);
  $("input").value = ""; autosize();
  renderThread();

  const answer = { role: "assistant", content: "", model };
  const bubble = el("div", { className: "msg assistant" }, el("div", { className: "meta", textContent: modelNames[model] || model }));
  const body = el("div", { className: "cursor" });
  bubble.append(body);
  $("thread").append(bubble);
  controller = new AbortController();
  $("sendLabel").textContent = "עצירה";
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "content-type": "application/json" }, signal: controller.signal,
      body: JSON.stringify({ model, sources: (chosen || []).filter(n => me.sources.some(x => x.name === n)),
        messages: conv.messages.map(({ role, content }) => ({ role, content })) }) });
    if (r.status === 401) { showLogin(); return; }
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(errors[data.error] || data.error || "שגיאה " + r.status);
    }
    try { answer.sources = JSON.parse(decodeURIComponent(r.headers.get("x-sources") || "[]")); } catch {}
    try {
      answer.model = r.headers.get("x-model-used") || model;
      answer.label = decodeURIComponent(r.headers.get("x-model-label") || "");
      answer.route = decodeURIComponent(r.headers.get("x-route") || "");
      bubble.firstChild.textContent = metaText(answer);
    } catch {}
    if (answer.sources && answer.sources.length) bubble.append(usedEl(answer.sources));
    const reader = r.body.getReader(), dec = new TextDecoder();
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      answer.content += dec.decode(value, { stream: true });
      body.replaceChildren(formatted(answer.content));
      const s = $("scroll");
      if (s.scrollHeight - s.scrollTop - s.clientHeight < 120) s.scrollTop = s.scrollHeight;
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      bubble.replaceWith(el("div", { className: "msg error", textContent: e.message }));
      conv.messages.pop();  // let the user retry the same question
      $("input").value = text; autosize();
    }
  } finally {
    body.classList.remove("cursor");
    controller = null;
    $("sendLabel").textContent = "שליחה";
  }
  if (answer.content) {
    conv.messages.push(answer);
    try { conv.id = (await call("/api/conversations", conv)).id; } catch {}
  }
  try { me = await call("/api/me"); renderBudget(); loadConvs(); } catch {}
}

function autosize() { const t = $("input"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 220) + "px"; }
$("input").addEventListener("input", autosize);
// "ask" bar on the admin dashboard opens /chat?q=…: put the question in the box (not sent), then drop it from the address
const asked = new URLSearchParams(location.search).get("q");
if (asked) { $("input").value = asked; autosize(); history.replaceState(null, "", location.pathname + location.hash); }
if (matchMedia("(pointer: coarse)").matches) $("input").placeholder = "כתבו הודעה…";  // phones: no keyboard-shortcut hints
$("input").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
$("composer").onsubmit = e => { e.preventDefault(); controller ? controller.abort() : send(); };
$("newChat").onclick = newChat;
UI.sideMenu($("sidebar"), $("menu"));

$("loginForm").onsubmit = async e => {
  e.preventDefault();
  $("loginError").textContent = "";
  try {
    await call("/api/login", { name: $("lName").value, password: $("lPass").value });
    $("lPass").value = "";
    start();
  } catch (err) {
    $("loginError").textContent = /too many/.test(err.message) ? "יותר מדי ניסיונות שגויים. נסו שוב בעוד 15 דקות." : "שם משתמש או סיסמה שגויים";
  }
};
$("logout").onclick = async () => { try { await call("/api/logout", {}); } catch {} location.reload(); };
$("changePw").onclick = () => { $("pwError").textContent = ""; $("pwForm").reset(); $("pwDialog").showModal(); };
$("pwForm").onsubmit = async e => {
  e.preventDefault();
  try {
    await call("/api/password", { old: $("pwOld").value, new: $("pwNew").value });
    $("pwDialog").close();
    UI.toast("הסיסמה הוחלפה. מעבירים אותך לכניסה מחדש…");
    setTimeout(() => location.reload(), 1500);
  } catch (err) { $("pwError").textContent = /current password/.test(err.message) ? "הסיסמה הנוכחית שגויה" : err.message; }
};

boot();
document.querySelectorAll("[data-close]").forEach(b => b.onclick = () => b.closest("dialog").close());
