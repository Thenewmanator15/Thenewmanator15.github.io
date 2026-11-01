import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const JS = new URL("../../static/js/", import.meta.url);

test("init is exported and leaves the page alone without a data blob", async () => {
  const { init } = await import("../../static/js/scope-ui.mjs");
  assert.equal(typeof init, "function");
  assert.doesNotThrow(() => init({ querySelector: () => null })); // the server-rendered page stays as it is
});

test("no script builds HTML from strings", () => {
  for (const f of readdirSync(JS).filter((n) => /\.m?js$/.test(n))) {
    const src = readFileSync(new URL(f, JS), "utf8");
    for (const bad of ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"]) {
      assert.ok(!src.includes(bad), `${f} uses ${bad}`);
    }
  }
});

test("links from the data blob keep only https, site paths and page anchors", async () => {
  const { safeHref } = await import("../../static/js/scope-ui.mjs");
  assert.equal(safeHref("https://github.com/x", "/a/"), "https://github.com/x");
  assert.equal(safeHref("/rf-wireless-embedded/sniffers/#photos", "/a/"), "/rf-wireless-embedded/sniffers/#photos");
  assert.equal(safeHref("#photos", "/a/b/"), "/a/b/#photos");
  assert.equal(safeHref("report.pdf", "/a/b/"), "/a/b/report.pdf");
  for (const bad of ["javascript:alert(1)", "JaVaScRiPt:x", "http://x.example", "//evil.example/x", "data:text/html,x",
                     "mailto:a@b.c", " javascript:x", "java\tscript:x", "", null, undefined, 42]) {
    assert.equal(safeHref(bad, "/a/"), null, String(bad));
  }
});

test("put never turns a missing child into the text 'null'", async () => {
  const { put } = await import("../../static/js/scope-ui.mjs");
  let got = null;
  put({ replaceChildren: (...a) => { got = a; } }, "a", null, [false, "b", [undefined, 0]]);
  assert.deepEqual(got, ["a", "b", 0]);
  const src = readFileSync(new URL("scope-ui.mjs", JS), "utf8");
  assert.equal(src.split(".replaceChildren(").length - 1, 1, "every replaceChildren call goes through put()");
});
