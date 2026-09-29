"use client";

import Link from "next/link";
import type { ReactNode } from "react";

/**
 * The Help's only markup: **bold** and [a link](/path). Anything else is plain text,
 * so the help strings stay readable in the source and cannot inject HTML.
 */
const TOKEN = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;

export default function HelpText({ text }: { text: string }) {
  const parts: ReactNode[] = text.split(TOKEN).map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <b key={i} className="font-semibold text-text">{p.slice(2, -2)}</b>;
    }
    const m = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(p);
    if (m) {
      return (
        <Link key={i} href={m[2]} className="text-accent hover:underline">
          {m[1]}
        </Link>
      );
    }
    return p;
  });
  return <>{parts}</>;
}
