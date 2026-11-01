// Browser checks for the front page that need a real DOM. Run them headless with
//   node tests/browser/run.mjs http://localhost:1112/ tests/browser/scope-ui.checks.js 1280 900
// or paste into the console on the front page; it returns { failed: [...], passed: [...] }.
// Each check states what a visitor should get. Run it after any change to scope-ui.mjs.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
  const btn = (t) => $$("#strip button").find((b) => b.textContent.startsWith(t));
  const passed = [], failed = [];
  const expect = (name, ok, got) => (ok ? passed : failed).push(ok ? name : `${name} (got ${JSON.stringify(got)})`);
  const key = (el, k, extra = {}) => el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, ...extra }));
  const inZoom = () => !!document.activeElement?.closest?.("#zoom");
  const plot = $("#plot");

  expect("no 'null' text anywhere in the scope", !/null/.test($("#scope").textContent), $("#scope").textContent.match(/.{0,20}null.{0,10}/)?.[0]);

  for (const b of $$("#strip button")) {
    const visible = b.textContent.trim(), name = (b.getAttribute("aria-label") || visible).trim();
    if (visible && !/^[◂▸↺]$/.test(visible) && !name.includes(visible)) expect(`button name contains "${visible}"`, false, name);
  }
  passed.push("button names contain their visible labels (checked above)");

  // On a laptop-sized window the measurement table fits, so no column (Proof) hides behind a sideways scroll.
  const mtw = $(".mtw");
  if (innerWidth >= 1000 && mtw) {
    expect("the measurement table fits at laptop width", mtw.scrollWidth <= mtw.clientWidth + 1, { scroll: mtw.scrollWidth, client: mtw.clientWidth });
  }

  // Opening a card from a tile moves focus into the card; Clear returns it to that tile.
  const tile = $("#tiles .pj"), id = tile.dataset.id;
  tile.focus(); tile.click(); await sleep(150);
  expect("a tile opens its card with focus inside the card", inZoom(), document.activeElement?.outerHTML?.slice(0, 60));
  const h3 = $("#zoom h3");
  plot.dispatchEvent(new WheelEvent("wheel", { deltaY: -40, bubbles: true, cancelable: true })); await sleep(150);
  expect("panning with a card open leaves the card alone (no re-announcement)", $("#zoom h3") === h3, "card rebuilt");
  expect("panning keeps focus in the card", inZoom(), document.activeElement?.outerHTML?.slice(0, 60));
  $("#zoom .zk button").click(); await sleep(150);
  expect("Clear returns focus to the tile that opened the card", document.activeElement?.dataset?.id === id, document.activeElement?.outerHTML?.slice(0, 60));

  // The same from a digital-line segment, with the keyboard.
  const seg = $(".dseg[data-line='D0']");
  if (seg) {
    const sid = seg.dataset.id;
    seg.focus(); key(seg, "Enter"); await sleep(150);
    expect("Enter on a role segment opens its card with focus inside", inZoom(), document.activeElement?.outerHTML?.slice(0, 60));
    $("#zoom .zk button").click(); await sleep(150);
    expect("Clear returns focus to the segment", document.activeElement?.dataset?.id === sid && document.activeElement?.dataset?.line === "D0",
      document.activeElement?.outerHTML?.slice(0, 60));
  }

  // A milestone, with the keyboard.
  const mk = $("#svg .mk");
  if (mk) {
    mk.focus(); key(mk, "Enter"); await sleep(150);
    expect("Enter on a milestone opens its card with focus inside", inZoom(), document.activeElement?.outerHTML?.slice(0, 60));
    $("#zoom .zk button").click(); await sleep(150);
  }

  // The pager keeps focus (zoomed out to the whole career, so there is more than one page).
  btn("Zoom −").click(); await sleep(150);
  const more = $("#tiles .more");
  if (more) {
    more.focus(); more.click(); await sleep(150);
    expect("the pager keeps focus after paging", document.activeElement?.classList?.contains("more"), document.activeElement?.outerHTML?.slice(0, 60));
  } else failed.push("no pager even at career width");

  // The wheel moves the view by its own amount: 60 px of wheel on a w-px plot moves 60/w of the window.
  btn("Autoset").click(); await sleep(150);
  const start = () => Number(/On screen: (\d{4})/.exec($("#rec").getAttribute("aria-label"))[1]);
  const s0 = start(), w = plot.getBoundingClientRect().width, years = (60 / Math.max(200, w)) * 10;
  for (let i = 0; i < 20; i++) plot.dispatchEvent(new WheelEvent("wheel", { deltaY: -3, bubbles: true, cancelable: true }));
  await sleep(150);
  expect("a small wheel flick moves the view by its own amount", s0 - start() <= Math.ceil(years) + 1, { s0, s1: start(), years });
  btn("Autoset").click(); await sleep(150);

  // An unfinished project says "in progress" on its tile and in its card; a marked part does in its project's card.
  // (No real page is unfinished now; fixture tests cover the labels.)
  const findTile = async (pid) => {
    for (let k = 0; k < 8; k++) {
      const t = $(`#tiles .pj[data-id='${pid}']`);
      if (t) return t;
      const next = $("#tiles .more");
      if (!next) return null;
      next.click(); await sleep(150);
    }
    return null;
  };
  btn("Zoom −").click(); await sleep(150);
  const sn = await findTile("sniffers");
  expect("the sniffers tile is not marked in progress", !!sn && !sn.querySelector(".rl.wip"), sn?.textContent ?? "no tile");
  const phdTile = await findTile("phd");
  phdTile?.click(); await sleep(150);
  expect("the PhD card itself has no in progress label", !$("#zoom h3 .rl.wip"), $("#zoom h3")?.textContent ?? "no card");
  const driver = $$("#zoom .parts .plink").find((a) => a.textContent === "The driver");
  expect("the PhD card lists the driver part, unlabelled", !!driver && !driver.nextElementSibling?.matches(".rl.wip"), $("#zoom .parts")?.textContent ?? "no parts line");
  $("#zoom .zk button")?.click(); await sleep(150);
  btn("Autoset").click(); await sleep(150);

  return { failed, passed };
})();
