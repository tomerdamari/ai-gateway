// Shared page pieces for the admin and chat screens: in-page confirmation dialog and short notices.
// Replaces the browser's own alert/confirm boxes, which look foreign and can't carry formatting.
const UI = (() => {
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

  return { toast, confirm, sideMenu };
})();
