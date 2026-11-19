// Render report/diagrams/*.mmd to report/figures/<name>.svg and .png (3x scale ~ 300 dpi)
// using the locally installed mermaid package and headless Chrome (DevTools protocol).
//   node report/scripts/render_mermaid.mjs [name ...]
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, readdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const report = join(here, "..");
const diagrams = join(report, "diagrams");
const figures = join(report, "figures");
const mermaidJs = join(report, "tools", "node_modules", "mermaid", "dist", "mermaid.min.js");
const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";

const only = process.argv.slice(2);
const files = readdirSync(diagrams).filter((f) => f.endsWith(".mmd") && (!only.length || only.includes(basename(f, ".mmd"))));

const page = `<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff;font-family:Arial,Helvetica,sans-serif}#out{display:inline-block;padding:12px}</style>
<script src="${pathToFileURL(mermaidJs).href}"></script></head><body><div id="out"></div></body></html>`;
const pagePath = join(mkdtempSync(join(tmpdir(), "mmd-")), "render.html");
writeFileSync(pagePath, page);

const port = 9600 + Math.floor(Math.random() * 300);
const profile = mkdtempSync(join(tmpdir(), "cdp-"));
const proc = spawn(chrome, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  "--allow-file-access-from-files", "--no-first-run", "about:blank"]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let wsUrl;
for (let i = 0; i < 60 && !wsUrl; i++) {
  await sleep(200);
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    wsUrl = list.find((t) => t.type === "page")?.webSocketDebuggerUrl;
  } catch {}
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
};
const send = (method, params = {}) =>
  new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1200, deviceScaleFactor: 3, mobile: false });
await send("Page.navigate", { url: pathToFileURL(pagePath).href });
await sleep(1500);

const config = {
  startOnLoad: false,
  securityLevel: "loose",
  theme: "base",
  flowchart: { htmlLabels: true, curve: "basis", nodeSpacing: 40, rankSpacing: 46, useMaxWidth: false },
  class: { useMaxWidth: false },
  sequence: { useMaxWidth: false, actorMargin: 24, width: 120, boxMargin: 6, messageFontSize: 15, actorFontSize: 14, mirrorActors: false },
  themeVariables: {
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "15px",
    primaryColor: "#eaf2fc",
    primaryBorderColor: "#2a78d6",
    primaryTextColor: "#0b0b0b",
    secondaryColor: "#fdeee6",
    tertiaryColor: "#f6f6f3",
    lineColor: "#52514e",
    clusterBkg: "#f9f9f7",
    clusterBorder: "#c3c2b7",
    actorBkg: "#eaf2fc",
    actorBorder: "#2a78d6",
    noteBkgColor: "#fff6dd",
  },
};

for (const file of files) {
  const name = basename(file, ".mmd");
  const source = readFileSync(join(diagrams, file), "utf8");
  const expr = `(async () => {
    mermaid.initialize(${JSON.stringify(config)});
    const { svg } = await mermaid.render("d_${name}", ${JSON.stringify(source)});
    const out = document.getElementById("out");
    out.innerHTML = svg;
    const el = out.querySelector("svg");
    el.style.maxWidth = "none";
    const r = out.getBoundingClientRect();
    return JSON.stringify({ svg: el.outerHTML, x: r.x, y: r.y, w: Math.ceil(r.width), h: Math.ceil(r.height) });
  })()`;
  const res = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (res.result?.exceptionDetails || !res.result?.result?.value) {
    console.error("FAILED", name, JSON.stringify(res.result?.exceptionDetails || res).slice(0, 600));
    continue;
  }
  const box = JSON.parse(res.result.result.value);
  writeFileSync(join(figures, `${name}.svg`), box.svg);
  await send("Emulation.setDeviceMetricsOverride", { width: Math.max(1600, box.w + 40), height: Math.max(1200, box.h + 40), deviceScaleFactor: 3, mobile: false });
  await sleep(150);
  const shot = await send("Page.captureScreenshot", {
    format: "png",
    clip: { x: box.x, y: box.y, width: box.w, height: box.h, scale: 1 },
    captureBeyondViewport: true,
  });
  writeFileSync(join(figures, `${name}.png`), Buffer.from(shot.result.data, "base64"));
  console.log("rendered", name, `${box.w}x${box.h}`);
}
ws.close();
proc.kill();
process.exit(0);
