import { test } from "node:test";
import assert from "node:assert/strict";
import {
  slugs, toYear, normalise, timebases, defaultView, activityAt, edgeWidth, smoothActivity, activitySeries,
  channelSeries, maxChannelActivity, noiseAt, laneWeights, laneLayout, rolesBus, studySegments, eventsIn,
  openLevel, overlayLayout, mathSources, mathSeries, mathStats, busDecode, maxActivity, inWindow, pageOf,
  nextItem, clampStart, moveEdge, ticks, clusterMilestones, encodeState, decodeState, readStoredStyle,
  writeStoredStyle, gatedReadouts, measureRows, pickAt, readoutsFor, labels,
} from "../../static/js/scope-core.mjs";

// The fixture: the seven channels as in data/channels.toml, and three projects.
const CHANNELS = [
  [1, "Instruments", "instruments"],
  [2, "RF, wireless and embedded", "rf-wireless-embedded"],
  [3, "Measurement data and signal processing", "measurement-data"],
  [4, "Performance and graphics", "performance-graphics"],
  [5, "Medical imaging", "medical-imaging"],
  [6, "Open standards and accessibility", "open-standards-accessibility"],
  [7, "Teaching and mentoring", "teaching-mentoring"],
].map(([n, name, slug]) => ({ n, name, slug, colour: `--c${n}`, archived: false, alias: null }));

const raw = (o) => ({
  title: o.id, url: `/${o.id}/`, featured: false, milestone: false, role: false, bus_label: null, study: false,
  text_only: false, summary: "", thumb: null, thumb_alt: null, skills: [], readouts: [], proof: [], parts: [], ...o,
});

const blob = {
  now: "2026-10", min: 2013, channels: CHANNELS, channelReadouts: {}, digital: [],
  study: [{ label: "BEng", start: "2013-09", end: "2017-07" }],
  openSince: "2026-06",
  events: [
    { id: "beng-award", title: "BEng", date: "2017-07", summary: "", proof: [] },
    { id: "afhea", title: "AFHEA", date: "2024-01", summary: "", proof: [] },
  ],
  items: [
    raw({ id: "phd", title: "PhD", channel: 1, start: "2017-09", end: "2024-03", featured: true, milestone: true,
          study: true, parts: [{ title: "Part one", url: "/phd/one/" }, { title: "Part two", url: "/phd/two/" }] }),
    raw({ id: "mbda", title: "MBDA", channel: 2, start: "2026-01", end: "now", role: true, bus_label: "MBDA",
          milestone: true, text_only: true }),
    raw({ id: "sniffers", title: "Sniffers", channel: 2, start: "2026-03", end: "now", featured: true, milestone: true }),
  ],
};

const { now, min, max, channels, items } = normalise(blob);
const ALL = Array(7).fill(true), NONE = Array(7).fill(false);
const only = (...ns) => ALL.map((_, i) => ns.includes(i + 1));
const SLUGS = slugs(channels);
const V = defaultView(min, max);
const D = { show: slugs(channels), from: V.from, to: V.to, f: null, cur: null, style: null };
const LIM = { min, max, slugs: SLUGS, channels: channels.map((c) => c.n) };
const R4 = (p) => [0, 1, 2, 3].map((i) => ({ label: p + i, value: String(i) }));
const CH = { 1: R4("a"), 2: R4("b"), 7: R4("g") };
const withFigures = (xs) => xs.map((i) => ({ ...i, readouts: [{ label: i.id, value: "1" }] }));
const withSkills = (xs) => xs.map((i) => ({ ...i, skills: [i.id + "-skill"] }));
const close = (a, b, eps = 1e-9) => Math.abs(a - b) < eps;

// The brief's tests.

test("toYear", () => { assert.equal(toYear("2017-09", 2026.75), 2017 + 8 / 12); assert.equal(toYear("now", 2026.75), 2026.75); });

test("activity counts overlap", () => { assert.equal(activityAt(items, 2017.7, ALL), 1); assert.equal(activityAt(items, 2026.5, ALL), 2); });

test("activity with no visible channels is all zeros", () => {
  const s = activitySeries(items, 2013, 2027, 50, NONE);
  assert.ok(s.every((v) => v === 0)); assert.equal(maxActivity(items, 2013, 2027, NONE), 0);
});

test("inWindow respects channels", () =>
  assert.deepEqual(inWindow(items, 2016, 2018, [1, 0, 0, 0, 0, 0, 0].map(Boolean)).map((i) => i.id), ["phd"]));

test("channel series are continuous (style C and A)", () => {
  const s = channelSeries(items, 2013, 2027, 14000, 1); // one sample per 0.001 yr
  assert.ok(s.every((v, i) => i === 0 || Math.abs(v - s[i - 1]) < 0.05)); assert.ok(s.every((v) => v >= 0));
});

test("lanes follow the view", () => {
  assert.deepEqual(laneWeights(items, 2017, 2022, ALL), [1, 0, 0, 0, 0, 0, 0]); // only CH1 has signal
  const L = laneLayout([1, 0, 0, 0, 0, 0, 0], 0, 200);
  assert.equal(L[1].h, 12); assert.equal(L[0].h, 200 - 6 * 12);
});

test("digital lines decode the selection", () => {
  const d = busDecode(items, blob.events, blob.study, 2023, 2027);
  assert.deepEqual(d.roles.map((r) => r.label), ["MBDA"]);
  assert.deepEqual(d.events.map((e) => e.date), ["2024-01"]);
  assert.ok(Math.abs(d.studyYears - (2024 + 2 / 12 - 2023)) < 1e-9); // the PhD's last stretch
  assert.deepEqual(studySegments(blob.study, items).map((z) => z.label), ["BEng", "PhD"]);
});

test("slugs come from the channels file", () => assert.deepEqual(slugs(channels), channels.map((c) => c.slug)));

test("pageOf wraps", () => assert.equal(pageOf([1, 2, 3, 4, 5, 6, 7], 2, 6).index, 0));

test("nextItem steps projects only", () => {
  assert.equal(nextItem(items, null, "milestone", ALL).id, "phd");
  assert.equal(nextItem(items, "phd", "milestone", ALL).id, "mbda");
});

test("clampStart keeps window inside career", () => assert.equal(clampStart(2025, 5, 2013, 2027), 2022));

test("the default view rolls the last 10 years", () => {
  assert.deepEqual(defaultView(2013, 2027), { from: 2017, to: 2027 });
  assert.deepEqual(defaultView(2019, 2027), { from: 2019, to: 2027 }); // short career: whole career
  assert.deepEqual(timebases(2013, 2027), [14, 10, 5, 1, 0.25]);
});

test("clusters merge close milestones", () => {
  // milestones at PhD 2017.67, MBDA 2026.0, sniffers 2026.17: at 100 px wide the last two are 1 px apart
  const c = clusterMilestones(items, 2013, 2027, 100, 16, ALL);
  assert.equal(c.length, 2); assert.deepEqual(c[1].ids, ["mbda", "sniffers"]);
});

test("moveEdge clamps and never crosses", () => {
  assert.deepEqual(moveEdge([2019, 2023], 0, -10, 2013, 2027), [2013, 2023]);
  const [a, b] = moveEdge([2019, 2023], 1, -10, 2013, 2027);
  assert.equal(a, 2019); assert.ok(Math.abs(b - 2019.02) < 1e-9);
});

test("state round-trips without style", () => {
  const s = { show: ["instruments"], from: 2017, to: 2024, f: "phd", cur: [2019, 2023], style: null };
  assert.deepEqual(decodeState(encodeState(s), D, LIM), s);
  assert.ok(!encodeState({ ...s, style: "paper" }).includes("style"));
});

test("decodeState rejects garbage", () => {
  assert.deepEqual(decodeState("style=neon&show=cats&from=2030&to=2001", D, LIM), { ...D, from: min, to: max }); // swapped, clamped
  assert.deepEqual(decodeState("from=2040", D, LIM), D); // zero-width window falls back
  assert.deepEqual(decodeState("%%%", D, LIM), D);
});

test("decodeState rejects attack strings", () => {
  for (const q of ["show=<script>alert(1)</script>", "f=\"><img src=x onerror=alert(1)>", "f=javascript:alert(1)",
                   "cur=1e309,NaN", "from=0x7E0&to=Infinity", "show=instruments,__proto__", "f=constructor"]) {
    const s = decodeState(q, D, LIM);
    assert.ok(s.show.every((x) => SLUGS.includes(x)));
    assert.ok(s.f === null || /^[a-z0-9-]+$/.test(s.f)); // checked against real ids later in the UI
    assert.ok([s.from, s.to].every(Number.isFinite));
  }
  assert.equal(Object.getPrototypeOf(decodeState("__proto__=x&constructor=y", D, LIM)), Object.prototype);
});

test("readouts gate to the selection", () => {
  const g = gatedReadouts(withFigures(items), 2017, 2020, ALL, CH);
  assert.equal(g.length, 4); assert.ok(g[0].label.startsWith("CH"));
  assert.equal(new Set(g.filter((r) => r.channel).map((r) => r.channel)).size, g.filter((r) => r.channel).length);
});

test("measureRows counts each project once", () => {
  const r = measureRows(withSkills(items), 2013, 2027, ALL, null, now);
  assert.equal(r.find((x) => x.channel === 1).projects, 1); // the PhD, not its parts
  assert.equal(r.find((x) => x.channel === 2).last, "now");
  assert.ok(r[0].years >= r[r.length - 1].years);
  const t = measureRows([items.find((i) => i.id === "mbda")], 2026, 2027, ALL, null, now); // a text-only role
  assert.deepEqual(t[0].skills, []); assert.equal(t[0].last, "now");
});

test("skills weight recent work", () => {
  const old = { id: "old", channel: 3, start: 2014, end: 2016, skills: ["Fortran"] };
  const recent = { id: "new", channel: 3, start: 2025, end: now, skills: ["Rust"] };
  // Fortran: 2 × 0.5 ** ((now − 2016) / 5) ≈ 0.45; Rust: 1
  assert.equal(measureRows([old, { ...old, id: "old2" }, recent], 2013, 2027, ALL, null, now)[0].skills[0], "Rust");
});

test("pickAt prefers the shortest project", () => {
  assert.equal(pickAt([...items, { id: "short", channel: 1, start: 2020, end: 2020.2 }], 2020.1, ALL).id, "short");
  assert.equal(pickAt(items, 2025.0, ALL), null);
});

test("readouts follow the selection", () => {
  const sn = readoutsFor(items.find((i) => i.id === "sniffers"), CH, ALL);
  assert.equal(sn.source, 2); assert.equal(sn.list.length, 4); assert.equal(sn.list[0].label, "CH2 · b0");
  const own = readoutsFor({ ...items.find((i) => i.id === "phd"), readouts: [{ label: "own", value: "1" }, { label: "a0", value: "0" }] }, CH, ALL);
  assert.deepEqual(own.list.map((r) => r.label), ["CH1 · own", "a0", "a1", "a2"]); // duplicates skipped
  assert.deepEqual(readoutsFor(null, CH, ALL).list.map((r) => r.label), ["CH1 · a0", "CH2 · b0", "CH7 · g0"]);
  assert.equal(readoutsFor(null, CH, [true, false, false, false, false, false, false]).list.length, 4);
  assert.equal(readoutsFor(null, CH, NONE).list[0].value, "off");
});

test("math is antisymmetric and zero for equal sides", () => {
  const hw = mathSources("hw"), sw = mathSources("sw");
  const m = mathSeries(items, 2013, 2027, 200, hw, sw), r = mathSeries(items, 2013, 2027, 200, sw, hw);
  assert.ok(m.every((v, i) => Math.abs(v + r[i]) < 1e-12)); // swapping A and B negates M
  assert.ok(mathSeries(items, 2013, 2027, 200, [1], [1]).every((v) => v === 0));
  const s = mathStats(items, 2013, 2027, hw, sw, now);
  assert.equal(s.aShare + s.bShare, 100);
});

test("overlay markers never overlap", () => {
  const series = [1, 2, 3, 4, 5, 6, 7].map((c) => ({ channel: c, mean: c / 10, y0: 100 })); // all at one level
  const { order, markers } = overlayLayout(series, 20, 180, 11, 3);
  const ys = markers.map((m) => m.y).sort((a, b) => a - b);
  assert.ok(ys.every((y, i) => i === 0 || y - ys[i - 1] >= 11)); assert.ok(ys[0] >= 20 && ys[ys.length - 1] <= 180);
  assert.equal(order[0], 7); assert.equal(order[order.length - 1], 3); // busiest at the back, hot at the front
});

test("storage that throws", () => {
  const bad = { getItem() { throw 1; }, setItem() { throw 1; } };
  assert.equal(readStoredStyle(bad), null); assert.equal(writeStoredStyle(bad, "hc"), false);
});

// Further tests for behaviour the brief describes but its tests don't reach.

test("normalise: max is the next quarter, open ends are now, short items get a month, aliases move", () => {
  assert.equal(now, 2026.75); assert.equal(max, 2027); assert.equal(min, 2013);
  assert.equal(items.find((i) => i.id === "mbda").end, now);
  const b = { ...blob, now: "2026-11", channels: [...CHANNELS, { n: 8, name: "Old", slug: "old", colour: "--c8", archived: true, alias: 2 }],
              items: [raw({ id: "blip", channel: 8, start: "2020-01", end: "2020-01" })] };
  const n = normalise(b);
  assert.equal(n.max, 2027); // 2026 + 10/12 rounds up to 2027.0
  assert.ok(close(n.items[0].end - n.items[0].start, 1 / 12)); assert.equal(n.items[0].channel, 2);
  assert.ok(!Object.isFrozen(blob.items[0]) && blob.items[0].start === "2017-09"); // the blob is not changed
});

test("edgeWidth scales with the view and is clamped", () => {
  assert.ok(close(edgeWidth(10), 0.12)); assert.ok(close(edgeWidth(100), 0.18)); assert.ok(close(edgeWidth(0.1), 0.006));
});

test("smoothActivity is about 1 inside a project and 0 well outside", () => {
  assert.ok(close(smoothActivity(items, 2020, 1, 0.12), 1, 1e-6));
  assert.ok(smoothActivity(items, 2015, 1, 0.12) < 1e-6);
  assert.ok(smoothActivity(items, 2017 + 8 / 12, 1, 0.12) > 0.49 && smoothActivity(items, 2017 + 8 / 12, 1, 0.12) < 0.51);
  assert.equal(maxChannelActivity(items, min, max), 2);
});

test("noiseAt is deterministic and stays in [-1, 1]", () => {
  const xs = Array.from({ length: 2000 }, (_, i) => noiseAt(2013 + i * 0.007));
  assert.ok(xs.every((v) => v >= -1 && v <= 1)); assert.equal(noiseAt(2020.123), noiseAt(2020.123));
  assert.ok(new Set(xs.map((v) => v.toFixed(3))).size > 100);
});

test("hidden channels get no lane; empty ones a thin lane", () => {
  assert.deepEqual(laneWeights(items, 2017, 2022, only(1, 3)), [1, null, 0, null, null, null, null]);
  const L = laneLayout([1, null, 0, 1, null, null, null], 0, 100);
  assert.equal(L[1].h, 0); assert.equal(L[2].h, 12); assert.equal(L[0].h, 44); assert.equal(L[3].h, 44);
  assert.deepEqual([L[0].y, L[2].y, L[3].y], [0, 44, 56]);
});

test("digital lines: roles bus, events and open-to-roles", () => {
  assert.deepEqual(rolesBus(items, 2013, 2027, ALL), [{ id: "mbda", label: "MBDA", start: 2026, end: now }]);
  assert.deepEqual(rolesBus(items, 2013, 2027, only(1)), []);
  assert.deepEqual(eventsIn(blob.events, 2020, 2027).map((e) => e.id), ["afhea"]);
  const o = openLevel("2026-06", 2013, 2027, now);
  assert.ok(close(o.start, 2026 + 5 / 12)); assert.equal(o.end, now);
  assert.equal(openLevel(null, 2013, 2027, now), null); assert.equal(openLevel("2026-06", 2013, 2020, now), null);
});

test("ticks pick the smallest step with 100 px per label", () => {
  assert.deepEqual(ticks(2020, 2025, 500).map((t) => t.label), ["2020", "2021", "2022", "2023", "2024", "2025"]);
  assert.deepEqual(ticks(2020, 2021, 400).map((t) => t.label), ["2020", "Apr", "Jul", "Oct", "2021"]);
  assert.equal(ticks(2020, 2021, 1200)[1].label, "Feb");
  assert.deepEqual(ticks(2000, 2030, 600).map((t) => t.t), [2000, 2005, 2010, 2015, 2020, 2025, 2030]);
});

test("milestones on hidden channels are not drawn", () => {
  assert.deepEqual(clusterMilestones(items, 2013, 2027, 100, 16, only(1)).map((c) => c.ids), [["phd"]]);
});

test("state with Math and overlay round-trips; bad values fall back", () => {
  const D2 = { ...D, m: null, layout: "lanes" };
  const s = { ...D2, show: ["instruments", "medical-imaging"], m: "hw-sw", layout: "overlay" };
  assert.deepEqual(decodeState(encodeState(s), D2, LIM), s);
  const bad = decodeState("m=hw-9&layout=grid", D2, LIM);
  assert.equal(bad.m, null); assert.equal(bad.layout, "lanes");
  assert.equal(decodeState("m=1-sw", D2, LIM).m, "1-sw");
  assert.deepEqual(decodeState("cur=2030,2020", D2, LIM).cur, [2020, max]);
  assert.equal(decodeState("cur=2020,2020.01", D2, LIM).cur, null);
  assert.equal(decodeState("?style=hc", D2, LIM).style, "hc");
});

test("stored style: valid values only", () => {
  const box = {}; const s = { getItem: (k) => box[k] ?? null, setItem: (k, v) => { box[k] = v; }, removeItem: (k) => { delete box[k]; } };
  assert.equal(writeStoredStyle(s, "paper"), true); assert.equal(readStoredStyle(s), "paper");
  assert.equal(box["scope-style"], "paper"); // the key static/js/theme-boot.js reads before paint
  box["scope-style"] = "neon"; assert.equal(readStoredStyle(s), null);
  assert.equal(writeStoredStyle(s, null), true); assert.equal(readStoredStyle(s), null);
});

test("pageOf and nextItem wrap both ways", () => {
  assert.deepEqual(pageOf([1, 2, 3, 4, 5, 6, 7], -1, 6), { items: [7], pages: 2, index: 1 });
  assert.deepEqual(pageOf([], 0, 6), { items: [], pages: 1, index: 0 });
  assert.equal(nextItem(items, "sniffers", "project", ALL).id, "phd");
  assert.equal(nextItem(items, null, "project", NONE), null);
});

test("math sources and stats", () => {
  assert.deepEqual(mathSources(3), [3]); assert.deepEqual(mathSources("4"), [4]); assert.deepEqual(mathSources("sw"), [3, 4, 5, 6]);
  const s = mathStats(items, 2013, 2027, mathSources("hw"), mathSources("sw"), now);
  assert.equal(s.aShare, 100); assert.equal(s.below, 0);
  assert.ok(s.above > 0.45 && s.above < 0.6, String(s.above)); // hardware busy for about 7.25 of 13.75 years
  assert.deepEqual(mathStats(items, 2030, 2031, [1], [2], now), { mean: 0, above: 0, below: 0, aShare: 0, bShare: 0 });
});

test("gated readouts pad with the stretch's length and project count", () => {
  const g = gatedReadouts(withFigures(items), 2017, 2020, ALL, CH);
  assert.deepEqual(g.map((r) => r.label), ["CH1 · phd", "ΔT", "projects", "peak"]);
  assert.equal(g[1].value, "3.0 yr"); assert.equal(g[2].value, "1");
  const none = gatedReadouts(items, 2026, 2027, ALL, CH); // text-only items fall back to the channel's first figure
  assert.equal(none[0].label, "CH2 · b0"); assert.equal(none.length, 4);
});

test("measure rows: focus, peak, proof and hidden channels", () => {
  const withProof = items.map((i) => (i.id === "sniffers" ? { ...i, proof: [{ kind: "repo", on_request: false }, { kind: "doc", on_request: true }] } : i));
  const names = channels.map((c) => c.name);
  const r = measureRows(withProof, 2013, 2027, ALL, null, now, names);
  const ch2 = r.find((x) => x.channel === 2);
  assert.equal(ch2.peak, 2); assert.deepEqual(ch2.proof, { total: 2, open: 1 }); assert.equal(ch2.name, "RF, wireless and embedded");
  assert.ok(close(ch2.years, now - 2026));
  assert.deepEqual(measureRows(items, 2013, 2027, only(1), null, now).map((x) => x.channel), [1]);
  const f = measureRows(items, 2013, 2027, ALL, "sniffers", now);
  assert.equal(f.length, 1); assert.equal(f[0].channel, 2); assert.equal(f[0].projects, 1);
  assert.deepEqual(measureRows(withSkills([items[1]]), 2026, 2027, ALL, null, now)[0].skills, []); // text-only adds none
});

// Final review fixes.

test("the wheel pans by its own delta, not a fixed tenth of the view", async () => {
  const { wheelPan } = await import("../../static/js/scope-core.mjs");
  assert.ok(close(wheelPan(0, -3, 0, 10, 1000), -0.03)); // a small trackpad step, in pixels
  assert.ok(close(wheelPan(0, 3, 1, 10, 1000), 0.48)); // lines count as 16 px
  assert.ok(close(wheelPan(50, -3, 0, 10, 1000), 0.5)); // the bigger axis wins
  assert.equal(wheelPan(0, 5, 0, 10, 0), 0);
});

test("any window width is kept and labelled; zoom steps to the next timebase", async () => {
  const { widthLabel, stepWidth } = await import("../../static/js/scope-core.mjs");
  assert.equal(widthLabel(14, 14), "career"); assert.equal(widthLabel(10, 14), "10 yr");
  assert.equal(widthLabel(7, 14), "7 yr"); assert.equal(widthLabel(2.5, 14), "2.5 yr"); assert.equal(widthLabel(0.25, 14), "3 mo");
  const TB = [14, 10, 5, 1, 0.25];
  assert.equal(stepWidth(TB, 7, 1), 5); assert.equal(stepWidth(TB, 7, -1), 10);
  assert.equal(stepWidth(TB, 10, 1), 5); assert.equal(stepWidth(TB, 0.25, 1), 0.25); assert.equal(stepWidth(TB, 14, -1), 14);
});

test("now never lags the visitor's own month", () => {
  const later = normalise(blob, "2027-03");
  assert.ok(close(later.now, 2027 + 2 / 12)); assert.equal(later.max, 2027.25);
  assert.ok(close(later.items.find((i) => i.id === "mbda").end, 2027 + 2 / 12));
  assert.equal(normalise(blob, "2020-01").now, 2026.75); // the build month is newer
  assert.equal(normalise(blob, "nonsense").now, 2026.75);
});

test("labels: role first, then in progress", () => {
  assert.deepEqual(labels({}), []);
  assert.deepEqual(labels({ role: true }), ["role"]);
  assert.deepEqual(labels({ wip: true }), ["in progress"]);
  assert.deepEqual(labels({ role: true, wip: true }), ["role", "in progress"]);
});
