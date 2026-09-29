// List every file in app/public for the service worker to save for offline use.
//
//   node scripts/offline_manifest.mjs      (runs before every `npm run build`)
//
// Writes app/public/offline-manifest.json: each file's path and size, in the order they
// are saved, so a phone that goes offline halfway has the numbers before the images.

import { readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const PUBLIC = fileURLToPath(new URL("../app/public/", import.meta.url));
const SKIP = new Set(["sw.js", "offline-manifest.json"]);

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

// The model and analysis data first, the rest of the data next, then documents and
// figures, and the Help pictures last: they matter least without a connection.
const rank = (path) =>
  /^\/data\/models\//.test(path) || path === "/analysis.json" ? 0
  : /\.json$/.test(path) ? 1
  : /\.(csv|md|txt|geojson|topojson)$/.test(path) ? 2
  : /^\/help\//.test(path) ? 4
  : 3;
const files = walk(PUBLIC)
  .map((p) => ({ path: "/" + relative(PUBLIC, p).split(sep).join("/"), size: statSync(p).size }))
  .filter((f) => !SKIP.has(f.path.slice(1)) && !f.path.split("/").some((s) => s.startsWith(".")))
  .sort((a, b) => rank(a.path) - rank(b.path) || a.size - b.size);

const total = files.reduce((t, f) => t + f.size, 0);
writeFileSync(join(PUBLIC, "offline-manifest.json"), JSON.stringify({ total, files }));
console.log(`offline manifest: ${files.length} files, ${(total / 1e6).toFixed(1)} MB`);
