"use client";

import { useJSON } from "@/lib/data";
import { asset } from "@/lib/paths";

/**
 * A screenshot of the studio, made by scripts/capture_help_shots.mjs, with optional
 * numbered callouts. The script records where every panel sat in each full-screen
 * shot (index.json), so a callout follows its panel whenever the shots are re-made.
 */

export interface ShotIndex {
  base: string;
  shots: Record<string, { w: number; h: number; marks?: Record<string, [number, number, number, number]> }>;
}

export function useShots() {
  return useJSON<ShotIndex>("/help/shots/index.json");
}

export default function Shot({
  id,
  alt,
  callouts = [],
  className = "",
}: {
  id: string;
  alt: string;
  /** Marks to number, in order: a help id or a named mark from index.json. */
  callouts?: { mark: string; n: number }[];
  className?: string;
}) {
  const idx = useShots();
  const s = idx.data?.shots[id];
  if (idx.state === "loading") return <div className={`bg-panel2 border border-border rounded-2 aspect-[16/10] ${className}`} />;
  if (!s) return null;
  return (
    <div
      className={`relative border border-border rounded-2 overflow-hidden bg-panel2 ${className}`}
      style={{ maxWidth: s.w + 2 }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={asset(`/help/shots/${id}.jpg`)}
        alt={alt}
        width={s.w}
        height={s.h}
        loading="lazy"
        className="block w-full h-auto"
      />
      {callouts.map(({ mark, n }) => {
        const b = s.marks?.[mark];
        if (!b) return null;
        return (
          <span
            key={mark}
            aria-hidden="true"
            className="absolute -translate-x-1/2 -translate-y-1/2 size-18 rounded-full bg-accent text-white text-10 font-semibold font-mono flex items-center justify-center border-2 border-white"
            style={{ left: `${((b[0] + 4) / s.w) * 100}%`, top: `${((b[1] + 4) / s.h) * 100}%` }}
          >
            {n}
          </span>
        );
      })}
    </div>
  );
}

/** Which of a topic's marks are in its full shot, numbered in order. */
export function placedMarks(idx: ShotIndex | null, shotId: string, marks: string[]): { mark: string; n: number }[] {
  const have = idx?.shots[shotId]?.marks ?? {};
  return marks.filter((m) => have[m]).map((mark, i) => ({ mark, n: i + 1 }));
}
