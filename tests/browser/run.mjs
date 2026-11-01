// Runs a browser checks file against a page in a headless Edge or Chrome, over the DevTools protocol.
// Works when no browser window is in view (a hidden tab throttles timers, which stalls the checks).
//
//   node tests/browser/run.mjs URL CHECKS_FILE [WIDTH] [HEIGHT] [--reduced-motion]
//
// The checks file is an async expression that returns { failed: string[], passed: string[] }.
// The browser is $BROWSER, else Edge's default path on Windows, else google-chrome. Exits 0 only when
// nothing failed and the page logged no errors. Needs Node 24 (built-in WebSocket); no dependencies.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = process.argv.slice(2);
const reduced = args.includes("--reduced-motion");
const [url, checksFile, width = "1280", height = "900"] = args.filter((a) => a !== "--reduced-motion");
if (!url || !checksFile) {
  console.error("usage: node tests/browser/run.mjs URL CHECKS_FILE [WIDTH] [HEIGHT] [--reduced-motion]");
  process.exit(2);
}
const browser = process.env.BROWSER
  || (process.platform === "win32" ? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" : "google-chrome");
const port = 9300 + Math.floor(Math.random() * 600);
const profile = mkdtempSync(join(tmpdir(), "browser-checks-"));
const proc = spawn(browser, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
const exited = new Promise((r) => proc.once("exit", r));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let code = 1;
try {
  let page;
  for (let i = 0; i < 50 && !page; i++) {
    await sleep(200);
    try { page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
  }
  if (!page) throw new Error(`the browser did not start (${browser})`);

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.addEventListener("open", r, { once: true }); ws.addEventListener("error", j, { once: true }); });
  let id = 0;
  const waiting = new Map(), events = [];
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); } else events.push(msg);
  });
  const send = (method, params = {}) => new Promise((r) => { const n = ++id; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });

  await send("Emulation.setDeviceMetricsOverride", { width: Number(width), height: Number(height), deviceScaleFactor: 1, mobile: false });
  // Always set it: the browser otherwise inherits the computer's own setting, and the checks would silently
  // take the other path.
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" }] });
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url });
  for (let i = 0; i < 100 && !events.some((e) => e.method === "Page.loadEventFired"); i++) await sleep(100);
  await sleep(800);
  const res = await send("Runtime.evaluate", { expression: readFileSync(checksFile, "utf8"), awaitPromise: true, returnByValue: true });
  const errors = events.filter((e) => e.method === "Runtime.exceptionThrown"
    || (e.method === "Runtime.consoleAPICalled" && e.params.type === "error"));
  const value = res.result?.result?.value;
  console.log(JSON.stringify({ url, viewport: `${width}x${height}`, reducedMotion: reduced,
    result: value ?? res.result?.exceptionDetails ?? res, pageErrors: errors.length }, null, 2));
  ws.close();
  code = Array.isArray(value?.failed) && value.failed.length === 0 && errors.length === 0 ? 0 : 1;
} catch (e) {
  console.error(String(e));
} finally {
  proc.kill();
  await exited;
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
process.exit(code);
