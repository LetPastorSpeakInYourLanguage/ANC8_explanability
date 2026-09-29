/*
 * The studio's service worker: the app keeps working without a connection.
 *
 * The screen being opened always comes first, from the network when there is one. Once
 * it is on screen, the page asks this worker to save the rest of the app in the
 * background (every screen, its scripts and styles, the data, the figures and the Help
 * pictures), a few files at a time so it never competes with what is being read.
 *
 *   /_next/static/*        cache first: these files never change under one name
 *   data (…?v=<build>)     cache first: the build is part of the address
 *   screens (navigations)  network first, the saved copy when offline
 *   other files            the saved copy at once, refreshed in the background
 *   /api/*                 never cached: Predict needs the connection
 *
 * Each build has its own cache (the build id is on this file's address); the old one is
 * removed when the new build takes over.
 */

const BUILD = new URL(self.location.href).searchParams.get("v") || "dev";
const CACHE = `anc8-${BUILD}`;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith("anc8-") && key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});

const screenKey = (url) => {
  const u = new URL(url);
  return `${u.origin}${u.pathname.replace(/\/$/, "") || "/"}`;
};

async function put(req, res) {
  if (res && res.ok && res.type === "basic") {
    const cache = await caches.open(CACHE);
    await cache.put(req, res);
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  // A screen's server-component data: let it fail offline, and the router falls back
  // to loading the screen itself, which comes from the cache below.
  if (req.headers.get("RSC") === "1" || url.searchParams.has("_rsc")) return;

  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const res = await fetch(req);
        put(screenKey(req.url), res.clone());
        return res;
      } catch {
        const cache = await caches.open(CACHE);
        return (await cache.match(screenKey(req.url))) || (await cache.match(screenKey(self.location.origin + "/"))) || Response.error();
      }
    })());
    return;
  }

  const immutable = url.pathname.startsWith("/_next/static/") || url.searchParams.has("v");
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    if (hit && immutable) return hit;
    const fresh = fetch(req).then((res) => { put(req, res.clone()); return res; });
    if (hit) {
      event.waitUntil(fresh.catch(() => {}));
      return hit;
    }
    return fresh;
  })());
});

// ------------------------------------------------------------------ saving the app
let warming = null;

self.addEventListener("message", (event) => {
  const msg = event.data || {};
  if (msg.type === "warm" && !warming) {
    warming = warm(msg.screens || [], msg.files || [], event.source).finally(() => { warming = null; });
    event.waitUntil(warming);
  }
  // "Fetch current version": drop the saved copy; the page then reloads from the network
  // and saves the app again.
  if (msg.type === "refresh") {
    event.waitUntil(caches.delete(CACHE).then(() => event.source && event.source.postMessage({ type: "refreshed" })));
  }
});

async function warm(screens, files, client) {
  const cache = await caches.open(CACHE);
  // Two lanes: the screens and the scripts and styles they name go first, then the files
  // in the manifest's order (model and analysis data first, Help pictures last).
  const high = [];
  const low = [];
  const seen = new Set();
  let total = 0;
  const add = (url, kind, lane) => {
    const abs = new URL(url, self.location.origin).href;
    if (!seen.has(abs)) { seen.add(abs); lane.push({ url: abs, kind }); total++; }
  };
  screens.forEach((s) => add(s, "screen", high));
  files.forEach((f) => add(f, "file", low));

  let done = 0;
  const report = () => client && client.postMessage({ type: "warm-progress", done, total });

  async function one(item) {
    const key = item.kind === "screen" ? screenKey(item.url) : item.url;
    let res = await cache.match(key);
    if (!res) {
      try {
        res = await fetch(item.url, { credentials: "same-origin" });
        if (!res.ok) return;
        await cache.put(key, res.clone());
      } catch { return; }
    }
    // A screen's HTML names the scripts and styles it needs; a stylesheet names its fonts.
    const type = res.headers.get("content-type") || "";
    if (type.includes("text/html") || type.includes("text/css")) {
      const text = await res.text();
      for (const m of text.matchAll(/\/_next\/static\/[^"'()\s\\]+/g)) add(m[0], "file", high);
    }
  }

  async function worker() {
    for (;;) {
      const item = high.shift() || low.shift();
      if (!item) return;
      await one(item);
      done++;
      if (done % 5 === 0) report();
    }
  }
  await Promise.all([worker(), worker(), worker()]);
  report();
  if (client) client.postMessage({ type: "warm-done", total });
}
