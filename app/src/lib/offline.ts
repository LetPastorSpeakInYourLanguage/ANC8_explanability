"use client";

import { useSyncExternalStore } from "react";
import { allNavItems } from "@/lib/nav";
import { asset } from "@/lib/paths";

/**
 * Offline use. In a production build the service worker (public/sw.js) is registered
 * once the first screen is showing; then, when the browser is idle, it is asked to save
 * the rest of the app: every screen, the model and analysis data, then the other files,
 * the Help pictures last. Data-saver mode skips the background download (the status bar
 * then offers to start it), and screens still save themselves as they are opened.
 */

export const BUILD = process.env.NEXT_PUBLIC_BUILD ?? "";

/** A data file's address, with the build in it so a new deploy is never read from an old cache. */
export const versioned = (path: string) => (BUILD ? `${asset(path)}?v=${BUILD}` : asset(path));

export type Phase = "off" | "waiting" | "saving" | "ready" | "skipped";
type State = { online: boolean; phase: Phase; saved: number; total: number };
let state: State = { online: true, phase: "off", saved: 0, total: 0 };
const subs = new Set<() => void>();
const emit = (patch: Partial<State>) => {
  state = { ...state, ...patch };
  subs.forEach((f) => f());
};

export function useOffline(): State {
  return useSyncExternalStore(
    (f) => { subs.add(f); return () => subs.delete(f); },
    () => state,
    () => state,
  );
}

const FLAG = `anc8-offline-${BUILD}`;
const flag = (v?: "1" | null) => {
  try {
    if (v === undefined) return localStorage.getItem(FLAG);
    if (v === null) localStorage.removeItem(FLAG);
    else localStorage.setItem(FLAG, v);
  } catch {}
  return null;
};

let started = false;
let reg: ServiceWorkerRegistration | null = null;

/** Ask the worker to save the whole app now. */
export async function saveNow() {
  if (!reg) return;
  const manifest = await fetch(asset("/offline-manifest.json")).then((r) => r.json()).catch(() => null);
  if (!manifest) return;
  const screens = [...new Set(allNavItems().map((i) => asset(i.path.split("?")[0])))];
  const files = (manifest.files as { path: string }[]).map((f) => (f.path.endsWith(".json") ? versioned(f.path) : asset(f.path)));
  emit({ phase: "saving", saved: 0, total: screens.length + files.length });
  (reg.active ?? navigator.serviceWorker.controller)?.postMessage({ type: "warm", screens, files });
}

/** Drop the saved copy and load the current version from the network. */
export async function fetchCurrent() {
  flag(null);
  const sw = reg?.active ?? navigator.serviceWorker?.controller;
  if (!sw) return window.location.reload();
  await reg?.update().catch(() => {});
  const done = new Promise<void>((res) => {
    const on = (e: MessageEvent) => { if (e.data?.type === "refreshed") { navigator.serviceWorker.removeEventListener("message", on); res(); } };
    navigator.serviceWorker.addEventListener("message", on);
    setTimeout(res, 3000);
  });
  sw.postMessage({ type: "refresh" });
  await done;
  window.location.reload();
}

export function startOffline() {
  if (started || typeof window === "undefined") return;
  started = true;
  emit({ online: navigator.onLine });
  window.addEventListener("online", () => emit({ online: true }));
  window.addEventListener("offline", () => emit({ online: false }));
  if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;

  emit({ phase: flag() === "1" ? "ready" : "waiting" });
  navigator.serviceWorker.addEventListener("message", (e) => {
    const m = e.data ?? {};
    if (m.type === "warm-progress") emit({ phase: "saving", saved: m.done, total: m.total });
    if (m.type === "warm-done") {
      emit({ phase: "ready", saved: m.total, total: m.total });
      flag("1");
    }
  });

  const register = async () => {
    reg = await navigator.serviceWorker.register(`${asset("/sw.js")}?v=${BUILD}`, { scope: asset("/") || "/" });
    await navigator.serviceWorker.ready;
    reg = (await navigator.serviceWorker.getRegistration()) ?? reg;
    if (state.phase === "ready") return;
    const conn = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
    if (conn?.saveData) return emit({ phase: "skipped" });
    await saveNow();
  };

  // Only after the screen being opened has what it needs.
  const idle = (window as Window & { requestIdleCallback?: (f: () => void, o?: { timeout: number }) => void }).requestIdleCallback;
  const go = () => register().catch(() => emit({ phase: "off" }));
  const later = () => (idle ? idle(go, { timeout: 4000 }) : setTimeout(go, 2000));
  if (document.readyState === "complete") later();
  else window.addEventListener("load", later, { once: true });
}
