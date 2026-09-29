// Screenshots for the studio's Help, made from the running app.
//
//   cd app && npm run dev            (in one terminal, or preview_start anc8-app)
//   cd app && npm run help:shots     (or: node scripts/capture_help_shots.mjs --base http://localhost:3000)
//
// For every topic in app/src/lib/help/shots.json the script opens the topic's screen,
// saves the first screenful as <topic>.jpg and records where every panel ([data-help])
// and shell part ([data-mark]) sits in it, so the Help can draw numbered callouts that
// stay on their panels when the layout changes. It then crops every [data-help] panel
// as <help id>.jpg. `special` entries set up a state first (hover a hint, type in the
// finder, open the tour) and crop one element. Everything goes to app/public/help/shots/
// with an index.json the Help reads. Light theme, 2x pixels, JPEG.
//
// playwright-core is pinned (app/package.json) to the version whose Chromium is already
// cached in %LOCALAPPDATA%\ms-playwright, so no browser is downloaded.

import { createRequire } from "node:module";
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const APP = join(ROOT, "app");
const OUT = join(APP, "public", "help", "shots");
const require = createRequire(join(APP, "package.json"));
const { chromium } = require("playwright-core");

const args = process.argv.slice(2);
const arg = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : dflt;
};
const BASE = arg("base", "http://localhost:3000").replace(/\/+$/, "");
const ONLY = arg("only", null); // a topic key, or a special id, to re-shoot just that
const QUALITY = Number(arg("quality", 78));

const manifest = JSON.parse(readFileSync(join(APP, "src", "lib", "help", "shots.json"), "utf8"));
const [VW, VH] = manifest.viewport;

const CSS = `
  nextjs-portal, [data-nextjs-toast], [data-next-badge-root] { display: none !important; }
  *, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }
`;

async function ready(page) {
  await page.waitForLoadState("networkidle", { timeout: 60000 }).catch(() => {});
  await page
    .waitForFunction(
      () => !document.querySelector("[aria-busy='true']") && document.fonts.status === "loaded"
        && !document.body.innerText.includes("Loading the studio"),
      null,
      { timeout: 45000 },
    )
    .catch(() => console.warn("  (still loading after 45 s; shooting anyway)"));
  await page.waitForTimeout(1200);
}

async function open(context, url, actions = []) {
  const page = await context.newPage();
  await page.goto(BASE + url, { waitUntil: "domcontentloaded", timeout: 120000 });
  await page.addStyleTag({ content: CSS });
  await ready(page);
  for (const a of actions) {
    if (a.click) await page.locator(a.click).first().click({ timeout: 10000 });
    if (a.hover) await page.locator(a.hover).first().hover({ timeout: 10000 });
    if (a.type) await page.keyboard.type(a.type, { delay: 40 });
    await page.waitForTimeout(a.wait ?? 500);
  }
  return page;
}

/** Boxes of every panel and shell part visible in the first screenful, in CSS pixels. */
async function marks(page) {
  return page.evaluate(([vw, vh]) => {
    const out = {};
    for (const el of document.querySelectorAll("[data-help], [data-mark]")) {
      const key = el.getAttribute("data-help") ?? `mark:${el.getAttribute("data-mark")}`;
      if (out[key]) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      const x = Math.max(0, r.left), y = Math.max(0, r.top);
      const x2 = Math.min(vw, r.right), y2 = Math.min(vh, r.bottom);
      // Only what shows: at least 24 px of it inside the screenful.
      if (x2 - x < 24 || y2 - y < 24) continue;
      out[key] = [Math.round(x), Math.round(y), Math.round(x2 - x), Math.round(y2 - y)];
    }
    return out;
  }, [VW, VH]);
}

const index = { base: "captured from the running studio by scripts/capture_help_shots.mjs", shots: {} };
const failed = [];
const topicOf = (id) => id.split(".")[0];

async function shootTopic(context, key, spec) {
  console.log(`topic ${key}: ${spec.url}`);
  const page = await open(context, spec.url, spec.actions);
  await page.setViewportSize({ width: VW, height: VH });
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(OUT, `${key}.jpg`), type: "jpeg", quality: QUALITY });
  index.shots[key] = { w: VW, h: VH, marks: await marks(page) };

  // Crops: a tall window so whole panels fit, each panel photographed where it stands.
  await page.setViewportSize({ width: VW, height: manifest.tall });
  await page.waitForTimeout(900);
  const ids = await page.evaluate(() =>
    [...new Set([...document.querySelectorAll("[data-help]")].map((e) => e.getAttribute("data-help")))]);
  for (const id of ids) {
    // A panel that shows on several screens is taken from its own topic's screen.
    if (index.shots[id] && topicOf(id) !== key) continue;
    const el = page.locator(`[data-help="${id}"]`).first();
    const box = await el.boundingBox().catch(() => null);
    if (!box || box.width < 8 || box.height < 8) continue;
    try {
      await el.screenshot({ path: join(OUT, `${id}.jpg`), type: "jpeg", quality: QUALITY, timeout: 20000 });
      index.shots[id] = { w: Math.round(box.width), h: Math.round(box.height) };
    } catch (e) {
      failed.push(`${id}: ${e.message.split("\n")[0]}`);
    }
  }
  await page.close();
}

async function shootSpecial(context, s) {
  console.log(`special ${s.id}: ${s.url}`);
  const actions = [];
  if (s.hover) actions.push({ hover: s.hover, wait: s.wait ?? 700 });
  if (s.click) actions.push({ click: s.click, wait: 300 });
  if (s.type) actions.push({ type: s.type, wait: s.wait ?? 1200 });
  if (!s.hover && !s.type && s.click) actions[actions.length - 1].wait = s.wait ?? 800;
  const page = await open(context, s.url, actions);
  const box = await page.locator(s.clip).first().boundingBox();
  if (!box) throw new Error(`nothing matches ${s.clip}`);
  const [t, r, b, l] = s.pad ?? [0, 0, 0, 0];
  const vp = page.viewportSize();
  const x = Math.max(0, box.x - l), y = Math.max(0, box.y - t);
  const clip = {
    x, y,
    width: Math.min(vp.width - x, box.width + l + r),
    height: Math.min(vp.height - y, box.height + t + b),
  };
  await page.screenshot({ path: join(OUT, `${s.id}.jpg`), type: "jpeg", quality: QUALITY, clip });
  index.shots[s.id] = { w: Math.round(clip.width), h: Math.round(clip.height) };
  await page.close();
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const indexPath = join(OUT, "index.json");
  if (ONLY) {
    try { Object.assign(index.shots, JSON.parse(readFileSync(indexPath, "utf8")).shots); } catch { /* first run */ }
  } else {
    for (const f of readdirSync(OUT)) if (f.endsWith(".jpg")) rmSync(join(OUT, f));
  }

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: VW, height: VH },
    deviceScaleFactor: 2,
    colorScheme: "light",
    reducedMotion: "reduce",
  });
  await context.addInitScript(() => {
    try { localStorage.setItem("anc-theme", "light"); } catch { /* ignore */ }
  });

  for (const [key, spec] of Object.entries(manifest.topics)) {
    if (ONLY && ONLY !== key) continue;
    try { await shootTopic(context, key, spec); } catch (e) { failed.push(`${key}: ${e.message.split("\n")[0]}`); }
  }
  for (const s of manifest.special) {
    if (ONLY && ONLY !== s.id && ONLY !== topicOf(s.id)) continue;
    try { await shootSpecial(context, s); } catch (e) { failed.push(`${s.id}: ${e.message.split("\n")[0]}`); }
  }
  await browser.close();

  const sorted = Object.fromEntries(Object.entries(index.shots).sort(([a], [b]) => a.localeCompare(b)));
  writeFileSync(indexPath, JSON.stringify({ ...index, shots: sorted }, null, 1) + "\n");
  console.log(`\n${Object.keys(sorted).length} shots in ${OUT}`);
  if (failed.length) {
    console.error(`${failed.length} failed:\n  ${failed.join("\n  ")}`);
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
