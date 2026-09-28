"use client";

import { useEffect, useState } from "react";
import { asset } from "@/lib/paths";

/**
 * One cache for every JSON file the studio reads from app/public. Screens ask for
 * what they need by path; a file is fetched once per page load however many
 * screens and panels read it, so moving between screens is instant after the
 * first visit.
 */

const cache = new Map<string, Promise<unknown>>();

export function loadJSON<T>(path: string): Promise<T> {
  let p = cache.get(path) as Promise<T> | undefined;
  if (!p) {
    p = fetch(asset(path)).then((r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return r.json() as Promise<T>;
    });
    // A failed fetch should be retried on the next visit, not cached as failed.
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return p;
}

export type Loaded<T> =
  | { state: "loading"; data: null; error: null }
  | { state: "ready"; data: T; error: null }
  | { state: "error"; data: null; error: string };

/** Read one file: loading → ready, or error with the reason. */
export function useJSON<T>(path: string | null): Loaded<T> {
  const [s, setS] = useState<Loaded<T>>({ state: "loading", data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    setS({ state: "loading", data: null, error: null });
    loadJSON<T>(path)
      .then((data) => live && setS({ state: "ready", data, error: null }))
      .catch((e) => live && setS({ state: "error", data: null, error: String(e?.message ?? e) }));
    return () => {
      live = false;
    };
  }, [path]);
  return s;
}
