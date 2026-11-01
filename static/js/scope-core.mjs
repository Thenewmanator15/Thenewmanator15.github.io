// The scope's logic: pure functions, no DOM. scope-ui.mjs draws what these return.
//
// Times are decimal years (2017-09 is 2017 + 8/12). A `channels` argument is a boolean array
// indexed by channel number − 1; its length comes from data/channels.toml, never a fixed 7.
// Items are projects only: timeline entries (the BEng award, AFHEA) and parts never become items.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const STYLES = ["scope", "paper", "hc"];
const STYLE_KEY = "scope-style"; // the same key static/js/theme-boot.js reads
const MONTH = 1 / 12;
const MIN_WINDOW = 0.25; // narrowest view, in years
const MIN_SPAN = 0.02; // narrowest selection (cursor span), in years
const PICK_SLOP = 0.05; // how near a project a click still picks it, in years
const NOW_SLOP = 0.05; // "last active" this close to now reads "now"
const M_EPS = 0.05; // |M| below this counts as neither side busier
const STATS_SAMPLES = 400;

const visible = (channels, n) => channels[n - 1] === true;
const clamp = (x, lo, hi) => Math.min(Math.max(x, lo), hi);
const overlaps = (i, lo, hi) => i.start <= hi && i.end >= lo;
const clipLen = (i, lo, hi) => Math.max(0, Math.min(i.end, hi) - Math.max(i.start, lo));
const byStart = (a, b) => a.start - b.start || String(a.id).localeCompare(String(b.id));

function unionLength(intervals) {
  const xs = intervals.filter(([a, b]) => b > a).sort((p, q) => p[0] - q[0]);
  let total = 0, cur = null;
  for (const [a, b] of xs) {
    if (cur && a <= cur[1]) cur[1] = Math.max(cur[1], b);
    else { if (cur) total += cur[1] - cur[0]; cur = [a, b]; }
  }
  return cur ? total + cur[1] - cur[0] : total;
}

function sampleTimes(from, to, samples) {
  if (samples <= 1) return [from];
  return Array.from({ length: samples }, (_, i) => from + ((to - from) * i) / (samples - 1));
}

// Complementary error function (Numerical Recipes erfcc, fractional error below 1.2e-7).
function erfc(x) {
  const z = Math.abs(x), t = 1 / (1 + 0.5 * z);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
    t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 +
    t * 0.17087277)))))))));
  return x >= 0 ? r : 2 - r;
}
const phi = (x) => 0.5 * erfc(-x / Math.SQRT2); // normal CDF

// ---- Data ----

export const slugs = (channels) => channels.map((c) => c.slug);

export function toYear(ym, now) {
  if (ym === "now") return now;
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym));
  return m ? Number(m[1]) + (Number(m[2]) - 1) / 12 : NaN;
}

// `today` ("YYYY-MM", the visitor's month) keeps "now" current between builds.
export function normalise(blob, today) {
  const built = toYear(blob.now, NaN), seen = toYear(today, NaN);
  const now = Number.isFinite(seen) && seen > built ? seen : built;
  const max = Math.floor(now * 4 + 1e-9) / 4 + 0.25; // the next quarter after now
  const channels = [...blob.channels].sort((a, b) => a.n - b.n);
  const alias = new Map(channels.filter((c) => c.alias != null).map((c) => [c.n, c.alias]));
  const items = blob.items.map((r) => {
    let channel = r.channel;
    const seen = new Set();
    while (alias.has(channel) && !seen.has(channel)) { seen.add(channel); channel = alias.get(channel); }
    const start = toYear(r.start, now);
    const end = Math.max(toYear(r.end, now), start + MONTH);
    return { ...r, channel, start, end };
  });
  const earliest = Math.floor(Math.min(...items.map((i) => i.start), now));
  const min = Number.isFinite(blob.min) ? blob.min : earliest;
  return { now, min, max, channels, items };
}

// ---- Timebase and view ----

export function timebases(min, max) {
  const span = max - min;
  return [span, ...[10, 5, 1, 0.25].filter((t) => t < span)];
}

// A view can be any width (a shared link keeps its own); Zoom steps to the neighbouring timebase.
export function widthLabel(w, career) {
  if (Math.abs(w - career) < 1e-6) return "career";
  if (w >= 1) return `${Number(w.toFixed(1))} yr`;
  return `${Math.round(w * 12)} mo`;
}

export function stepWidth(bases, w, dir) {
  const wide = [...bases].sort((a, b) => b - a);
  if (dir > 0) return wide.find((b) => b < w - 1e-9) ?? wide[wide.length - 1];
  return [...wide].reverse().find((b) => b > w + 1e-9) ?? wide[0];
}

// The wheel pans by its own movement: pixels (lines count as 16 px, pages as the width) turned
// into years at the current scale. The larger of the two axes wins.
export function wheelPan(dx, dy, mode, span, widthPx) {
  if (!(widthPx > 0)) return 0;
  const d = Math.abs(dx) > Math.abs(dy) ? dx : dy;
  const px = mode === 1 ? d * 16 : mode === 2 ? d * widthPx : d;
  return (px / widthPx) * span;
}

export function defaultView(min, max) {
  return max - min <= 12 ? { from: min, to: max } : { from: max - 10, to: max };
}

export function clampStart(start, width, min, max) {
  return width >= max - min ? min : clamp(start, min, max - width);
}

export function moveEdge(span, edge, dt, min, max) {
  let [a, b] = span;
  if (edge === 0) a = clamp(a + dt, min, b - MIN_SPAN);
  else b = clamp(b + dt, a + MIN_SPAN, max);
  return [a, b];
}

export function ticks(from, to, widthPx) {
  const span = to - from;
  if (!(span > 0) || !(widthPx > 0)) return [];
  const steps = [1, 3, 12, 24, 60, 120, 240, 600]; // months; past 5 years only for very long careers
  const step = steps.find((s) => (widthPx * s) / (12 * span) >= 100 - 1e-9) ?? steps[steps.length - 1];
  const out = [];
  for (let m = Math.ceil((from * 12) / step - 1e-9) * step; m <= to * 12 + 1e-9; m += step) {
    out.push({ t: m / 12, label: m % 12 === 0 ? String(m / 12) : MONTHS[m % 12] });
  }
  return out;
}

// ---- Activity (the analogue traces) ----

export function activityAt(items, t, channels) {
  return items.filter((i) => visible(channels, i.channel) && i.start <= t && t <= i.end).length;
}

export const edgeWidth = (span) => 0.12 * clamp(span / 10, 0.05, 1.5);

export function smoothActivity(items, t, channel, sigma) {
  let sum = 0;
  for (const i of items) {
    if (i.channel === channel) sum += Math.max(0, phi((t - i.start) / sigma) - phi((t - i.end) / sigma));
  }
  return sum;
}

export function activitySeries(items, from, to, samples, channels) {
  const sigma = edgeWidth(to - from);
  const shown = [...new Set(items.map((i) => i.channel))].filter((n) => visible(channels, n));
  return sampleTimes(from, to, samples).map((t) => shown.reduce((s, n) => s + smoothActivity(items, t, n, sigma), 0));
}

export function channelSeries(items, from, to, samples, channel) {
  const sigma = edgeWidth(to - from);
  const own = items.filter((i) => i.channel === channel);
  return sampleTimes(from, to, samples).map((t) => smoothActivity(own, t, channel, sigma));
}

function peakCount(items, lo, hi) {
  // Most projects running at once in [lo, hi]; a project ending as another starts doesn't overlap it.
  let best = 0;
  for (const c of items) {
    const t = Math.max(c.start, lo);
    if (t > hi) continue;
    const n = items.filter((i) => i.start <= t && t < i.end).length;
    best = Math.max(best, n);
  }
  return best;
}

export function maxActivity(items, min, max, channels) {
  return peakCount(items.filter((i) => visible(channels, i.channel) && overlaps(i, min, max)), min, max);
}

export function maxChannelActivity(items, min, max) {
  const chans = [...new Set(items.map((i) => i.channel))];
  return Math.max(0, ...chans.map((n) => peakCount(items.filter((i) => i.channel === n && overlaps(i, min, max)), min, max)));
}

export function noiseAt(t) {
  // Fixed in t, so the noise floor travels with the trace when the view pans.
  return (Math.sin(t * 517.3) + Math.sin(t * 1311.7 + 1.7) + Math.sin(t * 2903.1 + 4.2)) / 3;
}

// ---- Lanes and overlay ----

export function laneWeights(items, lo, hi, channels) {
  return channels.map((on, k) => (on ? (items.some((i) => i.channel === k + 1 && overlaps(i, lo, hi)) ? 1 : 0) : null));
}

export function laneLayout(weights, top, bottom, thinPx = 12) {
  // Hidden channels (null) get no lane. Every other lane is at least thinPx tall ("no signal");
  // lanes with signal share what is left in proportion to their weight, so weights can animate.
  const total = bottom - top;
  const shown = weights.filter((w) => w != null);
  const sumW = shown.reduce((s, w) => s + w, 0);
  const extra = total - thinPx * shown.length;
  const even = shown.length ? total / shown.length : 0;
  let y = top;
  return weights.map((w, k) => {
    let h = 0;
    if (w != null) h = extra < 0 || sumW === 0 ? even : thinPx + (extra * w) / sumW;
    const lane = { channel: k + 1, y, h };
    y += h;
    return lane;
  });
}

export function overlayLayout(series, top, bottom, gapPx = 11, hot = null) {
  const order = [...series].sort((a, b) => b.mean - a.mean || a.channel - b.channel).map((s) => s.channel);
  if (hot != null && order.includes(hot)) { order.splice(order.indexOf(hot), 1); order.push(hot); }
  const ms = [...series].sort((a, b) => a.y0 - b.y0 || a.channel - b.channel)
    .map((s) => ({ channel: s.channel, y: clamp(s.y0, top, bottom) }));
  for (let k = 1; k < ms.length; k++) ms[k].y = Math.max(ms[k].y, ms[k - 1].y + gapPx);
  if (ms.length) ms[ms.length - 1].y = Math.min(ms[ms.length - 1].y, bottom);
  for (let k = ms.length - 2; k >= 0; k--) ms[k].y = Math.min(ms[k].y, ms[k + 1].y - gapPx);
  if (ms.length && ms[0].y < top) {
    const step = ms.length > 1 ? (bottom - top) / (ms.length - 1) : 0; // too crowded: spread evenly
    ms.forEach((m, k) => { m.y = top + k * step; });
  }
  return { order, markers: ms };
}

// ---- Digital lines ----

export function rolesBus(items, from, to, channels) {
  return items.filter((i) => i.role && visible(channels, i.channel) && overlaps(i, from, to)).sort(byStart)
    .map((i) => ({ id: i.id, label: i.bus_label || i.title, start: i.start, end: i.end }));
}

export function studySegments(study, items, now) {
  const at = now ?? Math.max(-Infinity, ...items.map((i) => i.end));
  const fromSite = (study || []).map((s) => ({ id: null, label: s.label, start: toYear(s.start, at), end: toYear(s.end, at) }));
  const fromProjects = items.filter((i) => i.study).map((i) => ({ id: i.id, label: i.bus_label || i.title, start: i.start, end: i.end }));
  return [...fromSite, ...fromProjects].sort((a, b) => a.start - b.start);
}

export function eventsIn(events, from, to) {
  return (events || []).map((e) => ({ ...e, t: toYear(e.date, NaN) }))
    .filter((e) => e.t >= from && e.t <= to).sort((a, b) => a.t - b.t);
}

export function openLevel(openSince, from, to, now) {
  if (!openSince) return null;
  const start = Math.max(toYear(openSince, now), from), end = Math.min(now, to);
  return start < end ? { start, end } : null;
}

export function busDecode(items, events, study, lo, hi) {
  const roles = items.filter((i) => i.role && overlaps(i, lo, hi)).sort(byStart)
    .map((i) => ({ label: i.bus_label || i.title, title: i.title, start: i.start, end: i.end, years: clipLen(i, lo, hi) }));
  const ev = eventsIn(events, lo, hi).map((e) => ({ title: e.title, date: e.date }));
  const studyYears = unionLength(studySegments(study, items).map((s) => [Math.max(s.start, lo), Math.min(s.end, hi)]));
  return { roles, events: ev, studyYears };
}

// ---- Math channel: M = A − B ----

export function mathSources(key) {
  if (key === "hw") return [1, 2];
  if (key === "sw") return [3, 4, 5, 6];
  const n = Number(key);
  return Number.isInteger(n) && n >= 1 ? [n] : [];
}

const side = (items, t, chans, sigma) => chans.reduce((s, n) => s + smoothActivity(items, t, n, sigma), 0);

export function mathSeries(items, from, to, samples, a, b) {
  // Computed from every channel in A and B, shown or not, like a scope's math on a hidden channel.
  const sigma = edgeWidth(to - from);
  return sampleTimes(from, to, samples).map((t) => side(items, t, a, sigma) - side(items, t, b, sigma));
}

export function mathStats(items, lo, hi, a, b, now) {
  const end = Math.min(hi, now);
  if (!(end > lo)) return { mean: 0, above: 0, below: 0, aShare: 0, bShare: 0 };
  const sigma = edgeWidth(end - lo);
  let sumA = 0, sumB = 0, sumM = 0, above = 0, below = 0;
  for (let k = 0; k < STATS_SAMPLES; k++) {
    const t = lo + ((k + 0.5) * (end - lo)) / STATS_SAMPLES;
    const A = side(items, t, a, sigma), B = side(items, t, b, sigma), M = A - B;
    sumA += A; sumB += B; sumM += M;
    if (M > M_EPS) above++;
    else if (M < -M_EPS) below++;
  }
  const total = sumA + sumB;
  const aShare = total > 0 ? Math.round((100 * sumA) / total) : 0;
  return { mean: sumM / STATS_SAMPLES, above: above / STATS_SAMPLES, below: below / STATS_SAMPLES,
           aShare, bShare: total > 0 ? 100 - aShare : 0 };
}

// ---- Finding and stepping through projects ----

export function inWindow(items, lo, hi, channels) {
  return items.filter((i) => visible(channels, i.channel) && overlaps(i, lo, hi)).sort(byStart);
}

export function pageOf(list, index, perPage) {
  const pages = Math.max(1, Math.ceil(list.length / perPage));
  const k = ((index % pages) + pages) % pages;
  return { items: list.slice(k * perPage, k * perPage + perPage), pages, index: k };
}

export function nextItem(items, currentId, mode, channels) {
  const list = items.filter((i) => visible(channels, i.channel) && (mode !== "milestone" || i.milestone)).sort(byStart);
  if (!list.length) return null;
  if (currentId == null) return list[0];
  const k = list.findIndex((i) => i.id === currentId);
  if (k >= 0) return list[(k + 1) % list.length];
  const cur = items.find((i) => i.id === currentId);
  return (cur && list.find((i) => i.start > cur.start)) || list[0];
}

export function pickAt(items, t, channels) {
  const hits = items.filter((i) => visible(channels, i.channel) && i.start - PICK_SLOP <= t && t <= i.end + PICK_SLOP);
  hits.sort((a, b) => a.end - a.start - (b.end - b.start) || a.start - b.start);
  return hits[0] ?? null;
}

export function clusterMilestones(items, from, to, widthPx, minGapPx = 16, channels) {
  const ms = items.filter((i) => i.milestone && visible(channels, i.channel) && i.start >= from && i.start <= to).sort(byStart);
  const out = [];
  let lastX = -Infinity;
  for (const i of ms) {
    const x = ((i.start - from) / (to - from)) * widthPx;
    if (out.length && x - lastX < minGapPx) out[out.length - 1].ids.push(i.id);
    else out.push({ t: i.start, ids: [i.id] });
    lastX = x;
  }
  return out;
}

// ---- Shareable state (the address bar) ----

const NUM = /^-?\d{1,4}(\.\d{1,6})?$/;
const ID = /^[a-z0-9-]{1,80}$/;
const MATH = /^(hw|sw|\d{1,3})-(hw|sw|\d{1,3})$/;
const num = (v) => (NUM.test(v) ? Number(v) : NaN);
const fmt = (x) => String(Math.round(x * 1000) / 1000);

export function encodeState(s) {
  const parts = [`show=${s.show.map(encodeURIComponent).join(",")}`, `from=${fmt(s.from)}`, `to=${fmt(s.to)}`];
  if (s.f) parts.push(`f=${encodeURIComponent(s.f)}`);
  if (s.cur) parts.push(`cur=${fmt(s.cur[0])},${fmt(s.cur[1])}`);
  if (s.m) parts.push(`m=${encodeURIComponent(s.m)}`);
  if (s.layout === "overlay") parts.push("layout=overlay");
  return parts.join("&"); // never the style: that is the visitor's own setting, kept in storage
}

// d holds the defaults; lim the limits the address bar can't widen: { min, max, slugs, channels }.
// Each key is checked on its own and falls back to its default when it doesn't pass.
export function decodeState(search, d, lim = {}) {
  const out = { ...d };
  const { min = -Infinity, max = Infinity, slugs: all = d.show, channels: nums = [] } = lim;
  const p = new Map();
  for (const kv of String(search ?? "").replace(/^[?#]/, "").split("&")) {
    const k = kv.indexOf("=");
    if (k <= 0) continue;
    try { p.set(decodeURIComponent(kv.slice(0, k)), decodeURIComponent(kv.slice(k + 1))); } catch { /* skip */ }
  }
  if (p.has("show")) {
    const want = new Set(p.get("show").split(","));
    const keep = all.filter((s) => want.has(s));
    out.show = keep.length ? keep : [...all];
  }
  if (p.has("from") || p.has("to")) {
    let a = p.has("from") ? num(p.get("from")) : d.from, b = p.has("to") ? num(p.get("to")) : d.to;
    if (!Number.isFinite(a)) a = d.from;
    if (!Number.isFinite(b)) b = d.to;
    if (a > b) [a, b] = [b, a];
    a = clamp(a, min, max); b = clamp(b, min, max);
    if (b - a < MIN_WINDOW) { a = d.from; b = d.to; }
    out.from = a; out.to = b;
  }
  if (p.has("f")) out.f = ID.test(p.get("f")) ? p.get("f") : null;
  if (p.has("cur")) {
    let [a, b] = p.get("cur").split(",").map(num);
    out.cur = null;
    if (Number.isFinite(a) && Number.isFinite(b)) {
      if (a > b) [a, b] = [b, a];
      a = clamp(a, min, max); b = clamp(b, min, max);
      if (b - a >= MIN_SPAN) out.cur = [a, b];
    }
  }
  if (p.has("m")) {
    const m = MATH.exec(p.get("m"));
    const ok = m && [m[1], m[2]].every((x) => x === "hw" || x === "sw" || nums.includes(Number(x)));
    out.m = ok ? p.get("m") : null;
  }
  if (p.has("layout")) out.layout = p.get("layout") === "overlay" ? "overlay" : "lanes";
  if (p.has("style")) out.style = STYLES.includes(p.get("style")) ? p.get("style") : null;
  return out;
}

export function readStoredStyle(storage) {
  try {
    const v = storage.getItem(STYLE_KEY);
    return STYLES.includes(v) ? v : null;
  } catch { return null; }
}

export function writeStoredStyle(storage, style) {
  try {
    if (style == null) storage.removeItem(STYLE_KEY);
    else if (STYLES.includes(style)) storage.setItem(STYLE_KEY, style);
    else return false;
    return true;
  } catch { return false; }
}

// ---- Measurements ----

const tag = (n, r) => ({ label: `CH${n} · ${r.label}`, value: r.value, channel: n });

function spanText(years) {
  return years < 1 ? `${Math.round(years * 12)} mo` : `${years.toFixed(1)} yr`;
}

export function gatedReadouts(items, lo, hi, channels, channelReadouts) {
  const inside = inWindow(items, lo, hi, channels);
  const top = new Map();
  for (const i of inside) {
    const best = top.get(i.channel);
    const better = !best || (!!i.featured !== !!best.featured ? !!i.featured : clipLen(i, lo, hi) > clipLen(best, lo, hi));
    if (better) top.set(i.channel, i);
  }
  const ranked = [...top.entries()].sort(([na, a], [nb, b]) =>
    (!!b.featured - !!a.featured) || clipLen(b, lo, hi) - clipLen(a, lo, hi) || na - nb);
  const out = [];
  for (const [n, i] of ranked) {
    const r = i.readouts?.[0] ?? channelReadouts[n]?.[0];
    if (r && out.length < 4) out.push(tag(n, r));
  }
  out.sort((a, b) => a.channel - b.channel); // shown in lane order
  const pads = [
    { label: "ΔT", value: spanText(hi - lo), channel: null },
    { label: "projects", value: String(inside.length), channel: null },
    { label: "peak", value: String(peakCount(inside, lo, hi)), channel: null },
    { label: "topics", value: String(top.size), channel: null },
  ];
  while (out.length < 4) out.push(pads.shift());
  return out;
}

function row(channel, name, list, lo, hi, now) {
  const end = Math.min(Math.max(...list.map((i) => i.end)), hi);
  const weight = new Map(), latest = new Map();
  for (const i of list) {
    if (i.text_only) continue;
    const w = 0.5 ** (Math.max(0, now - i.end) / 5); // 1 while it runs, halving every five years after
    for (const s of i.skills || []) {
      weight.set(s, (weight.get(s) || 0) + w);
      latest.set(s, Math.max(latest.get(s) ?? -Infinity, i.end));
    }
  }
  const skills = [...weight.keys()].sort((a, b) => weight.get(b) - weight.get(a) || latest.get(b) - latest.get(a)).slice(0, 3);
  const proof = list.flatMap((i) => i.proof || []);
  return {
    channel, name,
    years: unionLength(list.map((i) => [Math.max(i.start, lo), Math.min(i.end, hi)])),
    last: Math.abs(end - now) <= NOW_SLOP ? "now" : end,
    projects: list.length,
    peak: peakCount(list, lo, hi),
    skills,
    proof: { total: proof.length, open: proof.filter((x) => !x.on_request).length },
  };
}

export function measureRows(items, lo, hi, channels, focusId, now, names = []) {
  const nameOf = (n) => names[n - 1] ?? `CH${n}`;
  if (focusId != null) {
    const f = items.find((i) => i.id === focusId);
    if (!f) return [];
    const [a, b] = overlaps(f, lo, hi) ? [lo, hi] : [f.start, f.end];
    return [row(f.channel, nameOf(f.channel), [f], a, b, now)];
  }
  const rows = [];
  for (let n = 1; n <= channels.length; n++) {
    const list = items.filter((i) => i.channel === n && visible(channels, n) && overlaps(i, lo, hi));
    if (list.length) rows.push(row(n, nameOf(n), list, lo, hi, now));
  }
  return rows.sort((a, b) => b.years - a.years || a.channel - b.channel);
}

export function readoutsFor(item, channelReadouts, channels) {
  if (item) {
    const n = item.channel, seen = new Set(), list = [];
    for (const r of [...(item.readouts || []), ...(channelReadouts[n] || [])]) {
      if (seen.has(r.label) || list.length === 4) continue;
      seen.add(r.label);
      list.push({ label: r.label, value: r.value, channel: n });
    }
    if (list.length) list[0] = tag(n, list[0]);
    return { source: n, list };
  }
  const shown = channels.map((on, k) => (on ? k + 1 : 0)).filter(Boolean);
  if (!shown.length) return { source: null, list: [{ label: "all channels", value: "off", channel: null }] };
  if (shown.length === 1) {
    const n = shown[0];
    const list = (channelReadouts[n] || []).slice(0, 4).map((r) => ({ label: r.label, value: r.value, channel: n }));
    if (list.length) list[0] = tag(n, list[0]);
    return { source: n, list };
  }
  const list = shown.filter((n) => channelReadouts[n]?.length).slice(0, 4).map((n) => tag(n, channelReadouts[n][0]));
  return { source: null, list };
}

// The small labels after a project's title, in order: "role", then "in progress" for an unfinished page.
export function labels(item) {
  return [item.role ? "role" : null, item.wip ? "in progress" : null].filter(Boolean);
}
