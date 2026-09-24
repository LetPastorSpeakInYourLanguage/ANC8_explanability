"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import { asset } from "@/lib/paths";

/**
 * Every written report, rendered from the same markdown files that live in the
 * repository, plus the figure gallery.
 *
 * The files are copied verbatim by scripts/export_app_data.py, so what a reader
 * sees here is exactly the text -- and the generated tables -- that ship in the
 * repository and the release package. Cross-references between documents and
 * figure names in the text become clickable in place.
 */

export type DocEntry = {
  key: string; title: string; audience: string; blurb: string;
  source: string; file: string;
};
export type FigureEntry = { figure: string; title: string; caption: string; file: string };
export type Documents = { documents: DocEntry[]; figures: FigureEntry[] };

const AUDIENCE_COLOUR: Record<string, string> = {
  "Ministry of Health": "#2f7d70",
  "General reader": "#4a6fa5",
  Researchers: "#7c6f9c",
  Everyone: "#8a6a3a",
  Reviewers: "#a8556b",
};

marked.setOptions({ gfm: true, breaks: false });

/**
 * Render markdown, then turn references into navigation: a code span or link
 * naming another document opens it, and a code span naming a figure opens that
 * figure. Done on the HTML string so the markdown itself stays untouched.
 */
export function render(md: string, docs: DocEntry[], figures: FigureEntry[]): string {
  // The generator's markers are HTML comments; marked keeps them, harmlessly.
  let html = marked.parse(md) as string;
  const byFile = new Map(docs.map((d) => [d.file, d.key]));
  const figs = new Set(figures.map((f) => f.figure));

  // <code>docs/PREDICTOR_VALUE.md</code> or <code>FINDINGS.md</code>
  html = html.replace(/<code>([^<]*?([A-Z_]+\.md))<\/code>/g, (m, full, file) => {
    const key = byFile.get(file);
    return key ? `<a href="#" data-doc="${key}" class="docref"><code>${full}</code></a>` : m;
  });
  // [text](../FINDINGS.md) style links
  html = html.replace(/<a href="([^"]*?([A-Z_]+\.md))"/g, (m, _href, file) => {
    const key = byFile.get(file);
    return key ? `<a href="#" data-doc="${key}" class="docref"` : m;
  });
  // figure names, with or without a code span
  html = html.replace(/<code>(fig\d{2}_[a-z0-9_]+)<\/code>/g, (m, name) =>
    figs.has(name) ? `<a href="#" data-fig="${name}" class="docref"><code>${name}</code></a>` : m);
  return html;
}

export function Lightbox({ fig, onClose }: { fig: FigureEntry; onClose: () => void }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={onClose}
      role="dialog"
      aria-label={fig.title}
    >
      <div className="card p-3 max-w-5xl w-full max-h-[92vh] overflow-auto"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <h3 className="font-semibold text-sm">{fig.title}</h3>
            <p className="label mt-1 leading-relaxed">{fig.caption}</p>
          </div>
          <button onClick={onClose} className="label text-lg px-2" aria-label="close">×</button>
        </div>
        {/* White backing: the figures are rendered on white for print. */}
        <div style={{ background: "#fff", borderRadius: 8 }} className="p-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={asset(fig.file)} alt={fig.title} className="w-full h-auto" />
        </div>
        <p className="label mt-2 text-[0.7rem]">{fig.figure}.png</p>
      </div>
    </div>
  );
}

function Gallery({ figures, onOpen }: { figures: FigureEntry[]; onOpen: (f: FigureEntry) => void }) {
  return (
    <div>
      <h2 className="text-xl font-semibold">Figures</h2>
      <p className="label mt-2 mb-5 leading-relaxed max-w-3xl">
        Every figure in the analysis, generated from the result files by{" "}
        <code>scripts/make_figures.py</code>. Click one to enlarge it.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {figures.map((f) => (
          <button key={f.figure} onClick={() => onOpen(f)}
                  className="card p-2 text-left hover:opacity-90">
            <div style={{ background: "#fff", borderRadius: 6 }} className="p-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset(f.file)} alt={f.title} loading="lazy"
                   className="w-full h-40 object-contain" />
            </div>
            <div className="text-sm font-medium mt-2 leading-snug">{f.title}</div>
            <div className="label text-[0.7rem] mt-0.5">{f.figure}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Reports({
  data, initialDoc,
}: {
  data: Documents; initialDoc?: string;
}) {
  const [active, setActive] = useState<string>(initialDoc ?? data.documents[0]?.key ?? "figures");
  const [text, setText] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [fig, setFig] = useState<FigureEntry | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (initialDoc) setActive(initialDoc);
  }, [initialDoc]);

  useEffect(() => {
    if (active === "figures") return;
    setError(null);
    fetch(asset(`/docs/${active}.md`))
      .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((t) => {
        setText(t);
        ref.current?.scrollIntoView({ block: "start", behavior: "smooth" });
      })
      .catch((e) => setError(String(e)));
  }, [active]);

  const html = useMemo(
    () => (text ? render(text, data.documents, data.figures) : ""),
    [text, data]
  );

  const onClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = (e.target as HTMLElement).closest("a[data-doc], a[data-fig]") as HTMLAnchorElement | null;
    if (!a) return;
    e.preventDefault();
    if (a.dataset.doc) setActive(a.dataset.doc);
    if (a.dataset.fig) setFig(data.figures.find((f) => f.figure === a.dataset.fig) ?? null);
  };

  const current = data.documents.find((d) => d.key === active);

  return (
    <div className="grid gap-6 lg:grid-cols-[250px_1fr]" ref={ref}>
      <nav className="lg:sticky lg:top-4 self-start">
        <p className="label mb-2">Documents</p>
        <div className="flex lg:flex-col gap-1 overflow-x-auto pb-1">
          {data.documents.map((d) => {
            const on = d.key === active;
            return (
              <button key={d.key} onClick={() => setActive(d.key)}
                      className="text-left rounded px-2.5 py-2 shrink-0"
                      style={{ background: on ? "var(--card)" : "transparent",
                               border: `1px solid ${on ? "var(--line)" : "transparent"}` }}>
                <div className="text-sm" style={{ fontWeight: on ? 600 : 400 }}>{d.title}</div>
                <div className="text-[0.66rem] mt-0.5 whitespace-nowrap"
                     style={{ color: AUDIENCE_COLOUR[d.audience] ?? "var(--muted)" }}>
                  {d.audience}
                </div>
              </button>
            );
          })}
          <button onClick={() => setActive("figures")}
                  className="text-left rounded px-2.5 py-2 shrink-0"
                  style={{ background: active === "figures" ? "var(--card)" : "transparent",
                           border: `1px solid ${active === "figures" ? "var(--line)" : "transparent"}` }}>
            <div className="text-sm" style={{ fontWeight: active === "figures" ? 600 : 400 }}>
              Figures
            </div>
            <div className="text-[0.66rem] mt-0.5 label">{data.figures.length} figures</div>
          </button>
        </div>
      </nav>

      <div className="card p-4 sm:p-7 min-w-0">
        {active === "figures" ? (
          <Gallery figures={data.figures} onOpen={setFig} />
        ) : error ? (
          <p style={{ color: "var(--warn)" }}>Could not load this document ({error}).</p>
        ) : (
          <>
            {current && (
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span className="text-[0.7rem] px-2 py-0.5 rounded"
                      style={{ background: AUDIENCE_COLOUR[current.audience] ?? "var(--muted)",
                               color: "#fff" }}>
                  for: {current.audience}
                </span>
                <span className="label text-[0.72rem]">{current.blurb}</span>
                <span className="label text-[0.72rem] ml-auto">
                  <code>{current.source}</code>
                </span>
              </div>
            )}
            <article className="doc" onClick={onClick}
                     dangerouslySetInnerHTML={{ __html: html }} />
          </>
        )}
      </div>

      {fig && <Lightbox fig={fig} onClose={() => setFig(null)} />}
    </div>
  );
}
