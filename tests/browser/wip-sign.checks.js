// Browser checks for the work-in-progress sign (templates/components/wip.html). Run on a marked page,
// once as it is and once with --reduced-motion:
//   node tests/browser/run.mjs http://localhost:1112/rf-wireless-embedded/sniffers/ tests/browser/wip-sign.checks.js
//   node tests/browser/run.mjs http://localhost:1112/rf-wireless-embedded/sniffers/ tests/browser/wip-sign.checks.js 1280 900 --reduced-motion
// Returns { failed: [...], passed: [...] }. Each check states what a visitor should get.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const passed = [], failed = [];
  const expect = (name, ok, got) => (ok ? passed : failed).push(ok ? name : `${name} (got ${JSON.stringify(got)})`);
  const sign = document.querySelector(".wip-sign");
  if (!sign) return { failed: ["no .wip-sign on this page"], passed };
  const crash = sign.querySelector(".wip-crash"), list = sign.querySelector(".wip-list");
  const css = (el) => getComputedStyle(el);
  const mine = () => document.getAnimations().filter((a) => sign.contains(a.effect?.target));

  const label = sign.querySelector(".wip-note .lbl");
  expect("the label sits inline with its sentence", css(label).display === "inline-block", css(label).display);

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    expect("reduced motion skips the crash", css(crash).display === "none", css(crash).display);
    expect("reduced motion runs no animation", mine().length === 0, mine().length);
    expect("reduced motion shows the checklist at once", css(list).visibility === "visible", css(list).visibility);
  } else {
    const ends = mine().map((a) => a.effect.getComputedTiming().endTime);
    expect("the crash plays", ends.length > 0, ends.length);
    expect("all motion ends by 5 s", ends.every((e) => Number.isFinite(e) && e <= 5000), Math.max(...ends));
    // endTime above is measured from each animation's own start; here, wait for them all to finish.
    const all = mine();
    await Promise.race([Promise.all(all.map((a) => a.finished)), sleep(7000)]);
    expect("everything stops", all.every((a) => a.playState === "finished"), all.map((a) => a.playState));
    expect("the crash is gone", css(crash).visibility === "hidden", css(crash).visibility);
    expect("the checklist shows", css(list).visibility === "visible", css(list).visibility);
  }

  // The high-contrast theme, picked after the page has loaded, hides the crash at once.
  document.documentElement.dataset.style = "hc";
  expect("high contrast hides the crash", css(crash).display === "none", css(crash).display);
  return { failed, passed };
})();
