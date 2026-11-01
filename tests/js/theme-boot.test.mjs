// The theme start-up script runs in <head> before the page paints.
// It applies a theme the visitor picked earlier and otherwise leaves the choice to the browser.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

const src = readFileSync(new URL("../../static/js/theme-boot.js", import.meta.url), "utf8");

function run(storage) {
  const attrs = {};
  const document = { documentElement: { setAttribute: (k, v) => { attrs[k] = v; } } };
  runInNewContext(src, { document, localStorage: storage });
  return attrs;
}

const store = (v) => ({ getItem: (k) => (k === "scope-style" ? v : null) });

test("a stored theme is applied", () => {
  assert.deepEqual(run(store("paper")), { "data-style": "paper" });
});

test("nothing stored leaves data-style unset", () => {
  assert.deepEqual(run(store(null)), {});
});

test("an unknown stored value is ignored", () => {
  assert.deepEqual(run(store("<script>")), {});
});

test("blocked storage does not throw", () => {
  const bad = { getItem() { throw new Error("SecurityError"); } };
  assert.deepEqual(run(bad), {});
});
