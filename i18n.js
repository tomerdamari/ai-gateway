// Interface language: Hebrew (default, right to left) or English (left to right).
// The pages are written in Hebrew. In English, every visible text, placeholder, tooltip and screen-reader label is swapped
// through window.EN (exact texts) and window.EN_PATTERNS ([regex, replacement] for texts with numbers or names inside),
// plus window.EN_HTML for whole blocks of static prose,
// both filled by en-*.js. Text that has no translation stays as it is, so data such as people's names is never touched.
const I18N = (() => {
  let lang = "he";
  try { lang = localStorage.getItem("lang") === "en" ? "en" : "he"; } catch {}
  const en = lang === "en", root = document.documentElement;
  const ATTRS = ["placeholder", "aria-label", "title", "data-label", "alt"];
  const HEB = /[\u0590-\u05FF]/;
  const dict = () => window.EN || {}, patterns = () => window.EN_PATTERNS || [];

  // translate one string; leading and trailing spaces are kept
  function t(s) {
    if (!en || !s || !HEB.test(s)) return s;
    const key = s.trim().replace(/[\u2066-\u2069]/g, "");
    const d = dict();
    if (Object.prototype.hasOwnProperty.call(d, key)) return s.replace(s.trim(), d[key]);
    for (const [re, rep] of patterns()) {
      if (re.test(key)) return s.replace(s.trim(), key.replace(re, rep));
    }
    return s;
  }

  function node(n) {
    if (n.nodeType === 3) {
      const v = t(n.nodeValue);
      if (v !== n.nodeValue) n.nodeValue = v;
    } else if (n.nodeType === 1) {
      for (const a of ATTRS) {
        const v = n.getAttribute(a);
        if (v && HEB.test(v)) { const w = t(v); if (w !== v) n.setAttribute(a, w); }
      }
      if (n.tagName === "STYLE" || n.tagName === "SCRIPT") return;
      for (const c of n.childNodes) node(c);
    }
  }

  if (en) {
    root.lang = "en";
    root.dir = "ltr";
    const start = () => {
      // whole blocks of the page's own static prose (window.EN_HTML: CSS selector -> English HTML), e.g. documentation sections
      for (const [sel, html] of Object.entries(window.EN_HTML || {})) document.querySelectorAll(sel).forEach(e => { e.innerHTML = html; });
      node(document.body);
      document.title = t(document.title);
      new MutationObserver(list => {
        for (const m of list) {
          if (m.type === "characterData") node(m.target);
          else if (m.type === "attributes") node(m.target);
          else m.addedNodes.forEach(node);
        }
        const title = t(document.title);
        if (title !== document.title) document.title = title;
      }).observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    };
    if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
  }

  const label = () => document.querySelectorAll("[data-lang-switch]").forEach(b => {
    b.textContent = en ? "עברית" : "English";
    b.lang = en ? "he" : "en";
  });
  if (document.body) label(); else document.addEventListener("DOMContentLoaded", label);

  // the switch: any element with data-lang-switch becomes a button that flips the language and reloads
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-lang-switch]");
    if (!b) return;
    try { localStorage.setItem("lang", en ? "he" : "en"); } catch {}
    location.reload();
  });

  return { lang, t, locale: en ? "en-US" : "he-IL" };
})();
