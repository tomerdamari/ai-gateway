let pw = "";
try { pw = sessionStorage.getItem("pw") || ""; } catch {}
let state = { models: [], accounts: [], teams: [], soft_limit: 0.8 };
let logs = [];

const $ = id => document.getElementById(id);
const BUTTON_ICONS = { "עריכה": "edit", "מחיקה": "trash", "הסרה": "trash", "העלאת קבצים": "upload", "סנכרון עכשיו": "refresh",
  "מפתח חדש": "key", "יצירת מפתח": "key", "ביטול מפתח": "x", "להחיל": "save", "העתקה": "copy", "בדיקה": "zap" };
function el(tag, props = {}, ...kids) {
  const { dataset, ...rest } = props;
  const e = Object.assign(document.createElement(tag), rest);
  if (dataset) Object.assign(e.dataset, dataset);
  e.append(...kids.filter(k => k !== null && k !== undefined));
  if (tag === "button" && BUTTON_ICONS[props.textContent]) e.prepend(icon(BUTTON_ICONS[props.textContent]));
  return e;
}
// money: whole dollars from $100, cents from 1 cent, and 4 decimals only for sub-cent amounts (single requests)
const money = v => "$" + (v >= 100 ? v.toFixed(0) : v >= 0.01 || v === 0 ? v.toFixed(2) : v.toFixed(4));
// date then time, isolated left-to-right so Hebrew text around it can't reorder the parts
const when = ts => {
  const d = new Date(ts * 1000), p = n => String(n).padStart(2, "0");
  return `${d.getDate()}.${d.getMonth() + 1}.${d.getFullYear()}  ${p(d.getHours())}:${p(d.getMinutes())}`;
};
const whenEl = ts => el("span", { className: "ltr muted small", style: "white-space:nowrap", textContent: when(ts) });
const num = (text, cls = "num") => el("span", { className: cls, textContent: text });
const actionNames = { create: "חשבון נוצר", update: "חשבון עודכן", delete: "חשבון נמחק", "key-new": "הונפק מפתח חדש",
  "key-revoke": "מפתח בוטל", "team-save": "צוות נשמר", "team-delete": "צוות נמחק", "source-save": "מקור מידע נשמר",
  "source-delete": "מקור מידע נמחק", "source-upload": "הועלו מסמכים", "source-sync": "תיקייה סונכרנה",
  "model-save": "מודל נשמר", "model-delete": "מודל נמחק", "model-default": "נקבע מודל ברירת מחדל", "model-auto": "בחירה אוטומטית עודכנה" };

async function api(path, body) {
  const r = await fetch("/admin/api/" + path, {
    method: body ? "POST" : "GET",
    headers: { "x-admin-password": pw, "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (r.status === 401) { showLogin(pw ? "סיסמה שגויה" : ""); throw new Error("unauthorized"); }
  if (!r.ok) throw new Error(data.error || r.status);
  return data;
}

function showLogin(msg) {
  $("login").hidden = false;
  document.querySelectorAll("[data-page]").forEach(s => s.hidden = true);
  $("loginError").textContent = msg;
}

// ---------- tabs ----------
let tab = "overview";
try { tab = sessionStorage.getItem("tab") || "overview"; } catch {}
const hashTab = () => location.hash.slice(1);
if (document.querySelector(`[data-page="${hashTab()}"]`)) tab = hashTab();  // links like /#models from the docs page
addEventListener("hashchange", () => { if (document.querySelector(`[data-page="${hashTab()}"]`)) showTab(hashTab()); });
function showTab(name) {
  tab = name;
  try { sessionStorage.setItem("tab", name); } catch {}
  document.querySelectorAll(".sidebar [data-tab]").forEach(b => b.dataset.tab === name ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current"));
  const changed = document.querySelector(`[data-page="${name}"]`)?.hidden;
  document.querySelectorAll("[data-page]").forEach(s => s.hidden = s.dataset.page !== name);
  if (changed) scrollTo(0, 0);
  renderCrumbs(name);
  if (hashTab() !== name) history.replaceState(null, "", "#" + name);
  if (name === "overview") drawDaily();
  if (name === "models") drawModelCharts();
  if (name === "reports") loadReport();
}
// breadcrumbs from the side menu itself: FireGate › section › page
function renderCrumbs(name) {
  const btn = document.querySelector(`.sidebar [data-tab="${name}"]`);
  if (!btn) return;
  let header = btn.closest("li");
  while (header && !header.classList.contains("sidebar-header")) header = header.previousElementSibling;
  const page = btn.textContent.trim(), group = header ? header.textContent.trim() : "";
  const home = el("a", { href: "#", textContent: "FireGate", onclick: e => { e.preventDefault(); showTab("overview"); } });
  $("crumbs").replaceChildren(
    el("li", {}, home),
    ...(group && group !== "ראשי" ? [el("li", { className: "group", textContent: group })] : []),
    el("li", {}, el("span", { ariaCurrent: "page", textContent: page })));
  document.title = `FireGate · ${page}`;
}
document.querySelectorAll(".sidebar [data-tab]").forEach(b => b.onclick = () => {
  showTab(b.dataset.tab);
  if (matchMedia("(max-width: 991px)").matches) $("sidebar").classList.remove("open");
});
UI.sideMenu($("sidebar"), $("toggle"));
$("overviewNewAccount").onclick = () => openAccount(null);
document.querySelectorAll("[data-close]").forEach(b => b.onclick = () => b.closest("dialog").close());

// ---------- shared pieces ----------
function icon(name) {
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg"), use = document.createElementNS(ns, "use");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  use.setAttribute("href", "#i-" + name);
  svg.append(use);
  return svg;
}
// AdminKit-style stat card: title + round icon, big value, then a coloured change and what it's compared with
function statCard(title, iconName, value, change, sub) {
  return el("div", { className: "card stat-card" },
    el("div", { className: "top" }, el("h2", { className: "card-title", textContent: title }), el("div", { className: "stat" }, icon(iconName))),
    el("div", { className: "stat-value" }, num(value)),
    el("div", { className: "stat-delta" }, change || null, el("span", { className: "muted", textContent: sub })));
}
// percent change; for spending, going up is bad
function change(now, before, upIsGood) {
  if (!before) return el("span", { className: "delta flat", textContent: now ? "חדש" : "—" });
  const pct = (now - before) / before * 100;
  const good = Math.abs(pct) < 0.5 ? null : (pct > 0) === upIsGood;
  return el("span", { className: "delta " + (good === null ? "flat" : good ? "good" : "bad"), dir: "ltr",
    textContent: (pct > 0 ? "+" : "") + pct.toFixed(1) + "%" });
}
function level(spent, budget) {
  if (!budget) return "";
  const pct = spent / budget;
  return pct >= 1 ? "bad" : pct >= state.soft_limit ? "warn" : "";
}
function meter(spent, budget, noCapText) {
  const lv = level(spent, budget);
  const pct = budget ? Math.min(spent / budget, 1) * 100 : 0;
  return el("div", { className: "meter " + lv },
    el("div", { className: "label" }, num(money(spent)), num(budget ? `מתוך ${money(budget)}` : noCapText || "ללא תקרה", "muted")),
    el("div", { className: "track" }, el("div", { className: "fill", style: `width:${pct}%` })));
}
// a raise is urgent (the person is about to be blocked); a cut is only a hint, so it gets no button
function suggestion(item) {
  if (!item.budget || !item.recommended) return null;  // 0 = no cap: never turn "unlimited" into a cap
  if (item.projected > item.budget * 0.9 && item.recommended > item.budget) return "raise";
  if (item.last_month > 0 && item.recommended < item.budget * 0.25) return "lower";
  return null;
}
function recommendCell(item, kind) {
  const label = "תקציב מומלץ", hint = suggestion(item);
  if (!item.budget) return el("td", { className: "num muted", dataset: { label }, textContent: "ללא תקרה" });
  if (hint === "lower") return el("td", { className: "num muted small", dataset: { label },
    title: `בחודש שעבר: ${money(item.last_month)}. אפשר לעדכן בעריכה.`, textContent: `אפשר להוריד ל-${money(item.recommended)}` });
  if (hint !== "raise") return el("td", { className: "num muted", dataset: { label }, textContent: "מתאים" });
  return el("td", { className: "num", dataset: { label } }, el("div", { className: "row", style: "justify-content:flex-end;gap:8px" },
    num(money(item.recommended)),
    el("button", { className: "soft sm", textContent: "להחיל", title: "להעלות את התקציב לסכום המומלץ לפני שהחשבון ייחסם",
      onclick: () => applyBudget(kind, item, item.recommended) })));
}
async function setBudget(kind, name, budget) {
  await api(kind === "team" ? "teams" : "accounts/update", { name, budget });
}
async function applyBudget(kind, item, budget) {
  const who = kind === "team" ? `צוות ${item.name}` : item.name;
  const body = el("div", { className: "grid", style: "gap:10px" },
    el("div", { className: "change-line" }, num(money(item.budget), "num old"), el("span", { textContent: "←" }), el("b", {}, num(money(budget)))),
    el("p", { className: "small", textContent: budget > item.budget
      ? `בקצב הנוכחי ${who} יוציא ${money(item.projected)} עד סוף החודש.`
      : `בחודש שעבר ${who} הוציא ${money(item.last_month)}. התקציב הנוכחי גבוה בהרבה מהצורך.` }));
  if (!await UI.confirm({ title: `לעדכן את התקציב של ${who}?`, body, ok: "עדכון התקציב" })) return;
  try {
    await setBudget(kind, item.name, budget);
    await load();
    UI.toast(`התקציב של ${who} עודכן ל-${money(budget)}.`, { action: "ביטול השינוי", onAction: async () => {
      await setBudget(kind, item.name, item.budget);
      await load();
      UI.toast(`התקציב של ${who} חזר ל-${money(item.budget)}.`);
    } });
  } catch (e) { fail(e); }
}
const PROVIDER_NAMES = { anthropic: "Claude", openai: "GPT", gemini: "Gemini" };
function modelChecks(container, checked) {
  container.replaceChildren(...state.models.map(m => {
    const info = (state.model_info || {})[m] || {};
    const tier = m.endsWith("smart") ? "חכם" : m.endsWith("fast") ? "מהיר" : "";
    return el("label", { className: "model-option" }, el("input", { type: "checkbox", value: m, checked: checked.includes(m) }),
      el("span", { textContent: info.label || `${PROVIDER_NAMES[info.provider] || ""} ${tier}`.trim() }),
      el("small", { className: "ltr", textContent: `${m} · $${info.price_in} / $${info.price_out}` }),
      info.enabled === false ? el("span", { className: "badge", textContent: "כבוי" }) : null);
  }));
}
const checkedModels = c => [...c.querySelectorAll("input:checked")].map(i => i.value);
function showKey(key) {
  $("keyValue").textContent = key;
  $("copyKey").lastChild.textContent = "העתקה";
  $("keyDialog").showModal();
}
$("copyKey").onclick = async () => {
  try { await navigator.clipboard.writeText($("keyValue").textContent); $("copyKey").lastChild.textContent = "הועתק ✓"; }
  catch { getSelection().selectAllChildren($("keyValue")); }
};
const MODEL_ERRORS = {
  "alias must be 2-40 lowercase letters, digits, dot, dash or underscore": "הכינוי צריך להיות 2 עד 40 אותיות אנגליות קטנות, ספרות, נקודה, מקף או קו תחתון",
  "unknown provider": "ספק לא מוכר", "model id is required": "צריך למלא את שם המודל אצל הספק", "price must be >= 0": "המחיר לא יכול להיות שלילי",
  "this is the default model; choose another default before turning it off": "זה מודל ברירת המחדל. קודם קובעים ברירת מחדל אחרת, ואז אפשר לכבות אותו",
  "this is the default model; choose another default first": "זה מודל ברירת המחדל. קודם קובעים ברירת מחדל אחרת",
  "backup model must be another existing model": "מודל הגיבוי צריך להיות מודל אחר מהרשימה",
  "meaning search needs an OpenAI or Google key in ⁦.env⁩": "חיפוש לפי משמעות צריך מפתח של OpenAI או Google בקובץ ⁦.env⁩",
  "reading PDF needs the pypdf package on the server": "קריאת PDF צריכה את הספרייה pypdf בשרת",
  "MCP server address must start with http:// or https://": "כתובת שרת ה-MCP צריכה להתחיל ב-http:// או https://",
  "choose the MCP tool to call": "צריך לבדוק חיבור ולבחור את כלי החיפוש",
  "only folder sources and MCP sources in sync mode can be synced": "אפשר לסנכרן רק תיקייה או שרת MCP במצב סנכרון",
  "turn the model on before making it the default": "קודם מדליקים את המודל, ואז אפשר לקבוע אותו כברירת מחדל" };
const ERRORS = { ...MODEL_ERRORS, "nothing to update": "אין מה לעדכן", "pick at least one known model": "צריך לבחור לפחות מודל אחד",
  "password must be at least 8 characters": "הסיסמה צריכה להיות באורך 8 תווים לפחות", "budget must be >= 0": "התקציב לא יכול להיות שלילי",
  "name is required": "צריך למלא שם", "give a password (chat login) or an API key, or both": "צריך סיסמה לצ'אט, מפתח API, או את שניהם" };
const hebrew = msg => ERRORS[msg] || (/already exists/.test(msg) ? "השם הזה כבר קיים" : /folder not found/.test(msg) ? "התיקייה לא נמצאה בשרת"
  : /^MCP server: /.test(msg) ? "שרת ה-MCP: " + msg.slice(12)
  : /could not read the file/.test(msg) ? `${msg.split(":")[0]}: לא הצלחנו לקרוא את הקובץ (פגום או מוצפן)`
  : /no text found/.test(msg) ? `${msg.split(":")[0]}: אין בקובץ טקסט (קובץ סרוק צריך זיהוי טקסט קודם)`
  : /accounts still use this model/.test(msg) ? `${parseInt(msg)} משתמשים עדיין מורשים להשתמש במודל. אפשר לכבות אותו, או להסיר אותו מהמשתמשים קודם` : msg);
const fail = e => { if (e.message !== "unauthorized") UI.toast(hebrew(e.message), { kind: "bad", timeout: 9000 }); };
const run = (fn, done) => async () => { try { const r = await fn(); if (r === false) return; await load(); if (done) UI.toast(done); } catch (e) { fail(e); } };

// ---------- charts ----------
let daily = [];
function lastDays(n) {
  const byDay = Object.fromEntries(daily.map(d => [d.day, d]));
  const out = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(Date.now() - i * 86400000);
    const key = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    out.push({ key, date: d, cost: byDay[key]?.cost || 0, requests: byDay[key]?.requests || 0 });
  }
  return out;
}
function drawDaily() {
  const box = $("dailyChart");
  const W = box.clientWidth;
  if (!W) return;
  const H = 260, padL = 48, padB = 26, padT = 12, padR = 8;
  const days = lastDays(30);
  const max = Math.max(...days.map(d => d.cost));
  if (!max) { box.replaceChildren(el("div", { className: "empty", textContent: "עוד אין שימוש ב-30 הימים האחרונים" })); return; }
  // round axis steps: 1, 2, 2.5 or 5 times a power of ten, four gridlines
  const raw = max / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].find(s => s * mag >= raw) * mag;
  const lines = Math.max(1, Math.ceil(max / step)), top = step * lines;
  const axisMoney = v => "$" + (step >= 1 ? v.toFixed(0) : v.toFixed(Math.min(4, Math.ceil(-Math.log10(step)) + 1)).replace(/\.?0+$/, ""));
  const plotW = W - padL - padR, plotH = H - padB - padT;
  const x = i => padL + (i / (days.length - 1)) * plotW;
  const y = v => padT + plotH - (v / top) * plotH;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("direction", "ltr");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "הוצאה יומית ב-30 הימים האחרונים");
  const add = (tag, attrs, text, parent = svg) => {
    const n = document.createElementNS(ns, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    parent.append(n); return n;
  };
  const grad = add("linearGradient", { id: "areaFill", x1: 0, y1: 0, x2: 0, y2: 1 }, undefined, add("defs", {}));
  add("stop", { offset: "0%", "stop-color": "var(--accent)", "stop-opacity": .25 }, undefined, grad);
  add("stop", { offset: "100%", "stop-color": "var(--accent)", "stop-opacity": 0 }, undefined, grad);
  for (let i = 0; i <= lines; i++) {
    const v = step * i, yy = y(v);
    add("line", { x1: padL, x2: W - padR, y1: yy, y2: yy, class: i ? "grid-line" : "base-line" });
    add("text", { x: padL - 8, y: yy + 4, "text-anchor": "end", class: "tick" }, axisMoney(v));
  }
  const pts = days.map((d, i) => [x(i), y(d.cost)]);
  const line = pts.map(([px, py], i) => (i ? "L" : "M") + px.toFixed(1) + "," + py.toFixed(1)).join(" ");
  add("path", { d: `${line} L${x(days.length - 1)},${y(0)} L${x(0)},${y(0)} Z`, fill: "url(#areaFill)" });
  add("path", { d: line, class: "line" });
  days.forEach((d, i) => {
    if (i % 5 === 0 || i === days.length - 1)
      add("text", { x: x(i), y: H - 6, "text-anchor": "middle", class: "tick" }, d.date.getDate() + "/" + (d.date.getMonth() + 1));
  });
  // hover: crosshair + dot + tooltip on the nearest day
  const cross = add("line", { y1: padT, y2: y(0), class: "cross", visibility: "hidden" });
  const dot = add("circle", { r: 5, class: "dot", visibility: "hidden" });
  const hit = add("rect", { x: padL, y: padT, width: plotW, height: plotH, fill: "transparent" });
  const tip = el("div", { className: "tip", hidden: true });
  hit.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect();
    const i = Math.max(0, Math.min(days.length - 1, Math.round(((e.clientX - r.left) * (W / r.width) - padL) / plotW * (days.length - 1))));
    const d = days[i], [px, py] = pts[i];
    for (const n of [cross, dot]) n.setAttribute("visibility", "visible");
    cross.setAttribute("x1", px); cross.setAttribute("x2", px);
    dot.setAttribute("cx", px); dot.setAttribute("cy", py);
    tip.hidden = false;
    tip.textContent = `${d.date.toLocaleDateString("he-IL")} · ${money(d.cost)} · ${d.requests} בקשות`;
    tip.style.left = px * (r.width / W) + "px";
    tip.style.top = py * (r.height / H) + "px";
  });
  hit.addEventListener("mouseleave", () => { for (const n of [cross, dot]) n.setAttribute("visibility", "hidden"); tip.hidden = true; });
  box.replaceChildren(svg, tip);
}
let resizeTimer;
addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { drawDaily(); drawModelCharts(); }, 120); });

// doughnut of spend by model; identity also carried by the legend table, never by colour alone
const SERIES = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6"];
function donut(items) {
  const total = items.reduce((t, i) => t + i.value, 0);
  if (!total) {
    $("modelDonut").replaceChildren(el("div", { className: "empty", textContent: "אין שימוש החודש" }));
    $("modelLegend").replaceChildren();
    return;
  }
  // more than six models: the smallest fold into "אחר" so colours never repeat
  if (items.length > SERIES.length) {
    const rest = items.slice(SERIES.length - 1);
    items = [...items.slice(0, SERIES.length - 1), { label: "אחר", value: rest.reduce((t, i) => t + i.value, 0), req: rest.reduce((t, i) => t + i.req, 0) }];
  }
  const ns = "http://www.w3.org/2000/svg", R = 70, C = 2 * Math.PI * R, gap = items.length > 1 ? 2 : 0;
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 180 180");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "חלוקת ההוצאה לפי מודל");
  let offset = 0;
  items.forEach((it, i) => {
    const len = it.value / total * C;
    const c = document.createElementNS(ns, "circle");
    for (const [k, v] of Object.entries({ cx: 90, cy: 90, r: R, fill: "none", "stroke-width": 22,
      stroke: `var(${SERIES[i]})`, "stroke-dasharray": `${Math.max(len - gap, 0.5)} ${C}`, "stroke-dashoffset": -offset,
      transform: "rotate(-90 90 90)" })) c.setAttribute(k, v);
    const t = document.createElementNS(ns, "title");
    t.textContent = `${it.label}: ${money(it.value)} (${Math.round(it.value / total * 100)}%)`;
    c.append(t);
    svg.append(c);
    offset += len;
  });
  $("modelDonut").replaceChildren(svg, el("div", { className: "center" }, el("b", {}, num(money(total))), el("span", { className: "muted small", textContent: "סה\"כ החודש" })));
  $("modelLegend").replaceChildren(...items.map((it, i) => el("tr", {},
    el("td", {}, el("span", { className: "legend-dot", style: `background:var(${SERIES[i]})` }), el("span", { className: "ltr", style: "white-space:nowrap", title: it.label, textContent: it.label.replace(/-\d{8}$/, "") })),
    el("td", { className: "num muted small", style: "white-space:nowrap", textContent: it.req + " בקשות" }),
    el("td", { className: "num" }, num(money(it.value))),
    el("td", { className: "num muted", textContent: Math.round(it.value / total * 100) + "%" }))));
}

// ---------- load + render ----------
let loadedOnce = false;
async function load() {
  const btn = $("refresh");
  btn.classList.add("busy");
  btn.setAttribute("aria-busy", "true");
  if (!loadedOnce) $("loadState").replaceChildren(el("div", { className: "grid kpis" }, ...[1, 2, 3, 4].map(() => el("div", { className: "skeleton" }))));
  let data;
  try {
    data = await Promise.all([api("overview"), api("usage"), api("daily"), api("logs"), api("audit"), api("sources"), api("security"), api("models"), api("models/daily"), api("sources/status")]);
  } catch (e) {
    if (e.message !== "unauthorized") {
      showTab(tab);
      $("loadState").replaceChildren(el("div", { className: "alert bad", role: "alert" }, icon("alert"),
        el("span", { className: "grow", textContent: `לא הצלחנו לטעון את הנתונים מהשער (${hebrew(e.message)}). ייתכן שהשרת לא זמין.` }),
        el("button", { className: "ghost sm", textContent: "לנסות שוב", onclick: () => load().catch(() => {}) })));
      if (loadedOnce) fail(e);
    }
    throw e;
  } finally {
    btn.classList.remove("busy");
    btn.removeAttribute("aria-busy");
  }
  loadedOnce = true;
  $("loadState").replaceChildren();
  const [ov, usage, d, lg, audit, src, sec, mdl, mdaily, sstat] = data;
  sourceStatus = sstat;
  modelsData = mdl;
  modelsDaily = mdaily;
  security = sec;
  renderSecurity();
  state = ov; daily = d; logs = lg; sourceList = src;
  renderSources();
  $("login").hidden = true;
  showTab(tab);

  // KPIs: this week against the week before, and the month's projection against last month
  const spent = ov.accounts.reduce((t, a) => t + a.spent, 0);
  const projected = ov.accounts.reduce((t, a) => t + a.projected, 0);
  const lastMonth = ov.accounts.reduce((t, a) => t + a.last_month, 0);
  const days14 = lastDays(14), thisWeek = days14.slice(7), prevWeek = days14.slice(0, 7);
  const sum = (arr, k) => arr.reduce((t, d) => t + d[k], 0);
  const active = new Set(usage.map(u => u.name)).size;
  $("kpis").replaceChildren(
    statCard("הוצאה החודש", "dollar", money(spent), change(sum(thisWeek, "cost"), sum(prevWeek, "cost"), false), "השבוע לעומת השבוע הקודם"),
    statCard("צפי לסוף החודש", "trend", money(projected), change(projected, lastMonth, false), `לעומת חודש קודם (${money(lastMonth)})`),
    statCard("בקשות החודש", "activity", usage.reduce((t, u) => t + u.requests, 0).toLocaleString("he-IL"),
      change(sum(thisWeek, "requests"), sum(prevWeek, "requests"), true), "השבוע לעומת השבוע הקודם"),
    statCard("משתמשים פעילים", "user-check", String(active), el("span", { className: "delta flat", textContent: `${Math.round(active / Math.max(ov.accounts.length, 1) * 100)}%` }),
      `מתוך ${ov.accounts.length} חשבונות`));

  // getting started: shown until the basics exist
  const steps = [
    [security.providers.length > 0, "לחבר ספק: להכניס מפתח של Anthropic, ‏OpenAI או Google לקובץ ⁦.env⁩ ולהפעיל את השער מחדש", null],
    [ov.teams.length > 0, "ליצור צוות עם תקציב חודשי", () => { showTab("teams"); openTeam(null); }],
    [ov.accounts.length > 0, "ליצור משתמש ראשון", () => openAccount(null)],
    [usage.length > 0, "לשאול שאלה ראשונה במסך הצ'אט", () => { location.href = "/chat"; }],
  ];
  const doneCount = steps.filter(([ok]) => ok).length;
  $("startCard").hidden = doneCount === steps.length;
  $("startProgress").textContent = `${doneCount} מתוך ${steps.length}`;
  $("startSteps").replaceChildren(...steps.map(([ok, text, go]) => el("li", { className: ok ? "done" : "" },
    el("span", { className: "grow", textContent: text }),
    !ok && go ? el("button", { className: "ghost sm", textContent: "לעשות את זה", onclick: go }) : null)));

  // alerts
  const alerts = [];
  for (const a of ov.accounts) {
    const lv = level(a.spent, a.budget);
    if (lv) alerts.push([lv, lv === "bad" ? `${a.name}: התקציב האישי נגמר (${money(a.spent)} מתוך ${money(a.budget)}). חסום עד 1 לחודש או עד הגדלת תקציב.`
      : `${a.name}: עבר ${Math.round(a.spent / a.budget * 100)}% מהתקציב האישי.`]);
    if (a.locked) alerts.push(["warn", `${a.name}: החשבון נעול אחרי 5 סיסמאות שגויות. איפוס סיסמה משחרר אותו.`]);
  }
  for (const t of ov.teams) {
    const lv = level(t.spent, t.budget);
    if (lv) alerts.push([lv, lv === "bad" ? `צוות ${t.name}: תקציב הצוות נגמר. כל חברי הצוות חסומים.` : `צוות ${t.name}: עבר ${Math.round(t.spent / t.budget * 100)}% מתקציב הצוות.`]);
  }
  // the provider-key check already leads the getting-started card while that card is visible
  for (const ch of security.checks) if (!ch.ok && !(security.providers.length === 0 && !$("startCard").hidden && /ספקים/.test(ch.text)))
    alerts.push(["warn", ch.text, "security"]);
  const order = { bad: 0, warn: 1 };
  alerts.sort((a, b) => order[a[0]] - order[b[0]]);
  $("alertsCard").hidden = false;
  $("alertsCount").textContent = alerts.length ? `${alerts.length} פריטים` : "";
  $("alerts").replaceChildren(...alerts.map(([lv, text, page]) => el("div", { className: "alert " + lv }, icon("alert"),
    el("span", { className: "grow", textContent: text }),
    page ? el("button", { className: "link small", textContent: "לפרטים", onclick: () => showTab(page) }) : null)));
  if (!alerts.length) $("alerts").append(el("div", { className: "alert good" }, icon("check"), el("span", { textContent: "הכל תקין: אין חריגות תקציב ואין הערות אבטחה פתוחות." })));

  drawDaily();
  const modelTotals = {};
  usage.forEach(u => { modelTotals[u.model] = modelTotals[u.model] || { value: 0, req: 0 }; modelTotals[u.model].value += u.cost; modelTotals[u.model].req += u.requests; });
  donut(Object.entries(modelTotals).sort((a, b) => b[1].value - a[1].value).map(([m, v]) => ({ label: m, value: v.value, req: v.req })));

  const reqBy = {};
  usage.forEach(u => reqBy[u.name] = (reqBy[u.name] || 0) + u.requests);
  const top = ov.accounts.filter(a => a.spent > 0).sort((a, b) => b.spent - a.spent).slice(0, 8);
  $("topAccounts").replaceChildren(...top.map(a => {
    const lv = level(a.spent, a.budget), pct = a.budget ? Math.round(a.spent / a.budget * 100) : 0;
    return el("tr", {},
      el("td", { className: "name" }, el("b", { textContent: a.name })),
      el("td", { textContent: a.team || "—", className: a.team ? "" : "muted", dataset: { label: "צוות" } }),
      el("td", { className: "num", dataset: { label: "בקשות" } }, num((reqBy[a.name] || 0).toLocaleString("he-IL"))),
      el("td", { className: "num", dataset: { label: "הוצאה" } }, num(money(a.spent))),
      el("td", { dataset: { label: "מצב תקציב" } }, el("span", { className: "badge " + (lv === "bad" ? "bad" : lv === "warn" ? "warn" : "good"),
        textContent: lv === "bad" ? "חסום" : `${pct}% מהתקציב` })));
  }));
  if (!top.length) $("topAccounts").append(el("tr", {}, el("td", { colSpan: 5, className: "empty", textContent: "אין שימוש החודש" })));

  $("teamSummary").replaceChildren(...ov.teams.map(t => el("div", { className: "team-row" },
    el("div", { className: "name" }, el("span", { textContent: t.name }), el("span", { className: "muted small", textContent: `צפי ${money(t.projected)}` })),
    meter(t.spent, t.budget))));
  if (!ov.teams.length) $("teamSummary").append(el("div", { className: "empty", textContent: "אין צוותים עדיין" }));

  renderAccounts();
  renderModels();

  // teams
  $("teams").replaceChildren(...ov.teams.map(t => el("tr", {},
    el("td", { className: "name" }, el("b", { textContent: t.name })),
    el("td", { className: "num", dataset: { label: "חברים" } }, num(String(t.members))),
    el("td", { dataset: { label: "הוצאה החודש" } }, meter(t.spent, t.budget)),
    el("td", { className: "num", dataset: { label: "צפי" } }, num(money(t.projected))),
    recommendCell(t, "team"),
    el("td", { className: "num", dataset: { label: "סכום תקציבי החברים" } }, num(money(t.members_budget))),
    el("td", {}, el("div", { className: "actions" },
      el("button", { className: "ghost", textContent: "עריכה", onclick: () => openTeam(t) }),
      el("button", { className: "danger", textContent: "מחיקה", onclick: run(() => UI.confirm({ title: `למחוק את צוות ${t.name}?`,
        body: "החברים יישארו בלי צוות, והתקציב של הצוות יימחק. ההיסטוריה ביומן נשארת.", ok: "מחיקת הצוות", danger: true })
        .then(ok => ok ? api("teams/delete", { name: t.name }) : false), `צוות ${t.name} נמחק.`) }))))));
  if (!ov.teams.length) $("teams").append(el("tr", {}, el("td", { colSpan: 7, className: "empty", textContent: "אין צוותים עדיין. לחצו על \"צוות חדש\"." })));

  renderLogs();

  $("audit").replaceChildren(...audit.map(a => el("tr", {},
    el("td", {}, whenEl(a.ts)),
    el("td", { textContent: actionNames[a.action] || a.action }),
    el("td", { className: "small" }, describe(a.detail)))));
  if (!audit.length) $("audit").append(el("tr", {}, el("td", { colSpan: 3, className: "empty", textContent: "אין שינויים עדיין" })));
}

let accountSort = { key: "spent", dir: -1 };
function renderAccounts() {
  const q = $("accountFilter").value.trim().toLowerCase();
  const { key, dir } = accountSort;
  const rows = state.accounts.filter(a => !q || a.name.toLowerCase().includes(q) || (a.team || "").toLowerCase().includes(q))
    .sort((a, b) => (typeof a[key] === "number" ? a[key] - b[key] : String(a[key]).localeCompare(String(b[key]), "he")) * dir);
  document.querySelectorAll("button.sort").forEach(b => b.dataset.sort === key
    ? b.setAttribute("aria-sort", dir > 0 ? "ascending" : "descending") : b.removeAttribute("aria-sort"));
  $("accounts").replaceChildren(...rows.map(a => el("tr", {},
    el("td", { className: "name" }, el("b", { textContent: a.name })),
    el("td", { textContent: a.team || "—", className: a.team ? "" : "muted", dataset: { label: "צוות" } }),
    el("td", { dataset: { label: "מודלים" } }, el("div", { className: "models", title: a.models.join(", ") },
      ...a.models.slice(0, 2).map(m => el("span", { className: "badge", textContent: m })),
      a.models.length > 2 ? el("span", { className: "badge ltr", textContent: "+" + (a.models.length - 2), title: a.models.slice(2).join(", ") }) : null)),
    el("td", { dataset: { label: "הוצאה החודש" } }, meter(a.spent, a.budget)),
    el("td", { className: "num", dataset: { label: "צפי" } }, el("div", { className: "stack" }, num(money(a.projected)),
      a.projected > a.budget ? el("span", { className: "badge warn", textContent: "יעבור את התקציב" }) : null)),
    recommendCell(a, "account"),
    el("td", { dataset: { label: "גישה" } }, el("div", { className: "models" },
      a.has_password ? el("span", { className: "badge", textContent: "צ'אט" }) : null,
      a.key_prefix ? el("span", { className: "badge ltr", textContent: a.key_prefix + "…" }) : null,
      a.locked ? el("span", { className: "badge bad", textContent: "נעול" }) : null,
      a.rpm ? el("span", { className: "badge", textContent: a.rpm + " לדקה" }) : null)),
    el("td", {}, el("div", { className: "actions" },
      el("button", { className: "ghost", textContent: "עריכה", onclick: () => openAccount(a) }),
      el("button", { className: "danger", textContent: "מחיקה", onclick: run(() => UI.confirm({ title: `למחוק את ${a.name}?`,
        body: "הכניסה לצ'אט והמפתח יפסיקו לעבוד מיד. היסטוריית השאלות נשארת ביומן.", ok: "מחיקה", danger: true })
        .then(ok => ok ? api("accounts/delete", { name: a.name }) : false), `${a.name} נמחק.`) }))))));
  if (!rows.length) $("accounts").append(el("tr", {}, el("td", { colSpan: 8, className: "empty",
    textContent: state.accounts.length ? "אין משתמשים שמתאימים לחיפוש." : "אין משתמשים עדיין. לחצו על \"משתמש חדש\"." })));
}
$("accountFilter").oninput = renderAccounts;
document.querySelectorAll("button.sort").forEach(b => b.onclick = () => {
  accountSort = { key: b.dataset.sort, dir: accountSort.key === b.dataset.sort ? -accountSort.dir : (b.dataset.sort === "name" || b.dataset.sort === "team" ? 1 : -1) };
  renderAccounts();
});

function describe(d) {
  const parts = [];
  if (d.name) parts.push(d.name);
  if ("budget" in d) parts.push("old_budget" in d ? `תקציב ${money(d.old_budget)} ← ${money(d.budget)}` : `תקציב ${money(d.budget)}`);
  if (d.team) parts.push(`צוות ${d.team}`);
  if (d.models) parts.push(`מודלים: ${String(d.models).replaceAll(",", ", ")}`);
  if (typeof d.model === "string" && d.provider) parts.push(`${PROVIDER_FULL[d.provider] || d.provider} · ${d.model}`);
  if (d.rpm) parts.push(`${d.rpm} בקשות לדקה`);
  if (d.password === "changed") parts.push("סיסמה הוחלפה");
  if (d.changes) {
    const names = { price_in: "מחיר נכנס", price_out: "מחיר יוצא", price_cached: "מחיר מטמון", fallback: "גיבוי", model: "שם אצל הספק", provider: "ספק", enabled: "פעיל" };
    for (const [k, [a, b]] of Object.entries(d.changes)) parts.push(k === "enabled" ? (b ? "הודלק" : "כובה") : `${names[k] || k}: ${a} ← ${b}`);
  }
  if (d.new) parts.push("נוסף");
  if (Array.isArray(d.teams)) parts.push("גישה: " + (d.teams.includes("*") ? "כל העובדים" : d.teams.join(", ") || "אף אחד"));
  if (Array.isArray(d.files)) parts.push(`${d.files.length} קבצים`);
  if (typeof d.files === "number") parts.push(`${d.files} קבצים${d.skipped ? `, ${d.skipped} דולגו` : ""}`);
  return parts.join(" · ");
}

function renderLogs() {
  const q = $("logFilter").value.trim().toLowerCase();
  const rows = logs.filter(l => !q || [l.name, l.team, l.model].some(v => (v || "").toLowerCase().includes(q)));
  const pretty = s => { try { return JSON.stringify(JSON.parse(s), null, 2); } catch { return s; } };
  $("logs").replaceChildren(...rows.map(l => el("tr", {},
    el("td", {}, whenEl(l.ts)),
    el("td", { textContent: l.name }),
    el("td", { textContent: l.team || "—", className: l.team ? "" : "muted" }),
    el("td", {}, el("span", { className: "badge", textContent: l.model })),
    el("td", { className: "num" }, num(l.tokens_in.toLocaleString())),
    el("td", { className: "num" }, num(l.tokens_out.toLocaleString())),
    el("td", { className: "num" }, num(money(l.cost))),
    el("td", {}, el("details", {}, el("summary", { className: "small", textContent: "שאלה ותשובה", ariaLabel: `השאלה והתשובה של ${l.name}, ${when(l.ts)}` }),
      el("pre", { textContent: pretty(l.request) }), el("pre", { textContent: pretty(l.response) }))))));
  if (!rows.length) $("logs").append(el("tr", {}, el("td", { colSpan: 8, className: "empty", textContent: "אין שאלות" })));
}
$("logFilter").oninput = renderLogs;

// ---------- dialogs ----------
let editingAccount = null;
function openAccount(a) {
  editingAccount = a ? a.name : null;
  $("accountTitle").textContent = a ? `עריכת ${a.name}` : "משתמש חדש";
  $("nameField").hidden = !!a;
  $("aName").required = !a;
  $("aName").value = "";
  $("aTeam").replaceChildren(el("option", { value: "", textContent: "בלי צוות" }), ...state.teams.map(t => el("option", { value: t.name, textContent: t.name })));
  $("aTeam").value = a ? a.team : "";
  $("aBudget").value = a ? a.budget : "";
  $("aRpm").value = a ? a.rpm : 0;
  modelChecks($("aModels"), a ? a.models : [state.default_model || state.models[0]]);
  $("pwLabel").textContent = a ? "סיסמה חדשה לצ'אט (ריק = בלי שינוי; גם משחרר נעילה)" : "סיסמה לכניסה לצ'אט (לפחות 8 תווים; ריק = בלי צ'אט)";
  $("aPassword").value = "";
  $("keyField").hidden = !!a;
  $("aKey").checked = false;
  $("keyRow").hidden = !a;
  if (a) {
    const keyAction = (label, cls, confirmText, action) => el("button", { type: "button", className: cls, textContent: label, onclick: async () => {
      if (confirmText && !await UI.confirm({ title: label + "?", body: confirmText, ok: label, danger: cls === "danger" })) return;
      try {
        const r = await api("accounts/key", { name: a.name, action });
        $("accountDialog").close();
        if (r.key) showKey(r.key);
        load();
      } catch (e) { $("accountError").textContent = hebrew(e.message); }
    } });
    $("keyRow").replaceChildren("מפתח לאפליקציות (API)", el("div", { className: "row" },
      a.key_prefix ? el("span", { className: "badge ltr", textContent: a.key_prefix + "…" }) : el("span", { className: "muted small", textContent: "אין מפתח" }),
      keyAction(a.key_prefix ? "מפתח חדש" : "יצירת מפתח", "ghost", a.key_prefix ? `להנפיק מפתח חדש ל-${a.name}? המפתח הקודם יפסיק לעבוד מיד.` : "", "new"),
      a.key_prefix ? keyAction("ביטול מפתח", "danger", `לבטל את המפתח של ${a.name}? אפליקציות שמשתמשות בו יפסיקו לעבוד מיד.`, "revoke") : null));
  }
  $("accountError").textContent = "";
  $("accountDialog").showModal();
}
$("newAccount").onclick = () => openAccount(null);
$("accountForm").onsubmit = async e => {
  e.preventDefault();
  const body = { team: $("aTeam").value, budget: Number($("aBudget").value), rpm: Number($("aRpm").value || 0), models: checkedModels($("aModels")) };
  if ($("aPassword").value) body.password = $("aPassword").value;
  try {
    if (editingAccount) {
      await api("accounts/update", { name: editingAccount, ...body });
      $("accountDialog").close();
      UI.toast(`השינויים ב-${editingAccount} נשמרו.`);
    } else {
      const r = await api("accounts", { name: $("aName").value, ...body, api_key: $("aKey").checked });
      $("accountDialog").close();
      if (r.key) showKey(r.key); else UI.toast(`${$("aName").value} נוצר.`);
    }
    load();
  } catch (err) { $("accountError").textContent = hebrew(err.message); }
};

let editingTeam = null;
function openTeam(t) {
  editingTeam = t ? t.name : null;
  $("teamTitle").textContent = t ? `עריכת צוות ${t.name}` : "צוות חדש";
  $("tNameField").hidden = !!t;
  $("tName").required = !t;
  $("tName").value = "";
  $("tBudget").value = t ? t.budget : 0;
  $("teamError").textContent = "";
  $("teamDialog").showModal();
}
$("newTeam").onclick = () => openTeam(null);
$("teamForm").onsubmit = async e => {
  e.preventDefault();
  try {
    await api("teams", { name: editingTeam || $("tName").value, budget: Number($("tBudget").value) });
    $("teamDialog").close();
    UI.toast(editingTeam ? `צוות ${editingTeam} עודכן.` : "הצוות נוצר.");
    load();
  } catch (err) { $("teamError").textContent = hebrew(err.message); }
};

// ---------- models ----------
let modelsData = { models: [], default_model: null, providers: {} };
const PROVIDER_FULL = { anthropic: "Anthropic", openai: "OpenAI", gemini: "Google" };
function saveModel(m, changes) {
  return api("models", { name: m.alias, label: m.label, provider: m.provider, model: m.model, price_in: m.price_in,
    price_out: m.price_out, price_cached: m.price_cached, fallback: m.fallback || "", enabled: m.enabled, ...changes });
}
async function toggleModel(m) {
  const label = m.label || m.alias;
  if (m.enabled) {
    const ok = await UI.confirm({ title: `לכבות את ${label}?`, ok: "כיבוי", danger: true,
      body: m.users ? `${m.users} משתמשים ואפליקציות מורשים להשתמש בו. מרגע הכיבוי הם יקבלו הודעה שהמודל כבוי, עד שתדליקו אותו שוב.`
        : "אף משתמש לא מורשה להשתמש בו כרגע." });
    if (!ok) return;
  }
  try {
    await saveModel(m, { enabled: !m.enabled });
    await load();
    UI.toast(`${label} ${m.enabled ? "כובה" : "הודלק"}.`, { action: "ביטול", onAction: async () => {
      await saveModel(m, { enabled: m.enabled });
      await load();
    } });
  } catch (e) { fail(e); }
}
async function testModel(m, btn) {
  btn.classList.add("busy");
  btn.setAttribute("aria-busy", "true");
  try {
    const r = await api("models/test", { name: m.alias });
    UI.toast(r.ok ? `${m.label || m.alias} עונה: החיבור תקין (${r.ms} מילישניות).`
      : `${m.label || m.alias} לא עונה: ${r.error === "no API key for this provider in ⁦.env⁩" ? `אין מפתח של ${PROVIDER_FULL[m.provider]} בקובץ ⁦.env⁩` : r.error}`,
      { kind: r.ok ? "good" : "bad", timeout: r.ok ? 6000 : 12000 });
  } catch (e) { fail(e); }
  finally { btn.classList.remove("busy"); btn.removeAttribute("aria-busy"); }
}
// ---------- automatic choice ----------
function renderAuto() {
  const a = modelsData.auto, on = modelsData.models.filter(m => m.enabled);
  $("autoEnabled").setAttribute("aria-checked", String(a.enabled));
  for (const [id, val] of [["autoCheap", a.cheap], ["autoStrong", a.strong]]) {
    $(id).replaceChildren(...on.map(m => el("option", { value: m.alias, textContent: `${m.label || m.alias} ($${m.price_in} / $${m.price_out})` })));
    $(id).value = val;
  }
  $("autoCount").textContent = a.count ? `${a.count.toLocaleString("he-IL")} שאלות נותבו החודש` : "";
}
$("autoEnabled").onclick = () => $("autoEnabled").setAttribute("aria-checked", String($("autoEnabled").getAttribute("aria-checked") !== "true"));
$("autoForm").onsubmit = run(async () => {
  await api("models/auto", { name: "auto", enabled: $("autoEnabled").getAttribute("aria-checked") === "true",
    cheap: $("autoCheap").value, strong: $("autoStrong").value });
}, "הגדרות הבחירה האוטומטית נשמרו.");
$("autoForm").addEventListener("submit", e => e.preventDefault(), true);

// ---------- reports ----------
let report = null;
const monthName = m => { const [y, mo] = m.split("-"); return new Date(+y, +mo - 1, 1).toLocaleDateString("he-IL", { month: "long", year: "numeric" }); };
async function loadReport() {
  const month = $("reportMonth").value || new Date().toISOString().slice(0, 7);
  try { report = await api("report?month=" + month); } catch (e) { return fail(e); }
  if ($("reportMonth").options.length !== report.months.length) {
    $("reportMonth").replaceChildren(...report.months.map(m => el("option", { value: m, textContent: monthName(m) })));
  }
  $("reportMonth").value = report.month;
  const t = report.totals;
  const tile = (label, ic, value, sub) => statCard(label, ic, value, null, sub);
  $("reportKpis").replaceChildren(
    tile("הוצאה", "dollar", money(t.cost), monthName(report.month)),
    tile("בקשות", "activity", t.requests.toLocaleString("he-IL"), "כל הספקים"),
    tile("אנשים ואפליקציות", "users", String(t.people), "שהשתמשו בחודש הזה"),
    tile("ממוצע לבקשה", "trend", money(t.requests ? t.cost / t.requests : 0), "עלות ממוצעת"));
  const pct = (v, b) => b ? Math.round(v / b * 100) + "%" : "—";
  const empty = (tb, n) => { if (!tb.childElementCount) tb.append(el("tr", {}, el("td", { colSpan: n, className: "empty", textContent: "אין שימוש בחודש הזה" }))); };
  $("reportTeams").replaceChildren(...report.by_team.map(r => el("tr", {},
    el("td", { className: "name" }, el("b", { textContent: r.key || "בלי צוות" })),
    el("td", { className: "num", dataset: { label: "בקשות" } }, num(r.requests.toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "הוצאה" } }, num(money(r.cost))),
    el("td", { className: "num", dataset: { label: "תקציב" } }, num(r.budget ? money(r.budget) : "—")),
    el("td", { className: "num", dataset: { label: "ניצול" } }, num(pct(r.cost, r.budget))))));
  empty($("reportTeams"), 5);
  $("reportAccounts").replaceChildren(...report.by_account.map(r => el("tr", {},
    el("td", { className: "name" }, el("b", { textContent: r.key })),
    el("td", { dataset: { label: "צוות" }, textContent: r.team || "—" }),
    el("td", { className: "num", dataset: { label: "בקשות" } }, num(r.requests.toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "טוקנים" } }, num((r.tokens_in + r.tokens_out).toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "הוצאה" } }, num(money(r.cost))),
    el("td", { className: "num", dataset: { label: "תקציב" } }, num(r.budget != null ? money(r.budget) : "—")))));
  empty($("reportAccounts"), 6);
  $("reportModels").replaceChildren(...report.by_model.map(r => el("tr", {},
    el("td", { className: "ltr", style: "text-align:start", textContent: r.key }),
    el("td", { className: "num", dataset: { label: "בקשות" } }, num(r.requests.toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "טוקנים" } }, num((r.tokens_in + r.tokens_out).toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "מתוכם מהמטמון" } }, num((r.cache_read || 0).toLocaleString("he-IL"))),
    el("td", { className: "num", dataset: { label: "הוצאה" } }, num(money(r.cost))))));
  empty($("reportModels"), 5);
}
$("reportMonth").onchange = loadReport;
// one file with three sections; the byte-order mark makes Excel read the Hebrew correctly
$("reportCsv").onclick = () => {
  if (!report) return;
  const q = v => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const row = cells => cells.map(q).join(",");
  const lines = [row([`דוח שימוש בבינה מלאכותית · ${monthName(report.month)}`]), "",
    row(["לפי צוות"]), row(["צוות", "בקשות", "הוצאה ($)", "תקציב ($)"]),
    ...report.by_team.map(r => row([r.key || "בלי צוות", r.requests, r.cost.toFixed(4), r.budget ?? ""])), "",
    row(["לפי משתמש"]), row(["שם", "צוות", "בקשות", "טוקנים נכנסים", "טוקנים יוצאים", "הוצאה ($)", "תקציב ($)"]),
    ...report.by_account.map(r => row([r.key, r.team, r.requests, r.tokens_in, r.tokens_out, r.cost.toFixed(4), r.budget ?? ""])), "",
    row(["לפי מודל"]), row(["מודל", "בקשות", "טוקנים נכנסים", "טוקנים יוצאים", "טוקנים מהמטמון", "הוצאה ($)"]),
    ...report.by_model.map(r => row([r.key, r.requests, r.tokens_in, r.tokens_out, r.cache_read || 0, r.cost.toFixed(4)])), "",
    row(["סה\"כ", report.totals.requests, report.totals.cost.toFixed(4)])];
  const url = URL.createObjectURL(new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" }));
  const a = el("a", { href: url, download: `ai-usage-${report.month}.csv` });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

// ---------- models charts ----------
let modelsDaily = [];
// colour follows the model (its place in the list), never its rank, so a model keeps its colour when others change
function modelColor(alias) {
  const i = modelsData.models.findIndex(m => m.alias === alias);
  return i >= 0 && i < SERIES.length ? `var(${SERIES[i]})` : "var(--muted)";
}
function aliasOf(realModel) {
  const m = modelsData.models.find(m => m.model === realModel);
  return m ? m.alias : null;
}
const modelName = alias => { const m = modelsData.models.find(x => x.alias === alias); return m ? (m.label || m.alias) : "אחר"; };

function drawModelCharts() {
  if ($("modelDailyChart").closest("[data-page]").hidden) return;
  drawModelDaily();
  drawShare();
}

function drawModelDaily() {
  const box = $("modelDailyChart"), W = box.clientWidth;
  if (!W) return;
  // series: models in list order (first six get colours), anything else folds into "אחר"
  const known = modelsData.models.slice(0, SERIES.length).map(m => m.alias);
  const keyOf = real => { const a = aliasOf(real); return a && known.includes(a) ? a : "_other"; };
  const byDay = {};
  for (const r of modelsDaily) {
    const k = keyOf(r.model);
    (byDay[r.day] = byDay[r.day] || {})[k] = ((byDay[r.day] || {})[k] || 0) + r.cost;
  }
  const days = lastDays(30).map(d => ({ ...d, parts: byDay[d.key] || {} }));
  const series = [...known, "_other"].filter(k => days.some(d => d.parts[k]));
  $("modelDailyLegend").replaceChildren(...series.map(k => el("span", {},
    el("i", { className: "legend-dot", style: `background:${k === "_other" ? "var(--muted)" : modelColor(k)}` }),
    k === "_other" ? "אחר" : modelName(k))));
  const totals = days.map(d => series.reduce((t, k) => t + (d.parts[k] || 0), 0));
  const max = Math.max(...totals);
  if (!max) { box.replaceChildren(el("div", { className: "empty", textContent: "עוד אין שימוש ב-30 הימים האחרונים" })); return; }
  const H = 260, padL = 48, padB = 26, padT = 12, padR = 4;
  const raw = max / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].find(s => s * mag >= raw) * mag;
  const lines = Math.max(1, Math.ceil(max / step)), top = step * lines;
  const axisMoney = v => "$" + (step >= 1 ? v.toFixed(0) : v.toFixed(Math.min(4, Math.ceil(-Math.log10(step)) + 1)).replace(/\.?0+$/, ""));
  const plotW = W - padL - padR, plotH = H - padB - padT, slot = plotW / days.length, bw = Math.max(3, slot - 3);
  const y = v => padT + plotH - (v / top) * plotH;
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("height", H);
  svg.setAttribute("direction", "ltr");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "הוצאה יומית לפי מודל ב-30 הימים האחרונים. הפירוט המלא בטבלת המודלים שמתחת.");
  const add = (tag, attrs, text) => {
    const n = document.createElementNS(ns, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    svg.append(n); return n;
  };
  for (let i = 0; i <= lines; i++) {
    const v = step * i, yy = y(v);
    add("line", { x1: padL, x2: W - padR, y1: yy, y2: yy, class: i ? "grid-line" : "base-line" });
    add("text", { x: padL - 8, y: yy + 4, "text-anchor": "end", class: "tick" }, axisMoney(v));
  }
  const tip = el("div", { className: "tip multi", hidden: true });
  days.forEach((d, i) => {
    const x = padL + i * slot + (slot - bw) / 2;
    if (i % 5 === 0 || i === days.length - 1)
      add("text", { x: x + bw / 2, y: H - 6, "text-anchor": "middle", class: "tick" }, d.date.getDate() + "/" + (d.date.getMonth() + 1));
    let acc = 0;
    const present = series.filter(k => d.parts[k]);
    present.forEach((k, j) => {
      const v = d.parts[k], y1 = y(acc), y0 = y(acc + v);
      acc += v;
      const r = j === present.length - 1 ? Math.min(3, bw / 2, y1 - y0) : 0;  // round only the top of the stack
      add("path", { class: "seg", fill: k === "_other" ? "var(--muted)" : modelColor(k),
        d: `M${x},${y1} V${y0 + r} Q${x},${y0} ${x + r},${y0} H${x + bw - r} Q${x + bw},${y0} ${x + bw},${y0 + r} V${y1} Z` });
    });
    const hit = add("rect", { x: padL + i * slot, y: padT, width: slot, height: plotH, fill: "transparent" });
    hit.addEventListener("mouseenter", () => {
      tip.hidden = false;
      tip.replaceChildren(el("div", {}, el("b", { textContent: d.date.toLocaleDateString("he-IL") })),
        ...present.slice().sort((a, b) => d.parts[b] - d.parts[a]).map(k => el("div", {},
          el("span", {}, el("i", { className: "legend-dot", style: `background:${k === "_other" ? "var(--muted)" : modelColor(k)}` }), k === "_other" ? "אחר" : modelName(k)),
          el("span", { className: "num", textContent: money(d.parts[k]) }))),
        el("div", { className: "total" }, el("span", { textContent: "סה\"כ" }), el("span", { className: "num", textContent: money(totals[i]) })));
      const r = svg.getBoundingClientRect();
      tip.style.left = (x + bw / 2) * (r.width / W) + "px";
      tip.style.top = y(totals[i] || 0) * (r.height / H) + "px";
    });
    hit.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  box.replaceChildren(svg, tip);
}

function drawShare() {
  const rows = modelsData.models.filter(m => m.requests > 0);
  const req = rows.reduce((t, m) => t + m.requests, 0), cost = rows.reduce((t, m) => t + m.cost, 0);
  if (!req) { $("shareChart").replaceChildren(el("div", { className: "empty", textContent: "אין שימוש החודש" })); return; }
  const pct = (v, t) => t ? Math.round(v / t * 100) : 0;
  $("shareChart").replaceChildren(...rows.sort((a, b) => b.cost - a.cost).map(m => {
    const rp = pct(m.requests, req), cp = pct(m.cost, cost);
    const bar = (label, p, color) => el("div", { className: "share-bar" },
      el("div", { className: "track", title: `${label}: ${p}%` }, el("div", { className: "fill", style: `width:${Math.max(p, 1)}%;background:${color}` })),
      el("span", { className: "num", textContent: `${p}%` }));
    return el("div", { className: "share-row", role: "group", ariaLabel: `${m.label || m.alias}: ${rp}% מהבקשות, ${cp}% מההוצאה` },
      el("div", { className: "head" },
        el("span", {}, el("i", { className: "legend-dot", style: `background:${modelColor(m.alias)}` }), el("b", { textContent: m.label || m.alias })),
        el("span", { className: "muted small", textContent: `${money(m.requests ? m.cost / m.requests : 0)} לבקשה` })),
      bar("חלק מהבקשות", rp, "var(--axis)"),
      bar("חלק מההוצאה", cp, modelColor(m.alias)));
  }));
}

function renderModels() {
  const { models, providers } = modelsData, def = modelsData.default_model;
  renderAuto();
  $("providerStatus").replaceChildren(
    modelsData.cache_saved > 0.0001 ? el("span", { className: "badge good", title: "חלקים חוזרים בשיחות נקראו מהמטמון של הספק במחיר מוזל",
      textContent: `חיסכון מהמטמון החודש: ${money(modelsData.cache_saved)}` }) : null,
    el("span", { className: "muted small", textContent: "מפתחות ספקים:" }),
    ...Object.entries(providers).map(([p, ok]) => el("span", { className: "badge " + (ok ? "good" : "warn"),
      title: ok ? "יש מפתח בקובץ ⁦.env⁩" : "אין מפתח בקובץ ⁦.env⁩: המודלים של הספק הזה לא יעבדו",
      textContent: `${PROVIDER_FULL[p]}: ${ok ? "מחובר" : "חסר מפתח"}` })));
  $("modelsTable").replaceChildren(...models.map(m => {
    const sw = el("button", { type: "button", className: "switch", role: "switch", ariaChecked: String(m.enabled),
      ariaLabel: `${m.label || m.alias} פעיל`, onclick: () => toggleModel(m) });
    return el("tr", { className: m.enabled ? "" : "off" },
      el("td", { dataset: { label: "פעיל" } }, sw),
      el("td", {}, el("div", { className: "stack" }, el("b", { style: "white-space:nowrap", textContent: m.label || m.alias }),
        el("span", { className: "ltr muted small", title: "הכינוי · השם אצל הספק", textContent: `${m.alias} · ${m.model}` }),
        m.fallback ? el("span", { className: "muted small", textContent: `גיבוי: ${modelName(m.fallback)}` + (m.backup_answers ? ` · ענה ${m.backup_answers} פעמים החודש` : "") }) : null)),
      el("td", { dataset: { label: "ספק" } }, el("span", { className: "badge " + (providers[m.provider] ? "" : "warn"),
        title: providers[m.provider] ? "" : "אין מפתח לספק הזה", textContent: PROVIDER_FULL[m.provider] || m.provider })),
      el("td", { className: "num", dataset: { label: "מחיר למיליון טוקנים" } }, num(`$${m.price_in} / $${m.price_out}`)),
      el("td", { className: "num", dataset: { label: "שימוש החודש" } }, el("div", { className: "stack" }, num(money(m.cost)),
        el("span", { className: "muted small", textContent: `${m.requests.toLocaleString("he-IL")} בקשות` }),
        m.cache_saved > 0.0001 ? el("span", { className: "small", style: "color:var(--success)", textContent: `חסך ${money(m.cache_saved)} במטמון` }) : null)),
      el("td", { className: "num", dataset: { label: "משתמשים" } }, num(String(m.users))),
      el("td", { dataset: { label: "ברירת מחדל" } }, m.alias === def
        ? el("span", { className: "badge primary", textContent: "ברירת מחדל" })
        : m.enabled ? el("button", { className: "link small", textContent: "לקבוע", title: "המודל שנבחר אוטומטית בצ'אט ומסומן למשתמש חדש",
            onclick: run(() => api("models/default", { name: m.alias }), `${m.label || m.alias} הוא עכשיו ברירת המחדל.`) }) : null),
      el("td", {}, el("div", { className: "actions" },
        el("button", { className: "ghost", textContent: "בדיקה", title: "שולח שאלה קצרה לספק ובודק שהמפתח והשם עובדים",
          onclick: e => testModel(m, e.currentTarget) }),
        el("button", { className: "ghost", textContent: "עריכה", onclick: () => openModel(m) }),
        el("button", { className: "danger", ariaLabel: `מחיקת ${m.label || m.alias}`, title: "מחיקה", onclick: run(() => UI.confirm({ title: `למחוק את ${m.label || m.alias}?`,
          body: m.users ? `${m.users} משתמשים עדיין מורשים להשתמש בו, ולכן אי אפשר למחוק. אפשר לכבות אותו, או להסיר אותו מהמשתמשים קודם.`
            : "המודל יימחק מהרשימה. השאלות שנשאלו בו נשארות ביומן.", ok: "מחיקה", danger: true })
          .then(ok => ok ? api("models/delete", { name: m.alias }) : false), `${m.label || m.alias} נמחק.`) }, icon("trash")))));
  }));
  drawModelCharts();
  if (!models.length) $("modelsTable").append(el("tr", {}, el("td", { colSpan: 8, className: "empty", textContent: "אין מודלים. לחצו על \"מודל חדש\"." })));
}

let editingModel = null;
function openModel(m) {
  editingModel = m ? m.alias : null;
  $("modelTitle").textContent = m ? `עריכת ${m.label || m.alias}` : "מודל חדש";
  $("mAliasField").hidden = !!m;
  $("mAlias").required = !m;
  $("mAlias").value = "";
  $("mLabel").value = m ? m.label : "";
  $("mProvider").value = m ? m.provider : "anthropic";
  $("mModel").value = m ? m.model : "";
  $("mIn").value = m ? m.price_in : "";
  $("mOut").value = m ? m.price_out : "";
  $("mEnabled").checked = m ? m.enabled : true;
  $("mCached").value = m && m.price_cached != null ? m.price_cached : "";
  $("mFallback").replaceChildren(el("option", { value: "", textContent: "בלי גיבוי" }),
    ...modelsData.models.filter(x => !m || x.alias !== m.alias).map(x => el("option", { value: x.alias, textContent: x.label || x.alias })));
  $("mFallback").value = m && m.fallback ? m.fallback : "";
  $("modelError").textContent = "";
  $("modelDialog").showModal();
}
$("newModel").onclick = () => openModel(null);
$("modelForm").onsubmit = async e => {
  e.preventDefault();
  const alias = editingModel || $("mAlias").value.trim();
  try {
    await api("models", { name: alias, label: $("mLabel").value, provider: $("mProvider").value, model: $("mModel").value.trim(),
      price_in: Number($("mIn").value), price_out: Number($("mOut").value), enabled: $("mEnabled").checked,
      price_cached: $("mCached").value === "" ? null : Number($("mCached").value), fallback: $("mFallback").value });
    $("modelDialog").close();
    await load();
    UI.toast(editingModel ? `${$("mLabel").value || alias} עודכן.` : `${$("mLabel").value || alias} נוסף. אפשר ללחוץ "בדיקה" כדי לוודא שהוא עובד.`);
  } catch (err) { $("modelError").textContent = hebrew(err.message); }
};

// ---------- security ----------
let security = { events: [], counts: {}, checks: [] };
const secLabels = {
  kinds: { "suspicious-prompt": "שאלה חשודה", "dangerous-answer": "תשובה עם פקודה מסוכנת", "sensitive-data-masked": "מידע רגיש הוסתר",
    "cross-site-request": "בקשה מאתר זר נחסמה", "bad-host": "כתובת לא מוכרת נחסמה", "account-locked": "חשבון ננעל",
    "admin-denied": "סיסמת מנהל שגויה מבחוץ", "document-refused": "מסמך חשוד לא נקלט", "document-forced": "מסמך חשוד הועלה באישור" },
  found: { "prompt-injection": "ניסיון לעקוף הוראות", "script": "קוד דפדפן", "dangerous-command": "פקודה מסוכנת" },
  bad: new Set(["cross-site-request", "bad-host", "admin-denied", "account-locked", "document-forced"]),
};
function secDetail(e) {
  const d = e.detail, parts = [];
  if (d.found) parts.push(d.found.map(f => secLabels.found[f] || f).join(", "));
  if (d.count) parts.push(`${d.count} ערכים הוסתרו`);
  if (d.file) parts.push(`קובץ: ${d.file}`);
  if (d.model) parts.push(d.model);
  if (d.ip) parts.push(`כתובת: ${d.ip}`);
  if (d.host) parts.push(`שם שרת: ${d.host}`);
  if (d.origin) parts.push(`אתר מקור: ${d.origin}`);
  if (d.minutes) parts.push(`ל-${d.minutes} דקות`);
  const box = el("div", { className: "stack" }, el("span", { textContent: parts.join(" · ") }));
  if (d.excerpt) box.append(el("span", { className: "muted small", dir: "auto", textContent: "“" + d.excerpt + "”" }));
  return box;
}
function renderSecurity() {
  const c = security.counts;
  const tile = (label, ic, n, sub) => statCard(label, ic, String(n || 0), null, sub + " · 7 ימים אחרונים");
  $("secKpis").replaceChildren(
    tile("שאלות חשודות", "alert", c["suspicious-prompt"], "נרשמו ביומן"),
    tile("מידע רגיש שהוסתר", "shield", c["sensitive-data-masked"], "לפני שיצא לספק"),
    tile("בקשות שנחסמו", "shield", (c["cross-site-request"] || 0) + (c["bad-host"] || 0) + (c["admin-denied"] || 0), "מאתרים זרים או מבחוץ"),
    tile("תשובות עם פקודה מסוכנת", "alert", c["dangerous-answer"], "העובד קיבל אזהרה"));
  $("secChecks").replaceChildren(...security.checks.map(ch => el("div", { className: "alert " + (ch.ok ? "good" : "warn") },
    icon(ch.ok ? "check" : "alert"), el("span", { textContent: ch.text }))));
  const sel = $("eventFilter"), current = sel.value;
  sel.replaceChildren(el("option", { value: "", textContent: "כל האירועים" }),
    ...Object.entries(secLabels.kinds).map(([k, v]) => el("option", { value: k, textContent: v })));
  sel.value = current;
  const rows = security.events.filter(e => !sel.value || e.kind === sel.value);
  $("secEvents").replaceChildren(...rows.map(e => el("tr", {},
    el("td", {}, whenEl(e.ts)),
    el("td", {}, el("span", { className: "badge " + (secLabels.bad.has(e.kind) ? "bad" : e.kind === "sensitive-data-masked" ? "" : "warn"),
      textContent: secLabels.kinds[e.kind] || e.kind })),
    el("td", { textContent: e.name || "—", className: e.name ? "" : "muted" }),
    el("td", { className: "small" }, secDetail(e)))));
  if (!rows.length) $("secEvents").append(el("tr", {}, el("td", { colSpan: 4, className: "empty", textContent: "אין אירועים" })));
}
$("eventFilter").onchange = renderSecurity;

// ---------- knowledge sources ----------
let sourceList = [], uploadTarget = null, editingSource = null, sourceStatus = { embeddings: null, vectors: {}, pdf: false };
const EMBED_NAMES = { openai: "OpenAI", gemini: "Google" };
function renderSourceStatus() {
  const st = sourceStatus, totals = Object.values(st.vectors).reduce((t, [d, n]) => [t[0] + d, t[1] + n], [0, 0]);
  const missing = totals[1] - totals[0];
  $("sourceStatus").replaceChildren(
    el("div", { className: "stack" },
      el("b", { textContent: st.embeddings ? `חיפוש לפי משמעות: פעיל (${EMBED_NAMES[st.embeddings]})` : "חיפוש לפי משמעות: כבוי" }),
      el("span", { className: "muted small", textContent: st.embeddings
        ? `${totals[0].toLocaleString("he-IL")} מתוך ${totals[1].toLocaleString("he-IL")} קטעים מאונדקסים. שאלה על "נופש" תמצא גם מסמך שכתוב בו "חופשה".`
        : "צריך מפתח של OpenAI או Google בקובץ ‎.env. בינתיים החיפוש לפי מילים בלבד." }),
      st.pdf ? null : el("span", { className: "small", style: "color:var(--danger)", textContent: "קריאת PDF לא זמינה בשרת הזה (חסרה הספרייה pypdf)." })),
    ...(st.embeddings && missing > 0 ? [el("button", { className: "ghost", textContent: `לאנדקס ${missing.toLocaleString("he-IL")} קטעים`,
      onclick: run(async () => { for (const s of sourceList) await api("sources/reindex", { name: s.name }); }, "האינדקס עודכן.") })] : []));
}
const size = n => n >= 1e6 ? (n / 1e6).toFixed(1) + "M תווים" : n >= 1e3 ? Math.round(n / 1e3) + "K תווים" : n + " תווים";

function renderSources() {
  renderSourceStatus();
  $("sources").replaceChildren(...sourceList.map(s => {
    const total = s.docs.reduce((t, d) => t + d.chars, 0);
    const access = s.teams.includes("*") ? [el("span", { className: "badge good", textContent: "כל העובדים" })]
      : s.teams.length ? s.teams.map(t => el("span", { className: "badge", textContent: t }))
      : [el("span", { className: "badge warn", textContent: "אף אחד עוד לא קיבל גישה" })];
    const docRows = s.docs.map(d => el("tr", {},
      el("td", { className: "ltr", style: "text-align:start", textContent: d.title }),
      el("td", { className: "num muted small", textContent: size(d.chars) }),
      el("td", {}, whenEl(d.updated)),
      el("td", {}, s.kind === "upload" ? el("button", { className: "danger sm", textContent: "הסרה",
        onclick: run(() => UI.confirm({ title: `להסיר את ${d.title}?`, body: "המסמך לא יופיע יותר בחיפוש בצ'אט.", ok: "הסרה", danger: true })
          .then(ok => ok ? api("sources/docs/delete", { name: s.name, id: d.id }) : false), `${d.title} הוסר.`) }) : null)));
    return el("div", { className: "card" },
      el("header", {},
        el("div", { className: "grid", style: "gap:6px" },
          el("div", { className: "row" }, el("h2", { textContent: s.name }),
            el("span", { className: "badge", textContent: { folder: "תיקייה בשרת", upload: "קבצים שהועלו", mcp: "שרת MCP" }[s.kind] }),
            s.kind === "mcp" ? el("span", { className: "badge", textContent: s.mcp.mode === "search" ? `חיפוש חי · ${s.mcp.tool}` : "סנכרון מסמכים" }) : null),
          s.description ? el("span", { className: "muted small", textContent: s.description }) : null,
          el("div", { className: "row", style: "gap:4px" }, el("span", { className: "small muted", textContent: "גישה:" }), ...access)),
        el("div", { className: "actions" },
          s.kind === "mcp" && s.mcp.mode === "search"
            ? el("button", { className: "ghost", textContent: "בדיקת חיבור", onclick: async () => {
                try {
                  const r = await api("sources/mcp-test", { name: "test", url: s.path, source: s.name });
                  UI.toast(r.ok ? `${s.name}: מחובר${r.server ? ` ל-${r.server}` : ""}.` : `${s.name}: לא מחובר (${r.error})`, { kind: r.ok ? "good" : "bad" });
                } catch (e) { fail(e); }
              } })
          : s.kind === "upload"
            ? el("button", { textContent: "העלאת קבצים", onclick: () => { uploadTarget = s.name; $("fileInput").click(); } })
            : el("button", { textContent: "סנכרון עכשיו", onclick: run(async () => {
                const r = await api("sources/sync", { name: s.name });
                UI.toast(`סונכרנו ${r.indexed} קבצים` + (r.skipped ? `. ${r.skipped} דולגו (לא טקסט, או גדולים מ-2MB)` : "")
                  + (r.flagged.length ? `. ${r.flagged.length} לא נקלטו בגלל תוכן חשוד: ${r.flagged.join(", ")}` : "."),
                  { kind: r.flagged.length ? "bad" : "good", timeout: 10000, ...(r.flagged.length ? { action: "לפרטים", onAction: () => showTab("security") } : {}) });
              }) }),
          el("button", { className: "ghost", textContent: "עריכה", onclick: () => openSource(s) }),
          el("button", { className: "danger", textContent: "מחיקה", onclick: run(() => UI.confirm({ title: `למחוק את המקור "${s.name}"?`,
            body: "כל המסמכים שבו יימחקו מהשער ולא יופיעו בצ'אט. קבצים בתיקייה בשרת עצמו לא נמחקים.", ok: "מחיקת המקור", danger: true })
            .then(ok => ok ? api("sources/delete", { name: s.name }) : false), `המקור ${s.name} נמחק.`) }))),
      el("div", { className: "row small muted", style: "margin-bottom:8px" },
        el("span", { textContent: `${s.docs.length} מסמכים · ${size(total)}` }),
        s.kind === "folder" || s.kind === "mcp" ? el("span", { className: "ltr", textContent: s.path }) : null,
        s.kind === "folder" || (s.kind === "mcp" && s.mcp.mode === "resources")
          ? el("span", {}, s.synced ? "סנכרון אחרון: " : "עוד לא סונכרן", s.synced ? whenEl(s.synced) : null) : null),
      s.docs.length ? el("details", {}, el("summary", { className: "small", textContent: "רשימת המסמכים" }),
        el("div", { className: "table-wrap" }, el("table", {}, el("tbody", {}, ...docRows))))
        : el("div", { className: "empty", style: "padding:12px 0", textContent:
            s.kind === "mcp" && s.mcp.mode === "search" ? "המקור הזה לא שומר מסמכים: בכל שאלה השער שואל את השרת בזמן אמת, ומסנן את התשובה."
            : s.kind === "folder" || s.kind === "mcp" ? "לחצו על \"סנכרון עכשיו\" כדי לקרוא את המסמכים" : "עוד אין מסמכים. לחצו על \"העלאת קבצים\"." }));
  }));
  if (!sourceList.length) $("sources").append(el("div", { className: "card empty", textContent: "אין מקורות מידע עדיין. לחצו על \"מקור חדש\"." }));
}

$("fileInput").onchange = run(async () => {
  const files = [...$("fileInput").files];
  $("fileInput").value = "";
  if (!files.length || !uploadTarget) return;
  const tooBig = files.filter(f => f.size > 5 * 1024 * 1024);
  if (tooBig.length) throw new Error("אפשר להעלות קבצים עד 5MB. גדולים מדי: " + tooBig.map(f => f.name).join(", "));
  // PDF and Word travel as base64 and are read on the server; text files as text
  const toB64 = async f => {
    const bytes = new Uint8Array(await f.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  };
  const payload = { name: uploadTarget, files: await Promise.all(files.map(async f => /\.(pdf|docx)$/i.test(f.name)
    ? { name: f.name, b64: await toB64(f) } : { name: f.name, text: await f.text() })) };
  let r;
  try { r = await api("sources/upload", payload); }
  catch (e) {
    if (!/suspicious/.test(e.message)) throw e;
    const kinds = Object.entries(secLabels.found).filter(([k]) => e.message.includes(k)).map(([, v]) => v).join(", ");
    if (!await UI.confirm({ title: "נמצא תוכן חשוד בקובץ", ok: "להעלות בכל זאת", danger: true,
      body: `${e.message.split(":")[0].replace("suspicious content in ", "")}: ${kinds}. מסמך כזה יגיע לכל מי שמחפש במקור. ההחלטה תירשם ביומן האבטחה.` })) return false;
    r = await api("sources/upload", { ...payload, force: true });
  }
  UI.toast(`הועלו ${r.added} קבצים ל"${uploadTarget}".`);
});

function openSource(s) {
  editingSource = s ? s.name : null;
  $("sourceTitle").textContent = s ? `עריכת ${s.name}` : "מקור מידע חדש";
  $("sNameField").hidden = !!s;
  $("sName").required = !s;
  $("sName").value = "";
  $("sDesc").value = s ? s.description : "";
  document.querySelector(`[name=sKind][value=${s ? s.kind : "upload"}]`).checked = true;
  $("sPath").value = s && s.kind === "folder" ? s.path : "";
  $("sMcpUrl").value = s && s.kind === "mcp" ? s.path : "";
  $("sMcpToken").value = "";
  $("sMcpToken").placeholder = s && s.mcp && s.mcp.has_token ? "שמור. ריק = בלי שינוי" : "";
  $("sMcpInfo").textContent = "";
  document.querySelector(`[name=sMode][value=${s && s.mcp ? s.mcp.mode : "search"}]`).checked = true;
  fillTools([], s && s.mcp ? s.mcp.tool : "", s && s.mcp ? s.mcp.arg : "");
  showKindFields();
  $("sEveryone").checked = !!(s && s.teams.includes("*"));
  $("sTeams").replaceChildren(...state.teams.map(t =>
    el("label", { className: "check" }, el("input", { type: "checkbox", value: t.name, checked: !!(s && s.teams.includes(t.name)) }), t.name)));
  $("sTeams").hidden = $("sEveryone").checked;
  $("sourceError").textContent = "";
  $("sourceDialog").showModal();
}
function showKindFields() {
  const kind = document.querySelector("[name=sKind]:checked").value;
  $("sPathField").hidden = kind !== "folder";
  $("sMcpFields").hidden = kind !== "mcp";
  $("sToolFields").hidden = document.querySelector("[name=sMode]:checked").value !== "search";
}
document.querySelectorAll("[name=sKind], [name=sMode]").forEach(r => r.onchange = showKindFields);
let mcpTools = [];
function fillTools(tools, tool, arg) {
  mcpTools = tools;
  if (tool && !tools.some(t => t.name === tool)) tools = [...tools, { name: tool, args: [arg || "query"], description: "" }];
  $("sTool").replaceChildren(...tools.map(t => el("option", { value: t.name, textContent: t.name, title: t.description || "" })));
  if (tool) $("sTool").value = tool;
  const fillArgs = () => {
    const t = tools.find(x => x.name === $("sTool").value) || { args: [] };
    const args = t.args.length ? t.args : ["query"];
    $("sArg").replaceChildren(...args.map(a => el("option", { value: a, textContent: a })));
    if (arg && args.includes(arg)) $("sArg").value = arg;
    else $("sArg").value = args.find(a => /^(q|query|search|text|question)$/i.test(a)) || args[0];
  };
  $("sTool").onchange = () => { arg = null; fillArgs(); };
  fillArgs();
}
$("sMcpTest").onclick = async () => {
  const btn = $("sMcpTest");
  btn.classList.add("busy");
  $("sMcpInfo").textContent = "";
  try {
    const r = await api("sources/mcp-test", { name: "test", url: $("sMcpUrl").value.trim(), token: $("sMcpToken").value, source: editingSource || "" });
    if (!r.ok) { $("sMcpInfo").textContent = "לא הצלחנו להתחבר: " + r.error; $("sMcpInfo").className = "small error"; return; }
    $("sMcpInfo").className = "small";
    $("sMcpInfo").textContent = `מחובר${r.server ? ` ל-${r.server}` : ""}: ${r.tools.length} כלים, ${r.resources} מסמכים.`;
    fillTools(r.tools, $("sTool").value, $("sArg").value);
  } catch (e) { $("sMcpInfo").textContent = hebrew(e.message); $("sMcpInfo").className = "small error"; }
  finally { btn.classList.remove("busy"); }
};
$("sEveryone").onchange = () => $("sTeams").hidden = $("sEveryone").checked;
$("newSource").onclick = () => openSource(null);
$("sourceForm").onsubmit = async e => {
  e.preventDefault();
  const kind = document.querySelector("[name=sKind]:checked").value;
  const teams = $("sEveryone").checked ? ["*"] : [...$("sTeams").querySelectorAll("input:checked")].map(i => i.value);
  try {
    const mode = document.querySelector("[name=sMode]:checked").value;
    await api("sources", { name: editingSource || $("sName").value, description: $("sDesc").value, kind, teams,
      path: kind === "mcp" ? $("sMcpUrl").value.trim() : $("sPath").value,
      ...(kind === "mcp" ? { token: $("sMcpToken").value, mode, tool: mode === "search" ? $("sTool").value : "", arg: $("sArg").value } : {}) });
    $("sourceDialog").close();
    UI.toast(editingSource ? `המקור ${editingSource} עודכן.` : "המקור נוצר.");
    load();
  } catch (err) { $("sourceError").textContent = hebrew(err.message); }
};

$("loginForm").onsubmit = e => {
  e.preventDefault();
  pw = $("pw").value;
  try { sessionStorage.setItem("pw", pw); } catch {}
  load().catch(() => {});
};
$("refresh").onclick = () => load().catch(() => {});

load().catch(() => {});
