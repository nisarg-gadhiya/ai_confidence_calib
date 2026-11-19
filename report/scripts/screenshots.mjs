// Screenshots of the running app for the report (headless Chrome, DevTools protocol).
// Ask-view shots intercept POST /api/ask and answer with a REAL stored response
// (pipeline_output of a run in backend/data/calibration_runs.json), so no LLM calls are made.
//   node report/scripts/screenshots.mjs [frontendUrl]
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const figures = join(root, "report", "figures");
const base = process.argv[2] || "http://localhost:5180/";
const runs = JSON.parse(readFileSync(join(root, "backend", "data", "calibration_runs.json"), "utf8"));
const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Stored runs used for the Ask-view shots (index in calibration_runs.json).
const STORED = { arithmetic: 20, factual: 14, logical: 28 };

async function session() {
  const port = 9900 + Math.floor(Math.random() * 90);
  const profile = mkdtempSync(join(tmpdir(), "cdp-"));
  const proc = spawn(chrome, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run", "--hide-scrollbars", "about:blank"]);
  let wsUrl;
  for (let i = 0; i < 60 && !wsUrl; i++) {
    await sleep(200);
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page")?.webSocketDebuggerUrl; } catch {}
  }
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const pending = new Map();
  const handlers = [];
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
    if (msg.method) handlers.forEach((h) => h(msg));
  };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  return { send, on: (h) => handlers.push(h), close: () => { ws.close(); proc.kill(); } };
}

async function shot(name, { width = 1280, height = 2400, theme = "light", hash = "", ask = null, js = "", clipTop = null }) {
  const s = await session();
  await s.send("Page.enable");
  await s.send("Runtime.enable");
  await s.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 2, mobile: width < 600 });
  await s.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
  if (ask) {
    const body = Buffer.from(JSON.stringify(runs[STORED[ask]].pipeline_output)).toString("base64");
    await s.send("Fetch.enable", { patterns: [{ urlPattern: "*/api/ask*" }] });
    s.on((msg) => {
      if (msg.method !== "Fetch.requestPaused") return;
      const { requestId, request } = msg.params;
      if (request.method === "OPTIONS") {
        s.send("Fetch.fulfillRequest", { requestId, responseCode: 204, responseHeaders: [
          { name: "Access-Control-Allow-Origin", value: "*" }, { name: "Access-Control-Allow-Headers", value: "*" }, { name: "Access-Control-Allow-Methods", value: "*" }] });
        return;
      }
      s.send("Fetch.fulfillRequest", { requestId, responseCode: 200, body, responseHeaders: [
        { name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: "*" }] });
    });
  }
  await s.send("Page.navigate", { url: base + hash });
  await sleep(hash ? 6000 : 4000);
  if (ask) {
    const question = runs[STORED[ask]].question.replace(/`/g, "'");
    await s.send("Runtime.evaluate", { awaitPromise: true, expression: `(async () => {
      const ta = document.querySelector("#question");
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
      setter.call(ta, ${JSON.stringify(question)});
      ta.dispatchEvent(new Event("input", { bubbles: true }));
      await new Promise(r => setTimeout(r, 200));
      document.querySelector(".primary-button").click();
    })()` });
    await sleep(5000);
  }
  if (js) {
    const r = await s.send("Runtime.evaluate", { expression: js, awaitPromise: true });
    if (r.result?.exceptionDetails) console.error(name, "script error", JSON.stringify(r.result.exceptionDetails).slice(0, 300));
    await sleep(4000);
  }
  const metrics = await s.send("Runtime.evaluate", { expression: "JSON.stringify({h: document.documentElement.scrollHeight})", returnByValue: true });
  const fullHeight = Math.min(JSON.parse(metrics.result.result.value).h, height);
  const top = clipTop ?? 0;
  const shotRes = await s.send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: top, width, height: Math.max(200, fullHeight - top), scale: 1 } });
  writeFileSync(join(figures, "raw", `${name}.png`), Buffer.from(shotRes.result.data, "base64"));
  console.log("saved", name, width, fullHeight - top);
  s.close();
}

const openRun = (text, tab = "") => `(async () => {
  const row = [...document.querySelectorAll(".run-table tbody tr")].find(r => r.textContent.includes(${JSON.stringify(text)}));
  row.click();
  await new Promise(r => setTimeout(r, 900));
  ${tab ? `[...document.querySelectorAll(".tab")].find(t => t.textContent.includes(${JSON.stringify(tab)})).click();` : ""}
  const d = document.querySelector(".run-detail");
  document.querySelectorAll(".dash-head, .filter-row, .stat-row, .chart-grid, .section-card").forEach(el => { if (!d.contains(el)) el.style.display = "none"; });
  window.scrollTo(0, 0);
})()`;

await fetch(base).catch(() => {});
await shot("_warmup", { height: 600 });
await shot("ui_ask_empty", { height: 1000 });
await shot("ui_ask_arithmetic", { ask: "arithmetic", height: 2600 });
await shot("ui_ask_factual", { ask: "factual", height: 2600,
  js: `(async () => { document.querySelectorAll(".link-button")[0]?.click(); })()` });
await shot("ui_ask_logical", { ask: "logical", height: 2800 });
await shot("ui_analytics", { hash: "#analytics", height: 1900 });
await shot("ui_run_history", { hash: "#analytics", height: 3200, js: `(async () => {
  document.querySelectorAll(".dash-head, .filter-row, .stat-row, .chart-grid").forEach(el => el.style.display = "none");
})()` });
await shot("ui_dark_detail", { hash: "#analytics", theme: "dark", height: 2400, js: openRun("Which mission first landed") });
await shot("ui_json_view", { hash: "#analytics", height: 1500, js: openRun("what is LSTM?", "JSON") });
await shot("ui_mobile", { width: 400, height: 2600, ask: "arithmetic" });
process.exit(0);
