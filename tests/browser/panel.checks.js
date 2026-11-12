// Browser checks for a project page in the panel layout (front matter panel = true). Run at laptop and
// phone width:
//   node tests/browser/run.mjs http://localhost:1111/rf-wireless-embedded/sniffers/ tests/browser/panel.checks.js 1280 900
//   node tests/browser/run.mjs http://localhost:1111/rf-wireless-embedded/sniffers/ tests/browser/panel.checks.js 390 844
// Returns { failed: [...], passed: [...] }. Each check states what a visitor should get.
(async () => {
  const passed = [], failed = [];
  const expect = (name, ok, got) => (ok ? passed : failed).push(ok ? name : `${name} (got ${JSON.stringify(got)})`);
  if (!document.querySelector(".panelhead")) return { failed: ["no .panelhead on this page"], passed };

  const doc = document.documentElement;
  expect("no sideways scroll", doc.scrollWidth <= innerWidth + 1, [doc.scrollWidth, innerWidth]);

  const charts = [...document.querySelectorAll(".chartbox")];
  const short = charts.filter((c) => (c.getAttribute("aria-label") || "").trim().length < 40)
    .map((c) => c.getAttribute("aria-label"));
  expect("every chart has a text description of 40 characters or more", charts.length > 0 && short.length === 0, short);

  // Chart text as drawn on screen: its font size scaled by how wide the chart is shown.
  const tiny = [];
  for (const svg of document.querySelectorAll(".chartbox svg.chart")) {
    const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    const px = Math.min(...[...svg.querySelectorAll("text")].map((t) => parseFloat(getComputedStyle(t).fontSize) * scale));
    if (px < 10) tiny.push(`${svg.closest("figure")?.querySelector("figcaption")?.textContent.slice(0, 30)}: ${px.toFixed(1)} px`);
  }
  expect("chart text is at least 10 px on screen", tiny.length === 0, tiny);

  const dots = [...document.querySelectorAll(".mcard .dot-on, .mcard .dot-off, .mcard .na")];
  const mute = dots.filter((d) => !d.querySelector(".sr")?.textContent.trim()).length;
  expect("every dot and dash in a matrix has words for screen readers", mute === 0, mute);
  expect("the matrix legend is there", !document.querySelector(".mx .dot-on, .mx .dot-off, .mx .na") || !!document.querySelector(".mxkey"), null);

  const folds = [...document.querySelectorAll("details.fold")];
  const noHeading = folds.filter((f) => !f.querySelector(":scope > summary h2[id]")).length;
  expect("every fold's title is a heading with an id", noHeading === 0, noHeading);
  if (folds.length) {
    const startOpen = folds.filter((f) => f.open);
    const hidden = startOpen.filter((f) => !(f.querySelector(":scope > :not(summary)")?.getBoundingClientRect().height > 0)).length;
    expect("a fold that starts open shows its text", hidden === 0, hidden);
    // Test opening on a fold that starts closed (the PhD overview's "In brief" starts open).
    const fold = folds.find((f) => !f.open) || folds[0], summary = fold.querySelector(":scope > summary");
    summary.focus();
    expect("a fold's title takes keyboard focus", document.activeElement === summary, document.activeElement?.tagName);
    // Script can't press a real key; Enter and Space on a focused summary act as this click does.
    summary.click();
    expect("a fold opens", fold.open === true, fold.open);
    const inside = fold.querySelector(":scope > :not(summary)");
    expect("its text shows once open", !!inside && inside.getBoundingClientRect().height > 0, null);
    summary.click();
  }

  const cramped = [...document.querySelectorAll(".mcard td, .mcard th, .mcard")]
    .filter((c) => c.scrollWidth > c.clientWidth + 1).map((c) => c.textContent.trim().slice(0, 40));
  expect("matrix cells wrap inside their cards", cramped.length === 0, cramped);

  const wide = [...document.querySelectorAll(".chartfig, .stiles, .lcd, .duo")]
    .filter((e) => e.getBoundingClientRect().right > innerWidth + 1).map((e) => e.className);
  expect("figures, tiles and readouts fit the screen", wide.length === 0, wide);
  return { failed, passed };
})();
