"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Info } from "lucide-react";

/**
 * The studio's screen vocabulary, taken from the house design
 * (lab_resource_v2/components/ui.tsx, states/ and the dashboard stat tiles).
 *
 * Flush panels divided by 1px rules: no floating cards, no shadows. IBM Plex Mono for
 * every quantity, Plex Sans for language. The one addition is `how` on a Panel: the
 * "how to read this" sentence lives behind an info icon, so a chart can speak for
 * itself and the explanation is one hover away rather than a paragraph on screen.
 */

export function Screen({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`p-10 md:p-14 flex flex-col gap-10 md:gap-14 ${className}`}>{children}</div>;
}

export function Hint({ children, label = "How to read this" }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);
  return (
    <span ref={ref} className="relative inline-flex">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="text-faint hover:text-accent"
      >
        <Info className="size-12" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute right-0 top-18 z-[1100] w-[min(300px,80vw)] bg-panel border border-border2 rounded-3 px-10 py-8 text-11 leading-relaxed text-text normal-case tracking-normal font-normal"
        >
          {children}
        </span>
      )}
    </span>
  );
}

export function Panel({
  title,
  actions,
  how,
  children,
  className = "",
  bodyClassName = "",
}: {
  title?: ReactNode;
  actions?: ReactNode;
  /** One or two sentences: how to read this panel. Shown on hover of the info icon. */
  how?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={`bg-panel border border-border rounded-3 min-w-0 ${className}`}>
      {(title || actions || how) && (
        <div className="flex items-center gap-8 px-14 py-8 border-b border-border min-h-36 flex-wrap">
          {title && (
            <div className="text-11 uppercase tracking-widest text-dim font-semibold flex-1 min-w-0 truncate">
              {title}
            </div>
          )}
          {actions}
          {how && <Hint>{how}</Hint>}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

/** A small segmented control, as in the house dashboard's breakdown switch. */
export function Segmented<K extends string>({
  options,
  value,
  onChange,
  label,
  size = "sm",
}: {
  options: { key: K; label: ReactNode; title?: string }[];
  value: K;
  onChange: (k: K) => void;
  label: string;
  size?: "sm" | "md";
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap overflow-hidden rounded-2 border border-border2 flex-none">
      {options.map((o) => {
        const on = o.key === value;
        return (
          <button
            key={o.key}
            type="button"
            role="radio"
            aria-checked={on}
            title={o.title}
            onClick={() => onChange(o.key)}
            className={`${size === "sm" ? "h-22 px-8 text-9.5" : "h-24 px-10 text-10.5"} border-r border-border2 font-medium last:border-r-0 whitespace-nowrap ${
              on ? "bg-accent text-white" : "bg-panel2 text-dim hover:text-text"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

const TONE_TEXT = { good: "text-good", warn: "text-warn", bad: "text-bad", accent: "text-accent" } as const;

/** The house stat tile. Clickable tiles drill into the shared state. */
export function StatTile({
  label,
  value,
  sub,
  tone,
  active,
  onClick,
  children,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: keyof typeof TONE_TEXT;
  active?: boolean;
  onClick?: () => void;
  children?: ReactNode;
}) {
  const content = (
    <>
      <div className="text-9.5 font-semibold uppercase tracking-label text-faint">{label}</div>
      <div className={`mt-4 font-mono text-21 font-semibold ${tone ? TONE_TEXT[tone] : ""}`}>{value}</div>
      {sub && <div className="mt-3 text-10 text-dim leading-snug">{sub}</div>}
      {children}
    </>
  );
  const className = `rounded-3 border bg-panel px-14 py-12 text-left min-w-0 ${
    active ? "border-accent bg-soft" : "border-border"
  } ${onClick ? "transition-colors hover:border-accent hover:bg-panel2" : ""}`;
  return onClick ? (
    <button type="button" onClick={onClick} className={className} aria-pressed={active}>
      {content}
    </button>
  ) : (
    <div className={className}>{content}</div>
  );
}

/** A status/attribute token. Always mono: it is a value, not prose. */
export function Tag({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad" | "accent" | "cross";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-panel3 text-dim border-border2",
    good: "bg-goodbg text-good border-good",
    warn: "bg-warnbg text-warn border-warn",
    bad: "bg-badbg text-bad border-bad",
    accent: "bg-soft text-accent border-accent",
    cross: "bg-crossbg text-cross border-cross",
  };
  return (
    <span className={`inline-block border rounded-2 px-6 py-1 text-9.5 font-mono whitespace-nowrap ${tones[tone]}`}>
      {children}
    </span>
  );
}

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  /** Right-align and use mono: for counts, rates and identifiers. */
  mono?: boolean;
  width?: string;
}

export function Table<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isActive,
  minWidth = 560,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  isActive?: (row: T) => boolean;
  minWidth?: number;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse" style={{ minWidth }}>
        <thead>
          <tr className="border-b border-border">
            {columns.map((c) => (
              <th
                key={c.header}
                style={{ width: c.width }}
                className={`text-9.5 uppercase tracking-label text-faint font-semibold px-12 py-7 ${
                  c.mono ? "text-right" : "text-left"
                }`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-border last:border-b-0 ${onRowClick ? "cursor-pointer hover:bg-panel2" : ""} ${
                isActive?.(row) ? "bg-sel" : ""
              }`}
            >
              {columns.map((c) => (
                <td
                  key={c.header}
                  className={`px-12 py-6 text-11.5 align-middle ${c.mono ? "text-right font-mono text-11" : ""}`}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Panel loading: keeps the frame and greys the rows. Never a full-page spinner. */
export function PanelLoading({ rows = 5 }: { rows?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-10 px-14 py-8 border-b border-border last:border-b-0">
          <div className="h-10 bg-panel3 rounded-2 flex-1" style={{ opacity: 1 - i * 0.12 }} />
          <div className="h-10 w-64 bg-panel3 rounded-2" style={{ opacity: 1 - i * 0.12 }} />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, body, action }: {
  title: string;
  body?: ReactNode;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="px-14 py-16 max-w-[560px]">
      <div className="text-13 font-semibold">{title}</div>
      {body && <div className="text-11.5 text-dim leading-loose mt-3">{body}</div>}
      {action && (
        <button
          onClick={action.onClick}
          className="border border-accent bg-accent text-white h-25 px-11 rounded-3 text-11.5 font-medium mt-10"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export function InlineError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="px-14 py-12">
      <div className="flex gap-10">
        <div className="w-3 bg-bad rounded-2 flex-none" />
        <div className="min-w-0">
          <div className="text-12 font-semibold text-bad">Could not load this panel</div>
          <div className="text-11 text-dim leading-loose mt-2">{message}</div>
          {onRetry && (
            <button onClick={onRetry} className="border border-border2 bg-panel h-23 px-9 rounded-3 text-11 text-dim mt-8">
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/** A caveat that belongs next to a number: coloured bar, short sentence. */
export function Note({ children, tone = "warn" }: { children: ReactNode; tone?: "warn" | "accent" | "bad" | "good" }) {
  const bar = { warn: "bg-warn", accent: "bg-accent", bad: "bg-bad", good: "bg-good" }[tone];
  return (
    <div className="flex gap-10 text-11 text-dim leading-relaxed">
      <div className={`w-3 rounded-2 flex-none ${bar}`} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function SectionRule({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="pt-4 pb-2 flex items-center gap-10">
      <div className="text-11 font-semibold uppercase tracking-widest text-dim whitespace-nowrap">{label}</div>
      <div className="flex-1 border-t border-border" />
      {children}
    </div>
  );
}

/** The house placeholder for a screen that a later milestone builds. */
export function ComingSoon({ title, note }: { title: string; note?: string }) {
  return (
    <div className="p-14 md:p-24">
      <div className="border border-border rounded-3 bg-panel2 px-16 py-20 max-w-[560px]">
        <div className="text-13 font-semibold">{title}</div>
        <div className="text-11.5 text-dim mt-6 leading-relaxed">
          {note ?? "This screen is being built in a later milestone of the studio."}
        </div>
      </div>
    </div>
  );
}
