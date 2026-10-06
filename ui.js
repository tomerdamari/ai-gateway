// Shared page pieces for the admin and chat screens: in-page confirmation dialog and short notices.
// Replaces the browser's own alert/confirm boxes, which look foreign and can't carry formatting.
const UI = (() => {
  const VERSION = "1.2.1";  // same as VERSION in gateway.py
  addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-version]").forEach(e => { e.textContent = "v" + VERSION; }));
  const make = (tag, props = {}, ...kids) => {
    const e = Object.assign(document.createElement(tag), props);
    e.append(...kids.filter(k => k !== null && k !== undefined && k !== false));
    return e;
  };

  function xIcon() {
    const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    for (const [x1, y1, x2, y2] of [[18, 6, 6, 18], [6, 6, 18, 18]]) {
      const l = document.createElementNS(ns, "line");
      Object.entries({ x1, y1, x2, y2 }).forEach(([k, v]) => l.setAttribute(k, v));
      svg.append(l);
    }
    return svg;
  }

  // notices: one live region so screen readers announce every message
  let region = null;
  function toast(text, { kind = "good", action, onAction, timeout = 6000 } = {}) {
    if (!region) {
      region = make("div", { className: "toasts" });
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      document.body.append(region);
    }
    const close = () => { item.classList.add("out"); setTimeout(() => item.remove(), 200); };
    const item = make("div", { className: "toast " + kind },
      make("span", { textContent: text }),
      action ? make("button", { type: "button", className: "link", textContent: action, onclick: () => { close(); onAction(); } }) : null,
      make("button", { type: "button", className: "link close", ariaLabel: "סגירת ההודעה", onclick: close }, xIcon()));
    region.append(item);
    setTimeout(close, timeout);
  }

  // confirm({ title, body, ok, danger }) -> Promise<boolean>; body may be a string or an element
  let dlg = null;
  function confirm({ title, body = "", ok = "אישור", cancel = "ביטול", danger = false }) {
    if (!dlg) {
      dlg = make("dialog", { className: "confirm" });
      document.body.append(dlg);
    }
    return new Promise(resolve => {
      const done = v => { dlg.close(); resolve(v); };
      const okBtn = make("button", { type: "button", className: danger ? "danger-solid" : "", textContent: ok, onclick: () => done(true) });
      dlg.replaceChildren(
        make("h2", { textContent: title }),
        typeof body === "string" ? make("p", { textContent: body }) : body,
        make("div", { className: "row" }, okBtn, make("button", { type: "button", className: "ghost", textContent: cancel, onclick: () => done(false) })));
      dlg.oncancel = e => { e.preventDefault(); done(false); };  // Esc
      dlg.showModal();
      okBtn.focus();
    });
  }

  // the side menu on small screens: off-canvas parts must leave the keyboard order while hidden
  function sideMenu(sidebar, toggle) {
    const small = matchMedia("(max-width: 991px)");
    // on phones the open menu covers the toggle: give it a backdrop and its own close button
    const backdrop = make("div", { className: "side-backdrop" });
    const close = make("button", { type: "button", className: "side-close", ariaLabel: "סגירת התפריט" }, xIcon());
    const shut = () => sidebar.classList.remove("open");
    backdrop.onclick = shut;
    close.onclick = shut;
    sidebar.prepend(close);
    document.body.append(backdrop);
    addEventListener("keydown", e => { if (e.key === "Escape" && small.matches) shut(); });
    const sync = () => {
      const open = small.matches ? sidebar.classList.contains("open") : !sidebar.classList.contains("collapsed");
      sidebar.inert = !open;
      backdrop.classList.toggle("show", small.matches && open);
      toggle.setAttribute("aria-expanded", String(open));
    };
    toggle.addEventListener("click", () => { sidebar.classList.toggle(small.matches ? "open" : "collapsed"); sync(); });
    small.addEventListener("change", sync);
    new MutationObserver(sync).observe(sidebar, { attributes: true, attributeFilter: ["class"] });
    sync();
  }

  // date picker in Slate's style: a field with a calendar icon opens a month panel (round days, today marked, a year
  // view and "clear"). The real <input type="date"> stays in the form, hidden, so it still holds the value (yyyy-mm-dd)
  // and code that sets or reads .value keeps working. The panel lives in the top layer (popover), so dialogs can't clip it.
  const pad = n => String(n).padStart(2, "0");
  const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parse = v => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v || ""); return m ? new Date(+m[1], m[2] - 1, +m[3]) : null; };
  const calIcon = () => {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("aria-hidden", "true"); s.classList.add("icon");
    s.innerHTML = '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M16 2v4M8 2v4M3 10h18"/></g>';
    return s;
  };
  function datePicker(input) {
    const loc = () => (window.I18N && I18N.locale) || "he-IL";
    const tr = s => (window.I18N ? I18N.t(s) : s);
    const label = make("span");
    const trigger = make("button", { type: "button", className: "date-trigger" }, calIcon(), label);
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");
    const panel = make("div", { className: "date-panel" });
    panel.popover = "manual";
    input.hidden = true;
    input.after(trigger, panel);
    let view = new Date(), years = false;

    const show = () => {
      const d = parse(input.value);
      label.textContent = d ? d.toLocaleDateString(loc()) : tr("בחירת תאריך");
      label.classList.toggle("placeholder", !d);
    };
    // code sets input.value directly (e.g. when a dialog opens): keep the field's text in step
    const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    Object.defineProperty(input, "value", { get() { return desc.get.call(this); }, set(v) { desc.set.call(this, v); show(); } });

    const place = () => {
      const r = trigger.getBoundingClientRect(), h = panel.offsetHeight || 340, w = panel.offsetWidth || 280;
      const below = r.bottom + 6 + h <= innerHeight || r.top < h;
      panel.style.top = (below ? r.bottom + 6 : r.top - h - 6) + "px";
      const rtl = getComputedStyle(trigger).direction === "rtl";
      panel.style.left = Math.max(8, Math.min(innerWidth - w - 8, rtl ? r.right - w : r.left)) + "px";
    };
    const nav = (dir, name, onclick) => {
      const b = make("button", { type: "button", className: "date-nav", ariaLabel: tr(name), onclick });
      b.innerHTML = dir === "prev" ? '<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="9 6 15 12 9 18"/></svg>'
                                   : '<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="15 6 9 12 15 18"/></svg>';
      return b;
    };
    const draw = () => {
      const sel = iso(parse(input.value) || new Date(0)), today = iso(new Date());
      if (years) {
        const first = view.getFullYear() - (view.getFullYear() % 12);
        panel.replaceChildren(
          make("div", { className: "date-head" },
            nav("prev", "שנים קודמות", () => { view.setFullYear(view.getFullYear() - 12); draw(); }),
            make("span", { className: "date-title", textContent: `${first}–${first + 11}` }),
            nav("next", "שנים הבאות", () => { view.setFullYear(view.getFullYear() + 12); draw(); })),
          make("div", { className: "date-years" }, ...Array.from({ length: 12 }, (_, i) => make("button", {
            type: "button", className: "date-year" + (first + i === view.getFullYear() ? " selected" : ""), textContent: first + i,
            onclick: () => { view.setFullYear(first + i); years = false; draw(); } }))));
        return;
      }
      const start = new Date(view.getFullYear(), view.getMonth(), 1);
      start.setDate(1 - start.getDay());  // the week starts on Sunday
      const cells = Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
      panel.replaceChildren(
        make("div", { className: "date-head" },
          nav("prev", "החודש הקודם", () => { view = new Date(view.getFullYear(), view.getMonth() - 1, 1); draw(); }),
          make("button", { type: "button", className: "date-title", ariaLabel: tr("בחירת שנה"),
            textContent: view.toLocaleDateString(loc(), { month: "long", year: "numeric" }), onclick: () => { years = true; draw(); } }),
          nav("next", "החודש הבא", () => { view = new Date(view.getFullYear(), view.getMonth() + 1, 1); draw(); })),
        make("div", { className: "date-week" }, ...Array.from({ length: 7 }, (_, i) =>
          make("span", { textContent: new Date(2026, 0, 4 + i).toLocaleDateString(loc(), { weekday: "narrow" }) }))),
        make("div", { className: "date-days" }, ...cells.map(d => {
          const k = iso(d);
          const b = make("button", { type: "button", textContent: d.getDate(),
            className: "date-day" + (d.getMonth() !== view.getMonth() ? " muted" : "") + (k === today ? " today" : "") + (k === sel ? " selected" : ""),
            onclick: () => { input.value = k; input.dispatchEvent(new Event("change", { bubbles: true })); close(); trigger.focus(); } });
          b.setAttribute("aria-label", d.toLocaleDateString(loc(), { day: "numeric", month: "long", year: "numeric" }));
          if (k === sel) b.setAttribute("aria-pressed", "true");
          return b;
        })),
        input.value ? make("button", { type: "button", className: "date-clear", textContent: tr("ניקוי"),
          onclick: () => { input.value = ""; input.dispatchEvent(new Event("change", { bubbles: true })); close(); trigger.focus(); } }) : "");
    };
    const outside = e => { if (!panel.contains(e.target) && !trigger.contains(e.target)) close(); };
    const key = e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); trigger.focus(); } };
    function open() {
      view = parse(input.value) || new Date(); years = false;
      draw(); panel.showPopover(); place();
      trigger.setAttribute("aria-expanded", "true");
      document.addEventListener("pointerdown", outside, true);
      document.addEventListener("keydown", key, true);
      addEventListener("scroll", place, true); addEventListener("resize", place);
      (panel.querySelector(".date-day.selected") || panel.querySelector(".date-day.today") || panel.querySelector(".date-day")).focus();
    }
    function close() {
      if (!panel.matches(":popover-open")) return;
      panel.hidePopover();
      trigger.setAttribute("aria-expanded", "false");
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", key, true);
      removeEventListener("scroll", place, true); removeEventListener("resize", place);
    }
    trigger.onclick = () => panel.matches(":popover-open") ? close() : open();
    show();
  }
  addEventListener("DOMContentLoaded", () => document.querySelectorAll('input[type="date"]').forEach(datePicker));

  return { toast, confirm, sideMenu, datePicker };
})();
