// The scope on the front page: draws the traces, digital lines and zoom pane, and wires the controls.
// The maths lives in scope-core.mjs. Every element is built with createElement and textContent:
// nothing from the URL or from content is ever inserted as markup.
import * as core from "./scope-core.mjs";

const SVGNS = "http://www.w3.org/2000/svg";
const PER_PAGE = 6;
const RUN_MS = 4500;
const RUN_GRACE_MS = 1500;
const STYLE_NAMES = { scope: "scope", paper: "paper", hc: "high contrast" };
const MEASURES = ["table", "key figures", "off"];
const HINT = "drag to zoom · drag the box to move through time · Shift-drag to pan";

// ---- Small builders ----

function dress(e, attrs, kids) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "text") e.textContent = String(v);
    else e.setAttribute(k, v === true ? "" : String(v));
  }
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    e.append(typeof k === "object" ? k : String(k));
  }
  return e;
}
// Replaces an element's children. Missing pieces (null, undefined, false) are skipped, so they never
// become the text "null". Every replaceChildren in this file goes through here.
export function put(e, ...kids) {
  e.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false));
  return e;
}
const el = (tag, attrs, ...kids) => dress(document.createElement(tag), attrs, kids);
const sv = (tag, attrs, ...kids) => dress(document.createElementNS(SVGNS, tag), attrs, kids);
const f1 = (x) => x.toFixed(1);
const pts = (xs, ys) => xs.map((x, i) => `${f1(x)},${f1(ys[i])}`).join(" ");
const media = (q) => typeof matchMedia === "function" && matchMedia(q).matches;

// A link from the data blob: https, a path on this site, or an anchor or file relative to `base`
// (the project's own page). Anything else (javascript:, http:, data:, //host) gives null.
export function safeHref(url, base) {
  if (typeof url !== "string" || !url || url !== url.trim() || /[\u0000-\u001f\s]/.test(url)) return null;
  if (url.startsWith("https://")) return url;
  if (url.startsWith("//")) return null;
  if (url.startsWith("/")) return url;
  if (/^[a-z][a-z0-9+.-]*:/i.test(url)) return null;
  return (typeof base === "string" && base.startsWith("/") ? base : "/") + url;
}

function years(item, now) {
  const a = String(Math.floor(item.start));
  const b = item.end >= now - 0.01 ? "now" : String(Math.floor(item.end));
  return a === b ? a : `${a} – ${b}`;
}

// ---- The scope ----

export function init(root) {
  const blobEl = root && typeof root.querySelector === "function" ? root.querySelector("#scope-data") : null;
  if (!blobEl) return;
  let blob;
  try { blob = JSON.parse(blobEl.textContent); } catch { return; }
  if (!blob || !Array.isArray(blob.items) || !Array.isArray(blob.channels)) return;
  new Scope(root, blob).start();
}

class Scope {
  constructor(root, blob) {
    this.root = root;
    this.blob = blob;
    const d = new Date();
    const n = core.normalise(blob, `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    Object.assign(this, { now: n.now, min: n.min, max: n.max, channels: n.channels, items: n.items });
    this.N = Math.max(...this.channels.map((c) => c.n));
    this.byN = new Map(this.channels.map((c) => [c.n, c]));
    this.byId = new Map(this.items.map((i) => [i.id, i]));
    this.events = blob.events || [];
    this.digital = [...(blob.digital || [])].sort((a, b) => a.order - b.order);
    this.TB = core.timebases(this.min, this.max);
    this.mcc = Math.max(1, core.maxChannelActivity(this.items, this.min, this.max));
    this.mmax = new Map();
    const view = core.defaultView(this.min, this.max);
    this.defaults = { W: view.to - view.from, S: view.from };
    this.st = {
      show: this.allOn(), dig: this.digital.map(() => true), W: view.to - view.from, S: view.from,
      layout: "lanes", hot: null, math: false, ma: "hw", mb: "sw",
      sel: null, tmp: null, cursors: false, ce: 0, meas: 0, trig: "project",
      run: false, runAt: 0, page: 0, lw: null,
      style: this.root.documentElement?.getAttribute("data-style") || null,
    };
    this.anim = null;
    this.drag = null;
  }

  allOn() {
    return Array.from({ length: this.N }, (_, k) => this.byN.has(k + 1) && !this.byN.get(k + 1).alias);
  }

  q(sel) { return this.root.querySelector(sel); }

  // ---- Start-up ----

  start() {
    const d = this.root;
    this.svg = this.q("#svg");
    this.plot = this.q("#plot");
    this.rec = this.q("#rec");
    this.rsvg = this.q("#rsvg");
    this.zoomEl = this.q("#zoom");
    this.roEl = this.q("#ro");
    this.tilesEl = this.q("#tiles");
    this.statEl = this.q("#stat");
    this.tip = this.q("#dtip");
    this.fold = this.q("#dfold");
    if (!this.svg || !this.plot || !this.tilesEl) return; // markup missing: leave the page as served
    for (const e of d.querySelectorAll("[data-scope-js]")) e.hidden = false;
    this.toastEl = this.q("#toast");
    this.buildStrip();
    this.load();
    this.wire();
    this.draw();
    setInterval(() => { if (this.st.run) this.nextFeatured(); }, RUN_MS);
    let pending = false;
    addEventListener("resize", () => {
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => { pending = false; this.draw(); });
    });
    for (const qy of ["(prefers-color-scheme: light)", "(prefers-contrast: more)", "(forced-colors: active)",
                      "(prefers-reduced-motion: reduce)", "(max-width: 820px)"]) {
      if (typeof matchMedia === "function") matchMedia(qy).addEventListener?.("change", () => this.draw());
    }
  }

  get W() { return this.st.W; }
  get E() { return this.st.S + this.W; }
  reducedMotion() { return media("(prefers-reduced-motion: reduce)"); }
  isPhone() { return media("(max-width: 820px)"); }
  effStyle() {
    if (this.st.style) return this.st.style;
    if (media("(prefers-contrast: more)") || media("(forced-colors: active)")) return "hc";
    return media("(prefers-color-scheme: light)") ? "paper" : "scope";
  }
  styleC() { return !(this.effStyle() === "hc" || this.reducedMotion()); }
  clampS() { this.st.S = core.clampStart(this.st.S, this.W, this.min, this.max); }
  slugsOn() { return this.channels.filter((c) => this.st.show[c.n - 1]).map((c) => c.slug); }
  chName(n) { return this.byN.get(n)?.name ?? `CH${n}`; }
  span() { // the measurement window: the selection, else the view
    const s = this.st.sel;
    return s && s.span ? s.span : [this.st.S, this.E];
  }

  load() {
    const st = this.st;
    const D = { show: this.slugsOn(), from: st.S, to: this.E, f: null, cur: null, m: null, layout: "lanes", style: null };
    const LIM = { min: this.min, max: this.max, slugs: this.channels.map((c) => c.slug), channels: this.channels.map((c) => c.n) };
    const s = core.decodeState(typeof location === "object" ? location.search : "", D, LIM);
    st.show = this.channels.reduce((a, c) => { a[c.n - 1] = s.show.includes(c.slug); return a; }, this.allOn().map(() => false));
    st.W = Math.min(s.to - s.from, this.max - this.min); // a shared link opens on exactly its own window
    st.S = s.from;
    this.clampS();
    st.layout = s.layout === "overlay" ? "overlay" : "lanes";
    if (s.m) { const [a, b] = s.m.split("-"); st.math = true; st.ma = a; st.mb = b; }
    if (s.cur) st.sel = { kind: "span", span: s.cur };
    if (s.f && this.byId.has(s.f)) this.focusOn(s.f);
    // A style from a link never overrides the visitor's own contrast or forced-colour settings.
    if (s.style && !media("(prefers-contrast: more)") && !media("(forced-colors: active)")) {
      st.style = s.style;
      this.root.documentElement?.setAttribute("data-style", s.style);
    }
  }

  // ---- The control strip ----

  buildStrip() {
    const strip = this.q("#strip");
    const chGroup = this.q("#ch-group");
    this.chButtons = [];
    for (const a of [...(chGroup?.querySelectorAll("a.chb") || [])]) {
      const n = Number(a.getAttribute("data-channel"));
      const b = el("button", { type: "button", class: "btn chb", "data-channel": n, "aria-pressed": "true" });
      b.addEventListener("click", () => this.toggleChannel(n));
      for (const ev of ["mouseenter", "focus"]) b.addEventListener(ev, () => this.hilite(n));
      for (const ev of ["mouseleave", "blur"]) b.addEventListener(ev, () => this.hilite(null));
      a.replaceWith(b);
      this.chButtons.push([n, b]);
    }
    const grp = (label, kicker, ...kids) => el("div", { class: "grp", role: "group", "aria-label": label },
      el("span", { class: "k", text: kicker }), ...kids);
    const btn = (text, attrs = {}) => el("button", { type: "button", class: "btn", text, ...attrs });

    this.digButtons = this.digital.map((d, k) => {
      const b = btn(`${d.id} ${d.label}`, { class: "btn chb dgb", "aria-pressed": "true", title: `Digital line ${d.id}: ${d.label}` });
      b.addEventListener("click", () => { this.st.dig[k] = !this.st.dig[k]; this.draw(); });
      return b;
    });
    this.mexpr = el("span", { class: "k", id: "mexpr" });
    this.mathBtn = btn("Math", { class: "btn chb mth", "aria-pressed": "false" });
    this.mathBtn.addEventListener("click", () => { this.st.math = !this.st.math; this.draw(); });
    const option = (k) => el("option", { value: k, text: this.srcName(k) });
    const keys = ["hw", "sw", ...this.channels.filter((c) => !c.alias).map((c) => String(c.n))];
    this.selA = el("select", { class: "msel", "aria-label": "Math source A" }, keys.map(option));
    this.selB = el("select", { class: "msel", "aria-label": "Math source B" }, keys.map(option));
    this.selA.addEventListener("change", () => { this.st.ma = this.selA.value; this.draw(); });
    this.selB.addEventListener("change", () => { this.st.mb = this.selB.value; this.draw(); });

    this.runBtn = btn("Run/Stop", { "aria-pressed": "false" });
    this.runBtn.addEventListener("click", () => {
      this.st.run = !this.st.run;
      this.st.runAt = Date.now();
      if (this.st.run) this.nextFeatured(); else this.draw();
    });
    const auto = btn("Autoset");
    auto.addEventListener("click", () => this.autoset());
    const single = btn("Single");
    single.addEventListener("click", () => this.single());
    this.trigButtons = [["project", "New project"], ["milestone", "Milestone"]].map(([k, t]) => {
      const b = btn(t, { "aria-pressed": String(k === this.st.trig), "data-trig": k });
      b.addEventListener("click", () => { this.st.trig = k; this.draw(); });
      return b;
    });
    const zout = btn("Zoom −", { title: "Zoom out" });
    zout.addEventListener("click", () => this.zoomBy(-1));
    const zin = btn("Zoom +", { title: "Zoom in" });
    zin.addEventListener("click", () => this.zoomBy(1));
    const earlier = btn("◂", { title: "Earlier (moves the zoom when one is open)", "aria-label": "Earlier (moves the zoom when one is open)" });
    earlier.addEventListener("click", () => this.step(-1));
    const later = btn("▸", { title: "Later (moves the zoom when one is open)", "aria-label": "Later (moves the zoom when one is open)" });
    later.addEventListener("click", () => this.step(1));
    this.curBtn = btn("Cursors", { "aria-pressed": "false" });
    this.curBtn.addEventListener("click", () => this.toggleCursors());
    this.measBtn = btn("Measure: table");
    this.measBtn.addEventListener("click", () => { this.st.meas = (this.st.meas + 1) % 3; this.draw(); });
    this.layBtn = btn("Layout: lanes");
    this.layBtn.addEventListener("click", () => {
      this.st.layout = this.st.layout === "lanes" ? "overlay" : "lanes";
      this.st.hot = null;
      this.draw();
    });
    this.dispBtn = btn("Display: scope");
    this.dispBtn.addEventListener("click", () => this.cycleStyle());
    const save = btn("Save");
    save.addEventListener("click", () => this.save());

    strip?.append(
      grp("Digital lines", "Digital", this.digButtons),
      el("div", { class: "grp", role: "group", "aria-label": "Math channel: a differential signal, M = A − B" },
        this.mexpr, this.mathBtn, this.selA, el("span", { "aria-hidden": "true", text: "−" }), this.selB),
      grp("Acquire", "Acquire", this.runBtn, auto, single),
      grp("Trigger, which chooses what Single steps through", "Trigger", this.trigButtons),
      grp("Time", "Time", zout, zin, earlier, later),
      grp("Menu", "Menu", this.curBtn, this.measBtn, this.layBtn, this.dispBtn, save),
    );
  }

  srcName(k) {
    if (k === "hw") return "Hardware (CH1+CH2)";
    if (k === "sw") return "Software (CH3–CH6)";
    return `CH${k} ${this.chName(Number(k))}`;
  }
  srcShort(k) { return k === "hw" ? "HW" : k === "sw" ? "SW" : `CH${k}`; }
  mExpr() { return `M = ${this.srcShort(this.st.ma)} − ${this.srcShort(this.st.mb)}`; }
  isHwSw() { return this.st.ma === "hw" && this.st.mb === "sw"; }

  // ---- Actions ----

  toggleChannel(n) {
    const st = this.st;
    st.show[n - 1] = !st.show[n - 1];
    st.page = 0;
    if (st.sel?.kind === "project" && !st.show[this.byId.get(st.sel.id).channel - 1]) st.sel = null;
    this.draw();
  }

  autoset() {
    Object.assign(this.st, { W: this.defaults.W, S: this.defaults.S, show: this.allOn(), cursors: false, sel: null, page: 0, run: false });
    this.draw();
  }

  zoomBy(d) {
    const c = this.st.S + this.W / 2;
    this.st.W = core.stepWidth(this.TB, this.st.W, d);
    this.st.S = c - this.W / 2;
    this.draw();
  }

  pan(d) { this.st.S += (d * this.W) / 10; this.draw(); }

  step(d) {
    const s = this.st.sel;
    if (!s?.span || s.kind === "event") { this.pan(d); return; }
    const [a0, b0] = s.span, w = b0 - a0;
    const a = Math.max(this.min, Math.min(this.max - w, a0 + (d * w) / 4));
    this.setSpan([a, a + w]);
    this.keepInView(a, a + w);
    this.draw();
  }

  keepInView(a, b) {
    if (a < this.st.S) this.st.S = a;
    if (b > this.E) this.st.S = b - this.W;
    this.clampS();
  }

  setSpan(span) {
    this.st.sel = { kind: "span", span };
    this.st.page = 0;
  }

  focusOn(id) {
    const p = this.byId.get(id);
    if (!p) return;
    this.st.sel = { kind: "project", id, span: [p.start, Math.max(p.end, p.start + 1 / 12)] };
    this.st.page = 0;
    if (p.start > this.E || p.end < this.st.S) { this.st.S = p.start - this.W / 2; this.clampS(); }
  }

  show(id) {
    this.openFrom(document.activeElement);
    this.st.run = false;
    this.focusOn(id);
    this.draw();
  }

  showEvent(id) {
    this.openFrom(document.activeElement);
    Object.assign(this.st, { run: false, cursors: false, sel: { kind: "event", id } });
    this.draw();
  }

  clearSel() {
    const inCard = !!this.zoomEl?.contains(document.activeElement);
    Object.assign(this.st, { sel: null, run: false, cursors: false });
    this.draw();
    if (inCard && !this.refocus(this.opener)) this.plot.focus({ preventScroll: true });
  }

  // ---- Keyboard focus: rebuilt parts keep it, a card opened from an item takes it, Clear returns it ----

  selectorFor(e) {
    if (!e?.closest) return null;
    const q = (v) => (typeof CSS !== "undefined" && CSS.escape ? CSS.escape(String(v)) : String(v));
    const pj = e.closest(".pj");
    if (pj) return `${pj.closest("#zoom") ? "#zoom" : "#tiles"} .pj[data-id="${q(pj.dataset.id)}"]`;
    if (e.closest(".more")) return "#tiles .more";
    const seg = e.closest(".dseg[data-line]");
    if (seg) return `#svg .dseg[data-line="${q(seg.dataset.line)}"][data-id="${q(seg.dataset.id)}"]`;
    const mk = e.closest(".mk");
    if (mk) return `#svg .mk[data-id="${q(mk.dataset.id)}"]`;
    if (e.closest("#zoom h3")) return "#zoom h3";
    if (e.closest("#zoom .zk button")) return "#zoom .zk button";
    if (e === this.plot) return "#plot";
    return null;
  }

  // Remember where a card was opened from. Opening it from a tile, segment or milestone moves focus into
  // the card; Single, Run and clicks on the trace leave focus where it is.
  openFrom(active) {
    const sel = this.selectorFor(active);
    this.focusCard = !!sel && sel !== "#plot";
    if (sel) this.opener = sel.startsWith("#zoom") ? "#plot" : sel;
  }

  refocus(sel) {
    const t = sel ? this.root.querySelector(sel) : null;
    if (!t || t.closest("[hidden]")) return false;
    t.focus({ preventScroll: true });
    return true;
  }

  keepFocus(container, rebuild) {
    const a = document.activeElement;
    const sel = container && a && container.contains(a) ? this.selectorFor(a) : null;
    rebuild();
    if (sel && !container.contains(document.activeElement)) this.refocus(sel);
  }

  toggleCursors() {
    const st = this.st;
    st.cursors = !st.cursors;
    if (st.cursors && !st.sel?.span) {
      st.sel = { kind: "span", span: [st.S + this.W * 0.3, st.S + this.W * 0.7] };
      st.run = false;
    }
    st.ce = 0;
    st.page = 0;
    this.draw();
  }

  moveCursor(i, dt) {
    const s = this.st.sel;
    if (!s?.span) return;
    const span = core.moveEdge(s.span, i, dt, this.min, this.max);
    this.setSpan(span);
    this.keepInView(span[i], span[i]);
    this.draw();
  }

  nextFeatured() {
    const list = this.items.filter((i) => i.featured && this.st.show[i.channel - 1]).sort((a, b) => a.start - b.start);
    if (!list.length) return;
    const cur = this.st.sel?.kind === "project" ? list.findIndex((i) => i.id === this.st.sel.id) : -1;
    this.focusOn(list[(cur + 1) % list.length].id);
    this.draw();
  }

  single() {
    const cur = this.st.sel?.kind === "project" ? this.st.sel.id : null;
    const next = core.nextItem(this.items, cur, this.st.trig, this.st.show);
    if (next) this.show(next.id);
  }

  stopRun() {
    if (!this.st.run || Date.now() - this.st.runAt < RUN_GRACE_MS) return;
    this.st.run = false;
    this.runBtn.setAttribute("aria-pressed", "false");
    this.statEl.textContent = this.statusText();
  }

  cycleStyle() {
    const order = ["scope", "paper", "hc"];
    const next = order[(order.indexOf(this.effStyle()) + 1) % order.length];
    this.st.style = next;
    this.root.documentElement?.setAttribute("data-style", next);
    let store = null;
    try { store = window.localStorage; } catch { store = null; }
    core.writeStoredStyle(store ?? { setItem() { throw new Error("no storage"); }, removeItem() {} }, next);
    this.draw();
  }

  save() {
    const st = this.st;
    const s = {
      show: this.slugsOn(), from: st.S, to: this.E,
      f: st.sel?.kind === "project" ? st.sel.id : null,
      cur: st.sel?.kind === "span" ? st.sel.span : null,
      m: st.math ? `${st.ma}-${st.mb}` : null,
      layout: st.layout,
    };
    try { history.replaceState(null, "", `?${core.encodeState(s)}`); } catch { /* ignore */ }
    const done = (m) => this.toast(m);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(location.href).then(() => done("Link to this view copied"), () => done("The link is in the address bar"));
    } else done("The link is in the address bar");
  }

  toast(text) {
    if (!this.toastEl) {
      this.toastEl = el("div", { id: "toast", role: "status" });
      this.root.body?.append(this.toastEl);
    }
    this.toastEl.textContent = text;
    this.toastEl.classList.add("on");
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => this.toastEl.classList.remove("on"), 1800);
  }

  hilite(n) {
    if (this.st.layout !== "overlay" || this.st.hot === n) return;
    this.st.hot = n;
    this.drawPlot();
  }

  // ---- Drawing ----

  draw() {
    this.clampS();
    const r = this.plot.getBoundingClientRect();
    this.G = { w: Math.max(200, r.width), h: Math.max(160, r.height) };
    this.svg.setAttribute("viewBox", `0 0 ${this.G.w} ${this.G.h}`);
    this.setLanes(core.laneWeights(this.items, this.st.S, this.E, this.st.show));
    this.drawPlot();
    this.drawRecord();
    this.drawStrip();
    this.drawBelow();
  }

  setLanes(target) {
    const st = this.st;
    const sameShape = st.lw && st.lw.length === target.length && st.lw.every((v, k) => (v == null) === (target[k] == null));
    if (!sameShape || this.reducedMotion()) { st.lw = target.slice(); this.anim = null; return; }
    const goal = target.join();
    if (this.anim) { if (this.anim.goal !== goal) this.anim = { from: st.lw.slice(), to: target, goal, t0: performance.now() }; return; }
    if (st.lw.join() === goal) return;
    this.anim = { from: st.lw.slice(), to: target, goal, t0: performance.now() };
    const tick = (t) => {
      if (!this.anim) return;
      const k = Math.min(1, (t - this.anim.t0) / 250), e = k * k * (3 - 2 * k);
      st.lw = this.anim.from.map((f, i) => (f == null || this.anim.to[i] == null ? this.anim.to[i] : f + (this.anim.to[i] - f) * e));
      this.drawPlot();
      if (k < 1) requestAnimationFrame(tick);
      else { st.lw = this.anim.to.slice(); this.anim = null; this.drawPlot(); }
    };
    requestAnimationFrame(tick);
  }

  digLines() {
    const on = this.digital.filter((d, k) => this.st.dig[k]);
    return this.isPhone() ? on.filter((d) => d.id === "D0" || d.id === "D2") : on;
  }

  // The shared drawing: the main screen and the zoom pane both use it.
  screen(from, to, w, h, weights, live) {
    const g = [];
    for (let i = 1; i < 10; i++) g.push(sv("line", { class: "gl", x1: f1((w * i) / 10), y1: 0, x2: f1((w * i) / 10), y2: h }));
    for (let j = 1; j < 6; j++) g.push(sv("line", { class: "gl", x1: 0, y1: f1((h * j) / 6), x2: w, y2: f1((h * j) / 6) }));
    const lines = this.digLines();
    const nd = lines.length, dTop = h - 22 - nd * 16, lim = nd ? dTop - 8 : h - 24;
    const mH = this.st.math ? 46 : 0, aBot = lim - (mH ? mH + 4 : 0);
    if (!this.st.show.some(Boolean)) {
      g.push(sv("text", { class: "msg", x: f1(w / 2), y: f1(aBot / 2), "text-anchor": "middle", text: "All channels are off. Switch one on, or press Autoset." }));
    } else if (!core.inWindow(this.items, from, to, this.st.show).length) {
      g.push(sv("text", { class: "msg", x: f1(w / 2), y: f1(aBot / 2), "text-anchor": "middle", text: "No projects in this window. Try Autoset." }));
    }
    g.push(this.st.layout === "overlay" ? this.overlay(from, to, w, 20, aBot) : this.lanes(from, to, w, 20, aBot, weights));
    if (mH) {
      const [lo, hi] = live ? this.span() : [from, to];
      g.push(this.mathLane(from, to, w, lim - mH, lim, live, lo, hi));
    }
    if (nd) {
      g.push(sv("line", { class: "ddiv", x1: 0, y1: dTop - 3, x2: w, y2: dTop - 3 }));
      g.push(this.digitalLines(from, to, w, dTop, lines, live));
    }
    for (const t of core.ticks(from, to, w)) {
      const x = Math.max(16, Math.min(w - 16, ((t.t - from) / (to - from)) * w));
      g.push(sv("text", { class: "lab", x: f1(x), y: h - 6, "text-anchor": "middle", text: t.label }));
    }
    return g;
  }

  tracePoints(from, to, w, n, base, amp, offset = 0) {
    const samples = Math.max(2, Math.floor(w / 1.5) + 1);
    const vals = core.channelSeries(this.items, from, to, samples, n);
    const C = this.styleC();
    const xs = [], ys = [];
    let sum = 0;
    vals.forEach((v, k) => {
      const t = from + ((to - from) * k) / (samples - 1);
      xs.push((w * k) / (samples - 1));
      ys.push(base - Math.pow(Math.max(0, v / this.mcc), 0.6) * amp + (C ? 0.8 * core.noiseAt(t + offset) : 0));
      sum += v;
    });
    return { p: pts(xs, ys), mean: sum / vals.length, y0: ys[0] };
  }

  lanes(from, to, w, top, bot, weights) {
    const g = sv("g", { class: "lanes" });
    const C = this.styleC();
    const L = core.laneLayout(weights, top, bot, 12);
    weights.forEach((wt, k) => {
      if (wt == null) return;
      const n = k + 1, lane = L[k], base = lane.y + lane.h - 4, amp = Math.max(0, lane.h - 10);
      const thin = wt < 0.5;
      const { p } = this.tracePoints(from, to, w, n, base, amp, n * 3.1);
      const lg = sv("g", { "data-channel": n });
      if (C && !thin) lg.append(sv("polyline", { class: "glow", points: p }));
      lg.append(sv("polyline", { class: thin ? "tr thin" : "tr", points: p }));
      lg.append(sv("text", { class: "lab cl", x: 4, y: f1(thin ? base - 2 : lane.y + 11), text: `${n}▸` }));
      if (thin) lg.append(sv("text", { class: "nosig", x: 22, y: f1(base - 2), text: "no signal" }));
      g.append(lg);
    });
    return g;
  }

  overlay(from, to, w, top, bot) {
    const g = sv("g", { class: "overlay" });
    const C = this.styleC(), base = bot - 4, amp = Math.max(0, bot - top - 14), hot = this.st.hot;
    const series = [], drawn = new Map();
    for (const c of this.channels) {
      if (!this.st.show[c.n - 1] || !core.inWindow(this.items, from, to, this.st.show).some((i) => i.channel === c.n)) continue;
      const t = this.tracePoints(from, to, w, c.n, base, amp, c.n * 3.1);
      drawn.set(c.n, t.p);
      series.push({ channel: c.n, mean: t.mean, y0: t.y0 });
    }
    const { order, markers } = core.overlayLayout(series, top + 8, base - 2, 11, hot);
    for (const n of order) {
      const cls = hot == null ? "ov" : n === hot ? "ov hot" : "ov dim";
      const og = sv("g", { class: cls, "data-channel": n });
      if (C) og.append(sv("polyline", { class: "glow", points: drawn.get(n) }));
      og.append(sv("polyline", { class: "tr", points: drawn.get(n) }));
      g.append(og);
    }
    for (const m of markers) g.append(sv("text", { class: "lab cl ovm", "data-channel": m.channel, x: 4, y: f1(m.y + 3), text: `${m.channel}▸` }));
    return g;
  }

  mathMax() {
    const key = `${this.st.ma}|${this.st.mb}`;
    if (!this.mmax.has(key)) {
      const s = core.mathSeries(this.items, this.min, this.max, 700, core.mathSources(this.st.ma), core.mathSources(this.st.mb));
      this.mmax.set(key, Math.max(...s.map(Math.abs)) || 1);
    }
    return this.mmax.get(key);
  }

  mathLane(from, to, w, top, bot, live, lo, hi) {
    const A = core.mathSources(this.st.ma), B = core.mathSources(this.st.mb);
    const samples = Math.max(2, Math.floor(w / 1.5) + 1);
    const vals = core.mathSeries(this.items, from, to, samples, A, B);
    const mid = (top + bot) / 2, amp = (bot - top) / 2 - 3, mm = this.mathMax(), C = this.styleC();
    const xs = [], ys = [];
    vals.forEach((v, k) => {
      const t = from + ((to - from) * k) / (samples - 1);
      xs.push((w * k) / (samples - 1));
      ys.push(mid - Math.sign(v) * Math.pow(Math.min(1, Math.abs(v) / mm), 0.6) * amp + (C ? 0.8 * core.noiseAt(t + 7.31) : 0));
    });
    const p = pts(xs, ys);
    const g = sv("g", live ? { class: "mlane", role: "img", "aria-label": this.mathWords(lo, hi) } : { class: "mlane", "aria-hidden": "true" });
    g.append(sv("line", { class: "mzero", x1: 0, y1: f1(mid), x2: w, y2: f1(mid) }));
    if (C) g.append(sv("polyline", { class: "glow", points: p }));
    g.append(sv("polyline", { class: "tr", points: p }), sv("text", { class: "lab cl", x: 4, y: f1(top + 10), text: "M▸" }));
    return g;
  }

  mathStats(lo, hi) {
    return core.mathStats(this.items, lo, hi, core.mathSources(this.st.ma), core.mathSources(this.st.mb), this.now);
  }

  mathWords(lo, hi) {
    const m = this.mathStats(lo, hi);
    const when = `${Math.floor(lo)} to ${Math.floor(Math.min(hi, this.now))}`;
    if (m.aShare + m.bShare === 0) return `Math lane, ${this.mExpr()}, ${when}: no activity on either side.`;
    if (this.isHwSw()) {
      const word = m.aShare >= 55 ? "mostly hardware" : m.aShare <= 45 ? "mostly software" : "roughly balanced";
      return `Math lane, ${this.mExpr()}, ${when}: ${word} (hardware ${m.aShare}%, software ${m.bShare}%).`;
    }
    return `Math lane, ${this.mExpr()}, ${when}: above zero ${Math.round(m.above * 100)}% of the time, below zero ${Math.round(m.below * 100)}%.`;
  }

  digitalLines(from, to, w, y0, lines, live) {
    const g = sv("g", { class: "digital" });
    const span = to - from, xs = (t) => Math.max(0, Math.min(w, ((t - from) / span) * w)), row = 16, x0 = 24;
    const seg = (line, id, full, aria, ...kids) => sv("g", live
      ? { class: "dseg", tabindex: "0", role: "button", "data-line": line, "data-id": id, "data-full": full, "aria-label": aria }
      : { class: "dseg", "aria-hidden": "true" }, sv("title", { text: full }), ...kids);
    lines.forEach((d, i) => {
      const yt = y0 + i * row + 3, yb = yt + 10, ym = yt + 5;
      g.append(sv("text", { class: "dlab", x: 4, y: yb - 1, text: d.id }));
      if (d.id === "D0") {
        let lx = x0;
        for (const r of core.rolesBus(this.items, from, to, this.st.show)) {
          const a = Math.max(xs(r.start), x0), b = xs(r.end), wd = b - a, it = this.byId.get(r.id);
          if (a > lx) g.append(sv("line", { class: "dl", x1: f1(lx), y1: ym, x2: f1(a), y2: ym }));
          const lab = wd >= r.label.length * 6.5 + 10 ? r.label : wd >= 26 ? `${r.label.slice(0, 2)}…` : "";
          const shape = wd > 8
            ? `M${f1(a)},${ym}L${f1(a + 3)},${yt}L${f1(b - 3)},${yt}L${f1(b)},${ym}L${f1(b - 3)},${yb}L${f1(a + 3)},${yb}Z`
            : `M${f1(a)},${yt}L${f1(b)},${yt}L${f1(b)},${yb}L${f1(a)},${yb}Z`;
          const full = `${r.label}: ${it.title}, ${years(it, this.now)}`;
          g.append(seg("D0", r.id, full, `Role, ${it.title}, ${years(it, this.now)}`, sv("path", { class: "dbus", d: shape }),
            lab ? sv("text", { class: "dtx", x: f1((a + b) / 2), y: yb - 2, "text-anchor": "middle", text: lab }) : null));
          lx = b;
        }
        if (lx < w) g.append(sv("line", { class: "dl", x1: f1(lx), y1: ym, x2: w, y2: ym }));
      } else if (d.id === "D1") {
        let path = `M${x0},${yb}`;
        for (const z of core.studySegments(this.blob.study, this.items, this.now)) {
          if (z.end < from || z.start > to) continue;
          const a = Math.max(xs(z.start), x0), b = xs(z.end);
          path += `L${f1(a)},${yb}L${f1(a + 1.5)},${yt}L${f1(b - 1.5)},${yt}L${f1(b)},${yb}`;
          if (b - a > 30) g.append(sv("text", { class: "dtx", x: f1(a + 5), y: yb - 1.5, text: z.label }));
        }
        g.append(sv("path", { class: "dl", d: `${path}L${w},${yb}` }));
      } else if (d.id === "D2") {
        g.append(sv("line", { class: "dl", x1: x0, y1: yb, x2: w, y2: yb }));
        for (const e of core.eventsIn(this.events, from, to)) {
          const x = Math.max(x0 + 4, xs(e.t)), full = `${e.title}, ${Math.floor(e.t)}`;
          g.append(seg("D2", e.id, full, `Event, ${full}`,
            sv("rect", { class: "hit", x: f1(x - 6), y: yt - 2, width: 12, height: 14 }),
            sv("path", { class: "dl", d: `M${f1(x - 1.5)},${yb}L${f1(x - 1.5)},${yt}L${f1(x + 1.5)},${yt}L${f1(x + 1.5)},${yb}` })));
        }
      } else if (d.id === "D3") {
        const o = core.openLevel(this.blob.openSince, from, to, this.now);
        if (!o) g.append(sv("line", { class: "dl", x1: x0, y1: yb, x2: w, y2: yb }));
        else {
          const a = Math.max(xs(o.start), x0), b = xs(o.end);
          g.append(sv("path", { class: "dl", d: `M${x0},${yb}L${f1(a)},${yb}` }),
            sv("path", { class: "dopen", d: `M${f1(a)},${yb}L${f1(a + 1.5)},${yt}L${f1(b)},${yt}L${f1(b + 1.5)},${yb}L${w},${yb}` }));
          if (b - a > 70) g.append(sv("text", { class: "dopentx", x: f1(a + 5), y: yb - 1.5, text: d.label }));
        }
      }
    });
    return g;
  }

  X(t) { return ((t - this.st.S) / this.W) * this.G.w; }
  T(x) { return this.st.S + (x / this.G.w) * this.W; }

  drawPlot() {
    if (!this.G) return;
    const { w, h } = this.G, st = this.st, E = this.E;
    const kids = this.screen(st.S, E, w, h, st.lw, true);
    const hs = st.tmp || st.sel?.span;
    if (hs) {
      const a1 = this.X(Math.max(hs[0], st.S)), a2 = this.X(Math.min(hs[1], E));
      kids.push(sv("rect", { class: "sel", x: f1(a1), y: 16, width: f1(Math.max(2, a2 - a1)), height: h - 38 }));
      if (!st.tmp) {
        kids.push(sv("line", { class: "hl", x1: f1(a1), y1: h - 22, x2: 0, y2: h }),
          sv("line", { class: "hl", x1: f1(a2), y1: h - 22, x2: w, y2: h }));
      }
    }
    for (const c of core.clusterMilestones(this.items, st.S, E, w, 16, st.show)) {
      const mx = this.X(c.t);
      const names = c.ids.map((id) => this.byId.get(id).title);
      kids.push(sv("g", { class: "mk", tabindex: "0", role: "button", "data-id": c.ids[0],
        "aria-label": `Milestone: ${names.join(", ")}` },
        sv("title", { text: names.join(", ") }),
        sv("polygon", { points: `${f1(mx - 6)},2 ${f1(mx + 6)},2 ${f1(mx)},13` }),
        c.ids.length > 1 ? sv("text", { class: "mkn", x: f1(mx + 8), y: 11, text: String(c.ids.length) }) : null));
    }
    if (st.cursors && st.sel?.span) {
      st.sel.span.forEach((c, i) => {
        if (c < st.S || c > E) return;
        const cx = this.X(c);
        kids.push(sv("line", { class: i === st.ce ? "cur on" : "cur", x1: f1(cx), y1: 0, x2: f1(cx), y2: h }),
          sv("text", { class: "lab", x: f1(cx + 4), y: 28, text: `C${i + 1} ${c.toFixed(1)}` }));
      });
    }
    this.keepFocus(this.svg, () => put(this.svg, ...kids));
  }

  drawRecord() {
    if (!this.rec || !this.rsvg) return;
    const r = this.rec.getBoundingClientRect(), w = Math.max(100, r.width), h = Math.max(10, r.height), n = 160;
    const vals = core.activitySeries(this.items, this.min, this.max, n + 1, this.st.show);
    const m = Math.max(0, ...vals);
    const p = vals.map((v, i) => `${f1((i / n) * w)},${f1(h - 2 - (m ? (v / m) * (h - 6) : 0))}`);
    const bx = ((this.st.S - this.min) / (this.max - this.min)) * w, bw = (this.W / (this.max - this.min)) * w;
    this.rsvg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    put(this.rsvg, 
      sv("path", { class: "rarea", d: `M0,${h - 2} L${p.join(" L")} L${w},${h - 2} Z` }),
      sv("rect", { class: "rbr", x: f1(bx), y: 1, width: f1(Math.max(4, bw)), height: h - 2, rx: 2 }));
    this.rec.setAttribute("aria-label", `Record bar: the whole career, ${Math.floor(this.min)} – ${Math.floor(this.now)}. `
      + `On screen: ${Math.floor(this.st.S)} – ${Math.floor(Math.min(this.E, this.now))}.`);
  }

  timebaseLabel() {
    return core.widthLabel(this.W, this.max - this.min);
  }

  statusText() {
    const st = this.st;
    return `H ${this.timebaseLabel()} · T ${st.trig === "milestone" ? "milestone" : "new project"}`
      + (st.sel?.kind === "span" ? " · M gate: zoom" : "")
      + (st.run ? " · RUN" : " · STOP")
      + (this.blob.openSince && core.toYear(this.blob.openSince, this.now) <= this.now ? " · OPEN" : "");
  }

  drawStrip() {
    const st = this.st, E = this.E;
    if (this.statEl) this.statEl.textContent = this.statusText();
    for (const [n, b] of this.chButtons) {
      const quiet = !this.items.some((i) => i.channel === n && i.start <= E && i.end >= st.S);
      b.setAttribute("aria-pressed", String(!!st.show[n - 1]));
      b.classList.toggle("quiet", quiet);
      put(b, `CH${n} ${this.chName(n)}`, quiet ? el("span", { class: "ns", text: "no signal" }) : null);
    }
    this.digButtons.forEach((b, k) => b.setAttribute("aria-pressed", String(!!st.dig[k])));
    this.mathBtn.setAttribute("aria-pressed", String(st.math));
    this.mexpr.textContent = this.mExpr();
    this.selA.value = st.ma;
    this.selB.value = st.mb;
    this.runBtn.setAttribute("aria-pressed", String(st.run));
    for (const b of this.trigButtons) b.setAttribute("aria-pressed", String(b.getAttribute("data-trig") === st.trig));
    this.curBtn.setAttribute("aria-pressed", String(st.cursors));
    this.measBtn.textContent = `Measure: ${MEASURES[st.meas]}`;
    this.layBtn.textContent = `Layout: ${st.layout}`;
    this.dispBtn.textContent = `Display: ${STYLE_NAMES[this.effStyle()]}`;
    if (this.fold) {
      const bits = [];
      if (this.isPhone()) {
        const k1 = this.digital.findIndex((d) => d.id === "D1"), k3 = this.digital.findIndex((d) => d.id === "D3");
        if (k1 >= 0 && st.dig[k1]) {
          const segs = core.studySegments(this.blob.study, this.items, this.now);
          if (segs.length) bits.push(`Study: ${segs.map((z) => `${z.label} ${Math.floor(z.start)} – ${Math.floor(z.end)}`).join(", ")}`);
        }
        if (k3 >= 0 && st.dig[k3] && this.blob.openSince) bits.push(`Open to roles since ${this.blob.openSince.slice(0, 4)}`);
      }
      this.fold.textContent = bits.join(" · ");
      this.fold.hidden = !bits.length;
    }
  }

  // ---- Below the trace: measurements, tiles, zoom pane, All projects ----

  drawBelow() {
    const st = this.st;
    const [lo, hi] = this.span();
    const inw = core.inWindow(this.items, lo, hi, st.show);
    this.drawMeasure(lo, hi, inw);
    const open = !!st.sel;
    this.tilesEl.hidden = open;
    this.drawTiles(inw);
    this.drawZoom(inw);
    this.filterList();
  }

  item(id) { return this.byId.get(id); }

  // "role" and "in progress" after a title (core.labels decides which).
  labelEls(i) { return core.labels(i).map((t) => [" ", el("span", { class: t === "role" ? "rl" : "rl wip", text: t })]); }

  pj(i) {
    const b = el("button", { type: "button", class: "pj", "data-channel": i.channel, "data-id": i.id },
      el("span", { class: "dot", "aria-hidden": "true" }),
      el("span", { class: "tag", title: `CH${i.channel} ${this.chName(i.channel)}`, text: `CH${i.channel}` }),
      el("span", { class: "ti" }, i.title, this.labelEls(i)),
      el("span", { class: "dt", text: years(i, this.now) }));
    b.addEventListener("click", () => this.show(i.id));
    return b;
  }

  drawTiles(inw) {
    const st = this.st;
    const page = core.pageOf(inw, st.page, PER_PAGE);
    st.page = page.index;
    const kids = page.items.map((i) => this.pj(i));
    if (page.pages > 1) {
      const left = inw.length - (page.index + 1) * PER_PAGE;
      const more = el("button", { type: "button", class: "btn more", title: "Next page of projects",
        "aria-label": left > 0 ? `+${left} ▸ next page of projects` : "↺ first page of projects", text: left > 0 ? `+${left} ▸` : "↺" });
      more.addEventListener("click", () => { st.page += 1; this.draw(); });
      kids.push(more);
    }
    if (!inw.length) {
      kids.push(el("p", { class: "empty", text: st.show.some(Boolean)
        ? "No projects in this window. Try Autoset." : "All channels are off. Switch one on, or press Autoset." }));
    }
    this.keepFocus(this.tilesEl, () => put(this.tilesEl, ...kids));
  }

  clearButton() {
    const b = el("button", { type: "button", class: "btn", text: "Clear ✕" });
    b.addEventListener("click", () => this.clearSel());
    return b;
  }

  proofList(list, base) {
    if (!list?.length) return null;
    return el("div", { class: "proof", "aria-label": "Proof" }, list.map((q) => {
      const href = safeHref(q.url, base);
      if (!href) return el("span", { class: "ptag", text: q.label });
      const bits = [el("a", { class: "plink", href, text: q.label })];
      const arch = safeHref(q.archive, base);
      if (arch) bits.push(el("a", { class: "plink", href: arch, text: "(archived copy)" }));
      return bits;
    }));
  }

  // The pane is aria-live, so it is rebuilt only when what it shows changes: panning with a card open
  // doesn't re-announce it.
  drawZoom(inw) {
    const st = this.st, z = this.zoomEl;
    if (!z) return;
    if (!st.sel) { z.hidden = true; put(z); this.zoomKey = null; return; }
    const key = JSON.stringify([st.sel, st.sel.kind === "span"
      ? [st.show, st.dig, st.math, st.ma, st.mb, st.layout, this.effStyle(), this.G.w, this.G.h, inw.map((i) => i.id)] : null]);
    const same = key === this.zoomKey && !z.hidden;
    z.hidden = false;
    if (!same) {
      this.zoomKey = key;
      this.keepFocus(z, () => this.buildZoom(inw));
    }
    if (this.focusCard) {
      this.focusCard = false;
      z.querySelector("h3")?.focus();
    }
  }

  buildZoom(inw) {
    const st = this.st, z = this.zoomEl;
    if (st.sel.kind === "event") {
      const e = this.events.find((x) => x.id === st.sel.id);
      if (!e) { st.sel = null; z.hidden = true; return; }
      z.className = "zoom nophoto";
      put(z, el("div", {},
        el("p", { class: "k zk" }, el("span", { class: "dot dg", "aria-hidden": "true" }), "D2 · Event", this.clearButton()),
        el("h3", { tabindex: "-1" }, e.title, " ", el("span", { class: "rl", text: "timeline" })),
        el("p", { class: "zd", text: e.date.slice(0, 4) }),
        el("p", { class: "story", text: e.summary || "" }),
        this.proofList(e.proof, "/")));
      return;
    }
    if (st.sel.kind === "span") {
      z.className = "zoom span";
      const [a, b] = st.sel.span;
      const zw = Math.max(200, Math.round(this.G.w - 28)), zh = Math.round(this.G.h);
      const wave = sv("svg", { class: "wave", viewBox: `0 0 ${zw} ${zh}`, preserveAspectRatio: "none", "aria-hidden": "true", height: zh },
        this.screen(a, b, zw, zh, core.laneWeights(this.items, a, b, st.show), false));
      const cards = inw.slice(0, PER_PAGE).map((i) => this.pj(i));
      put(z, 
        el("p", { class: "k zk", text: `Zoom · ${a.toFixed(1)} – ${b.toFixed(1)} · ΔT ${(b - a).toFixed(1)} yr · ${inw.length} project${inw.length === 1 ? "" : "s"}` }, this.clearButton()),
        wave,
        el("div", { class: "pjs" }, cards.length ? cards : el("p", { class: "empty", text: "No projects in this stretch." })),
        inw.length > PER_PAGE ? el("p", { class: "empty more-note", text: `+${inw.length - PER_PAGE} more in the All projects list` }) : null);
      return;
    }
    const p = this.item(st.sel.id);
    const photo = p.thumb && !p.text_only;
    z.className = photo ? "zoom" : "zoom nophoto";
    const href = safeHref(p.url, "/");
    const parts = p.parts?.length
      ? el("p", { class: "parts" }, el("span", { class: "k", text: "Parts:" }), " ",
          p.parts.map((q, k) => [k ? " · " : "", el("a", { class: "plink", href: safeHref(q.url, "/") || "/", text: q.title }), this.labelEls(q)]))
      : null;
    put(z, 
      photo ? el("img", { class: "photo", src: p.thumb, alt: p.thumb_alt || "", loading: "lazy" }) : null,
      el("div", {},
        el("p", { class: "k zk", "data-channel": p.channel },
          el("span", { class: "dot", "aria-hidden": "true" }), `Zoom · CH${p.channel} ${this.chName(p.channel)}`, this.clearButton()),
        el("h3", { tabindex: "-1" }, href ? el("a", { href, text: p.title }) : p.title, this.labelEls(p)),
        el("p", { class: "zd", text: years(p, this.now) }),
        el("p", { class: "story", text: p.summary || "" }),
        parts,
        this.proofList(p.proof, p.url),
        href ? el("p", { class: "zact" }, el("a", { class: "btn", href, text: "Open project ▸" })) : null));
  }

  drawMeasure(lo, hi, inw) {
    const st = this.st, ro = this.roEl;
    if (!ro) return;
    ro.hidden = st.meas === 2;
    if (st.meas === 2) { put(ro); return; }
    const sel = st.sel, kids = [];
    if (st.meas === 0) kids.push(...this.table(lo, hi, inw));
    else kids.push(this.figures(lo, hi));
    if (sel?.span) kids.push(this.decode(lo, hi));
    put(ro, ...kids);
  }

  caption(lo, hi, inw) {
    const st = this.st, n = inw.length, stats = (a, b) => ` · ΔT ${(b - a).toFixed(1)} yr · ${n} project${n === 1 ? "" : "s"}`;
    if (st.sel?.kind === "project") return "Measure · selected project";
    if (st.sel?.kind === "span") return `Measure · gate: zoom ${lo.toFixed(1)} – ${hi.toFixed(1)}${stats(lo, hi)}`;
    const b = Math.min(hi, this.now);
    return `Measure · ${Math.floor(lo)} – ${Math.floor(b)}${stats(lo, b)}`;
  }

  table(lo, hi, inw) {
    const st = this.st, cap = this.caption(lo, hi, inw);
    const focus = st.sel?.kind === "project" ? st.sel.id : null;
    const rows = core.measureRows(this.items, lo, hi, st.show, focus, this.now, this.channels.reduce((a, c) => { a[c.n - 1] = c.name; return a; }, []));
    const head = [["Source"], ["Experience", "Time on this topic in the range, overlaps merged"], ["Last active", "Most recent activity"],
      ["Projects"], ["Peak", "Most projects at once"], ["Top skills", "Weighted towards recent work"],
      ["Proof", "Items a reader can check, with the number that are open"]];
    const body = rows.map((r) => el("tr", { "data-channel": r.channel },
      el("td", { text: focus ? this.item(focus).title : `CH${r.channel} ${r.name}` }),
      el("td", { text: `${r.years.toFixed(1)} yr` }),
      el("td", { text: r.last === "now" ? "now" : String(Math.floor(r.last)) }),
      el("td", { text: String(r.projects) }),
      el("td", { text: String(r.peak) }),
      el("td", { class: "sk", text: r.skills.length ? r.skills.join(", ") : "–" }),
      el("td", { text: r.proof.total ? `${r.proof.total} (${r.proof.open} open)` : "–" })));
    if (st.math) {
      const m = this.mathStats(lo, hi);
      const txt = `mean ${m.mean >= 0 ? "+" : ""}${m.mean.toFixed(2)} · M > 0: ${Math.round(m.above * 100)}% · M < 0: ${Math.round(m.below * 100)}%`
        + (this.isHwSw() && m.aShare + m.bShare ? ` · hardware ${m.aShare}% · software ${m.bShare}%` : "");
      body.push(el("tr", { class: "mrow" }, el("td", { text: this.mExpr() }), el("td", { colspan: 6, text: txt })));
    }
    if (!body.length) body.push(el("tr", {}, el("td", { colspan: 7, text: "Nothing to measure here." })));
    return [
      el("p", { class: "k mcap", "aria-hidden": "true", text: cap }),
      el("div", { class: "mtw" }, el("table", { class: "mt" },
        el("caption", { class: "sr", text: cap }),
        el("thead", {}, el("tr", {}, head.map(([t, title]) => el("th", { scope: "col", title, text: t })))),
        el("tbody", {}, body))),
    ];
  }

  figures(lo, hi) {
    const st = this.st, CH = this.blob.channelReadouts || {};
    let list;
    if (st.sel?.kind === "span") list = core.gatedReadouts(this.items, lo, hi, st.show, CH);
    else list = core.readoutsFor(st.sel?.kind === "project" ? this.item(st.sel.id) : null, CH, st.show).list;
    return el("div", { class: "rog" }, list.map((r) =>
      el("div", { class: "ro", "data-channel": r.channel ?? null }, el("span", { text: r.label }), " ", r.value)));
  }

  decode(lo, hi) {
    const d = core.busDecode(this.items, this.events, this.blob.study, lo, hi);
    const rows = [
      ...d.roles.map((r) => ["D0 role", `${r.label} · ${r.title}`, `${Math.floor(r.start)} – ${r.end >= this.now - 0.01 ? "now" : Math.floor(r.end)}`, `${r.years.toFixed(1)} yr`]),
      ...d.events.map((e) => ["D2 event", e.title, e.date.slice(0, 4), ""]),
      ...(d.studyYears > 0 ? [["D1 study", "in range", "", `${d.studyYears.toFixed(1)} yr`]] : []),
    ];
    const cap = `Bus decode · ${lo.toFixed(1)} – ${hi.toFixed(1)}`;
    return el("div", { class: "decode" },
      el("p", { class: "k mcap", "aria-hidden": "true", text: cap }),
      el("div", { class: "mtw" }, el("table", { class: "mt dig" }, el("caption", { class: "sr", text: cap }),
        el("tbody", {}, rows.length ? rows.map((r) => el("tr", {}, r.map((c) => el("td", { text: c }))))
          : el("tr", {}, el("td", { text: "Nothing on the digital lines here." }))))));
  }

  filterList() {
    for (const li of this.root.querySelectorAll(".all li.row[data-channel]")) {
      li.hidden = !this.st.show[Number(li.getAttribute("data-channel")) - 1];
    }
    for (const ul of this.root.querySelectorAll(".all ul.rows")) {
      const any = [...ul.children].some((li) => !li.hidden);
      ul.hidden = !any;
      const h = ul.previousElementSibling;
      if (h?.classList.contains("year")) h.hidden = !any;
    }
  }

  // ---- Pointer and keyboard ----

  wire() {
    const plot = this.plot, svg = this.svg;
    this.zoomEl?.addEventListener("mouseenter", () => this.stopRun());
    this.zoomEl?.addEventListener("focusin", () => this.stopRun());

    const segOf = (e) => e.target.closest?.(".dseg[data-line]");
    const act = (g) => (g.getAttribute("data-line") === "D0" ? this.show(g.getAttribute("data-id")) : this.showEvent(g.getAttribute("data-id")));
    const tipOn = (g) => {
      if (!this.tip) return;
      const r = g.getBoundingClientRect(), pr = plot.getBoundingClientRect();
      this.tip.textContent = g.getAttribute("data-full");
      this.tip.style.left = `${r.left + r.width / 2 - pr.left}px`;
      this.tip.style.top = `${r.top - pr.top - 2}px`;
      this.tip.hidden = false;
    };
    const tipOff = () => { if (this.tip) this.tip.hidden = true; };
    svg.addEventListener("click", (e) => {
      const m = e.target.closest?.(".mk");
      if (m) { this.show(m.getAttribute("data-id")); return; }
      const g = segOf(e);
      if (g) act(g);
    });
    svg.addEventListener("keydown", (e) => {
      const m = e.target.closest?.(".mk");
      if (m && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); e.stopPropagation(); this.show(m.getAttribute("data-id")); return; }
      const g = segOf(e);
      if (!g) return;
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault(); e.stopPropagation();
        const L = [...svg.querySelectorAll(`.dseg[data-line="${g.getAttribute("data-line")}"]`)];
        L[L.indexOf(g) + (e.key === "ArrowRight" ? 1 : -1)]?.focus();
      } else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); act(g); }
    });
    svg.addEventListener("focusin", (e) => { const g = segOf(e); if (g) tipOn(g); });
    svg.addEventListener("focusout", tipOff);
    svg.addEventListener("mouseover", (e) => {
      const g = segOf(e);
      if (g) tipOn(g); else tipOff();
      const o = e.target.closest?.(".ov,.ovm");
      if (o) this.hilite(Number(o.getAttribute("data-channel")));
    });
    svg.addEventListener("mouseleave", () => { tipOff(); this.hilite(null); });

    // Record bar: a click moves the view there; dragging the bracket slides it.
    let rdrag = null;
    const recT = (e) => { const r = this.rec.getBoundingClientRect(); return this.min + ((e.clientX - r.left) / r.width) * (this.max - this.min); };
    this.rec?.addEventListener("pointerdown", (e) => {
      const t = recT(e);
      rdrag = { off: t >= this.st.S && t <= this.E ? t - this.st.S : this.W / 2 };
      this.st.S = t - rdrag.off;
      this.rec.setPointerCapture?.(e.pointerId);
      this.draw();
    });
    this.rec?.addEventListener("pointermove", (e) => { if (rdrag) { this.st.S = recT(e) - rdrag.off; this.draw(); } });
    for (const ev of ["pointerup", "pointercancel"]) this.rec?.addEventListener(ev, () => { rdrag = null; });

    // The trace: drag selects, Shift-drag pans, a click picks. Touch: swipe pans; press-and-hold then drag selects.
    const rx = (e) => e.clientX - plot.getBoundingClientRect().left;
    plot.addEventListener("pointerdown", (e) => {
      if (e.target.closest?.(".mk,.dseg")) return;
      const st = this.st, x = rx(e);
      if (e.pointerType === "touch") {
        const d = { k: "touch", mode: null, x0: e.clientX, rx0: x, t0: this.T(x), S0: st.S };
        d.timer = setTimeout(() => { if (this.drag === d && !d.mode) { d.mode = "sel"; st.tmp = [d.t0, d.t0]; this.drawPlot(); } }, 450);
        this.drag = d;
        plot.setPointerCapture?.(e.pointerId);
        return;
      }
      let d = null;
      const span = st.sel?.span;
      if (st.cursors && span) {
        if (Math.abs(x - this.X(span[0])) < 10) d = { k: "edge", i: 0 };
        else if (Math.abs(x - this.X(span[1])) < 10) d = { k: "edge", i: 1 };
        if (d) st.ce = d.i;
      }
      if (!d && span && st.sel.kind !== "event" && !e.shiftKey && x >= this.X(span[0]) - 4 && x <= this.X(span[1]) + 4) {
        d = { k: "move", t0: this.T(x), z: span.slice(), x0: x };
      }
      if (!d) d = e.shiftKey ? { k: "pan", x0: e.clientX, S0: st.S } : { k: "sel", t0: this.T(x), x0: x };
      this.drag = d;
      plot.setPointerCapture?.(e.pointerId);
    });
    plot.addEventListener("pointermove", (e) => {
      const d = this.drag, st = this.st;
      if (!d) return;
      const x = rx(e);
      if (d.k === "touch") {
        const dx = e.clientX - d.x0;
        if (!d.mode && Math.abs(dx) > 8) { clearTimeout(d.timer); d.mode = "pan"; }
        if (d.mode === "pan") { st.S = d.S0 - (dx / this.G.w) * this.W; this.draw(); }
        else if (d.mode === "sel") { const t = this.T(x); st.tmp = [Math.min(d.t0, t), Math.max(d.t0, t)]; this.draw(); }
        return;
      }
      if (d.k === "pan") st.S = d.S0 - ((e.clientX - d.x0) / this.G.w) * this.W;
      else if (d.k === "sel") { const t = this.T(x); st.tmp = [Math.min(d.t0, t), Math.max(d.t0, t)]; }
      else if (d.k === "move") {
        if (Math.abs(x - d.x0) < 3 && !d.moved) return;
        d.moved = true;
        const wd = d.z[1] - d.z[0], a = Math.max(this.min, Math.min(this.max - wd, d.z[0] + this.T(x) - d.t0));
        this.setSpan([a, a + wd]);
      } else if (d.k === "edge") {
        const span = st.sel.span;
        this.setSpan(core.moveEdge(span, d.i, this.T(x) - span[d.i], this.min, this.max));
      }
      this.draw();
    });
    plot.addEventListener("pointerup", (e) => {
      const d = this.drag, st = this.st;
      if (!d) return;
      this.drag = null;
      const x = rx(e);
      const commit = (a, b) => {
        st.tmp = null;
        st.sel = { kind: "span", span: [Math.max(this.min, Math.min(a, b)), Math.min(this.max, Math.max(a, b))] };
        st.run = false; st.page = 0;
        this.draw();
      };
      const pick = (t) => { const p = core.pickAt(this.items, t, st.show); if (p) this.show(p.id); };
      if (d.k === "touch") {
        clearTimeout(d.timer);
        if (d.mode === "sel") { if (Math.abs(x - d.rx0) >= 6) commit(d.t0, this.T(x)); else { st.tmp = null; this.draw(); } }
        else if (!d.mode) pick(this.T(x));
        return;
      }
      if (d.k === "sel") {
        st.tmp = null;
        if (Math.abs(x - d.x0) < 6) { this.drawPlot(); pick(this.T(x)); } else commit(d.t0, this.T(x));
      } else if (d.k === "move" && !d.moved) pick(this.T(x));
    });
    plot.addEventListener("pointercancel", () => {
      if (this.drag?.timer) clearTimeout(this.drag.timer);
      this.drag = null;
      this.st.tmp = null;
      this.drawPlot();
    });
    // The wheel pans by how far it moved; Ctrl+wheel zooms one timebase per 50 px of movement.
    let zoomAcc = 0;
    plot.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (e.ctrlKey) {
        zoomAcc += e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
        if (Math.abs(zoomAcc) >= 50) { this.zoomBy(zoomAcc > 0 ? -1 : 1); zoomAcc = 0; }
        return;
      }
      this.st.S += core.wheelPan(e.deltaX, e.deltaY, e.deltaMode, this.W, this.G?.w ?? 0);
      this.draw();
    }, { passive: false });
    plot.addEventListener("keydown", (e) => {
      if (e.target !== plot) return; // keys on a milestone or digital segment are handled above
      const st = this.st;
      if (st.cursors && st.sel?.span) {
        if (e.key === "[" || e.key === "]") { e.preventDefault(); st.ce = e.key === "[" ? 0 : 1; this.draw(); return; }
        if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
          e.preventDefault();
          this.moveCursor(st.ce, (e.key === "ArrowLeft" ? -1 : 1) * (e.shiftKey ? 0.1 : 0.01) * this.W);
          return;
        }
      }
      const k = { ArrowLeft: () => this.step(-1), ArrowRight: () => this.step(1), ArrowUp: () => this.zoomBy(1),
        ArrowDown: () => this.zoomBy(-1), Escape: () => this.clearSel() }[e.key];
      if (k) { e.preventDefault(); k(); }
    });
    addEventListener("keydown", (e) => { if (e.key === "Escape" && this.st.sel && e.target !== plot) this.clearSel(); });
  }
}
