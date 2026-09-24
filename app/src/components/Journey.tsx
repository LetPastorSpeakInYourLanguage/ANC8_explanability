"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Explainers from "@/components/Explainers";
import { Lightbox, render, type Documents, type FigureEntry } from "@/components/Reports";
import { asset } from "@/lib/paths";

/**
 * "Analysis record": every analysis in the study, in reading order, every term
 * in plain language, and a reading guide for every figure.
 *
 * The content is parsed from docs/ANALYSIS_RECORD.md and docs/GLOSSARY.md by
 * scripts/export_app_data.py, so this view and the documents in Reports can
 * never say different things.
 */

type Entry = {
  id: string; title: string; kind: string;
  figures: string[]; terms: string[];
  question: string; did: string; tested: string; found: string; changed: string; source: string;
};
type Phase = { id: string; title: string; intro: string; entries: Entry[] };
type Term = { id: string; name: string; aka: string[]; plain: string; here?: string; good?: string };
type Group = { title: string; intro: string; terms: Term[] };
type Guide = { shows: string; read: string; takeaway: string };
export type JourneyData = {
  intro: string;
  phases: Phase[];
  glossary: { start: string; groups: Group[] };
  figures: Record<string, Guide>;
};

type View = "record" | "terms" | "figures";

/** "record" | "terms" | "term-ap" | "figures" | "fig-fig05_calibration" */
function parseSub(sub?: string): { view: View; target?: string } {
  if (!sub) return { view: "record" };
  if (sub.startsWith("term-")) return { view: "terms", target: sub.slice(5) };
  if (sub.startsWith("fig-")) return { view: "figures", target: sub.slice(4) };
  if (sub === "terms" || sub === "figures") return { view: sub };
  return { view: "record" };
}

function Md({ text, docs, onDoc, onFig, className = "" }: {
  text: string; docs: Documents | null;
  onDoc: (key: string) => void; onFig: (name: string) => void; className?: string;
}) {
  const html = useMemo(
    () => render(text, docs?.documents ?? [], docs?.figures ?? []),
    [text, docs]
  );
  return (
    <div
      className={`doc doc-compact ${className}`}
      onClick={(e) => {
        const a = (e.target as HTMLElement).closest("a[data-doc], a[data-fig]") as HTMLAnchorElement | null;
        if (!a) return;
        e.preventDefault();
        if (a.dataset.doc) onDoc(a.dataset.doc);
        if (a.dataset.fig) onFig(a.dataset.fig);
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function Chip({ children, onClick, title, tone }: {
  children: React.ReactNode; onClick: () => void; title?: string; tone?: string;
}) {
  return (
    <button onClick={onClick} title={title}
            className="text-[0.72rem] rounded-full px-2.5 py-0.5 whitespace-nowrap hover:opacity-80"
            style={{ border: `1px solid ${tone ?? "var(--line)"}`, color: tone ?? "var(--fg)" }}>
      {children}
    </button>
  );
}

export default function Journey({
  data, docs, sub, onNavigate,
}: {
  data: JourneyData;
  docs: Documents | null;
  sub?: string;
  onNavigate: (tab: string, doc?: string) => void;
}) {
  const { view, target } = parseSub(sub);
  const [fig, setFig] = useState<FigureEntry | null>(null);
  const [phase, setPhase] = useState<string>("all");
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [allOpen, setAllOpen] = useState(false);
  const [query, setQuery] = useState("");
  const topRef = useRef<HTMLDivElement>(null);

  const terms = useMemo(() => {
    const m = new Map<string, Term>();
    data.glossary.groups.forEach((g) => g.terms.forEach((t) => m.set(t.id, t)));
    return m;
  }, [data]);
  const figures = useMemo(
    () => new Map((docs?.figures ?? []).map((f) => [f.figure, f])),
    [docs]
  );

  const go = (s: string) => onNavigate("record", s);
  const openFig = (name: string) => {
    const f = figures.get(name);
    if (f) setFig(f);
  };
  const openDoc = (key: string) => onNavigate("reports", key);

  // Jump to a term or figure named in the address, and mark it briefly.
  useEffect(() => {
    if (!target) return;
    const el = document.getElementById(`${view === "terms" ? "term" : "fig"}-${target}`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("flash");
    const t = setTimeout(() => el.classList.remove("flash"), 1800);
    return () => clearTimeout(t);
  }, [view, target]);

  const all = data.phases.flatMap((p) => p.entries);
  const nTerms = data.glossary.groups.reduce((n, g) => n + g.terms.length, 0);

  const md = (text: string, className?: string) => (
    <Md text={text} docs={docs} onDoc={openDoc} onFig={openFig} className={className} />
  );

  return (
    <div ref={topRef}>
      <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div>
          <h2 className="text-xl font-semibold">Analysis record</h2>
          <p className="label mt-1 max-w-3xl leading-relaxed">
            Every analysis in the study: the question, how it was tested and
            what it found, and what every term and chart means. Written for
            readers without a statistics background.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg p-1" style={{ border: "1px solid var(--line)" }}>
          {([
            ["record", "The analyses"],
            ["terms", "Terms explained"],
            ["figures", "Reading the figures"],
          ] as [View, string][]).map(([v, label]) => (
            <button key={v} onClick={() => go(v)}
                    className="px-3 py-1.5 text-sm rounded-md"
                    style={view === v
                      ? { background: "var(--accent)", color: "#fff", fontWeight: 600 }
                      : { color: "var(--muted)" }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === "record" && (
        <div>
          <div className="grid gap-3 sm:grid-cols-4 mb-5">
            {[
              [String(data.phases.length), "parts of the study"],
              [String(all.length), "analyses, each with how it was tested"],
              [String(nTerms), "terms explained in plain language"],
              [String(Object.keys(data.figures).length), "figures, each with a reading guide"],
            ].map(([n, l]) => (
              <div key={l} className="card p-3">
                <div className="text-2xl font-semibold tabular" style={{ color: "var(--accent)" }}>{n}</div>
                <div className="label mt-1 leading-snug">{l}</div>
              </div>
            ))}
          </div>

          <div className="card p-4 sm:p-5 mb-5">
            {md(data.intro)}
            <p className="label mt-2">
              New to the terms? Start with{" "}
              <button className="underline" onClick={() => go("terms")}>Terms explained</button>:
              it builds AP, AUROC and calibration from one example of 100 women.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="label mr-1">Show</span>
            <Chip onClick={() => setPhase("all")} tone={phase === "all" ? "var(--accent)" : undefined}>
              All parts
            </Chip>
            {data.phases.map((p, i) => (
              <Chip key={p.id} onClick={() => setPhase(p.id)}
                    tone={phase === p.id ? "var(--accent)" : undefined}>
                {i + 1}. {p.title}
              </Chip>
            ))}
            <button className="label underline ml-auto" onClick={() => {
              setAllOpen(!allOpen); setOpen({});
            }}>
              {allOpen ? "collapse all" : "expand all"}
            </button>
          </div>

          <ol className="relative" style={{ borderLeft: "2px solid var(--line)", marginLeft: 8 }}>
            {data.phases.filter((p) => phase === "all" || p.id === phase).map((p) => {
              const idx = data.phases.indexOf(p);
              const entries = p.entries;
              if (!entries.length) return null;
              return (
                <li key={p.id} className="mb-8 pl-6">
                  <div className="-ml-[2.4rem] flex items-center gap-3 mb-3">
                    <span className="rounded-full w-7 h-7 flex items-center justify-center text-xs font-semibold"
                          style={{ background: "var(--accent)", color: "#fff" }}>{idx + 1}</span>
                    <div>
                      <h3 className="font-semibold leading-tight">{p.title}</h3>
                    </div>
                  </div>
                  {p.intro && (
                    <div className="mb-4 max-w-3xl">{md(p.intro, "label")}</div>
                  )}
                  <div className="grid gap-3">
                    {entries.map((e) => {
                      const isOpen = allOpen ? open[e.id] !== false : !!open[e.id];
                      return (
                        <article key={e.id} className="card p-4 relative">
                          <span className="absolute -left-[1.95rem] top-5 w-3 h-3 rounded-full"
                                style={{ background: "var(--card)", border: "2px solid var(--accent)" }} />
                          <h4 className="font-semibold">{e.title}</h4>
                          <div className="mt-2 text-sm">
                            <span className="label">Question · </span>{e.question}
                          </div>
                          <div className="mt-3 rounded-lg p-3" style={{ background: "var(--bg)" }}>
                            <div className="label text-[0.7rem] uppercase tracking-wide mb-1">What we found</div>
                            {md(e.found)}
                          </div>

                          {isOpen && (
                            <div className="grid gap-4 md:grid-cols-2 mt-4">
                              {([
                                ["What we did", e.did],
                                ["How we tested it", e.tested],
                                ["What changed because of it", e.changed],
                                ["Source", e.source],
                              ] as [string, string][]).map(([h, t]) => (
                                <div key={h}>
                                  <div className="label text-[0.7rem] uppercase tracking-wide mb-1">{h}</div>
                                  {md(t)}
                                </div>
                              ))}
                            </div>
                          )}

                          <div className="flex flex-wrap items-center gap-1.5 mt-3">
                            <button className="text-[0.75rem] mr-2 underline" style={{ color: "var(--accent)" }}
                                    onClick={() => setOpen({ ...open, [e.id]: !isOpen })}>
                              {isOpen ? "hide details" : "how it was done"}
                            </button>
                            {e.figures.map((f) => (
                              <Chip key={f} onClick={() => openFig(f)}
                                    title={figures.get(f)?.title}>
                                ▦ {figures.get(f)?.title ?? f}
                              </Chip>
                            ))}
                            {e.terms.map((t) => {
                              const term = terms.get(t);
                              return (
                                <Chip key={t} onClick={() => go(`term-${t}`)}
                                      title={term ? term.plain.replace(/\*\*/g, "") : t}
                                      tone="var(--set21)">
                                  ? {term?.name ?? t}
                                </Chip>
                              );
                            })}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {view === "terms" && (
        <div className="grid gap-6">
          <section className="card p-4 sm:p-6">
            <h3 className="text-lg font-semibold">Start here: 100 women</h3>
            <div className="mt-2 max-w-3xl">{md(data.glossary.start)}</div>
          </section>

          <Explainers />

          <div className="flex flex-wrap items-center gap-3">
            <input value={query} onChange={(e) => setQuery(e.target.value)}
                   placeholder="Search terms (e.g. AUROC, bootstrap, tier)…"
                   className="rounded-lg px-3 py-2 text-sm w-full sm:w-96"
                   style={{ border: "1px solid var(--line)", background: "var(--card)", color: "var(--fg)" }} />
            <div className="flex flex-wrap gap-1.5">
              {data.glossary.groups.map((g) => (
                <a key={g.title} href={`#record/terms`}
                   onClick={(e) => {
                     e.preventDefault();
                     document.getElementById(`group-${g.title}`)?.scrollIntoView({ behavior: "smooth" });
                   }}
                   className="label text-[0.72rem] underline">{g.title}</a>
              ))}
            </div>
          </div>

          {data.glossary.groups.map((g) => {
            const q = query.trim().toLowerCase();
            const shown = g.terms.filter((t) => !q ||
              [t.name, t.plain, t.here ?? "", ...t.aka].join(" ").toLowerCase().includes(q));
            if (!shown.length) return null;
            return (
              <section key={g.title} id={`group-${g.title}`}>
                <h3 className="font-semibold mb-3">{g.title}</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  {shown.map((t) => (
                    <div key={t.id} id={`term-${t.id}`} className="card p-4 scroll-mt-24">
                      <div className="flex items-baseline justify-between gap-2">
                        <h4 className="font-semibold">{t.name}</h4>
                        <button className="label text-[0.68rem]" title="copy a link to this term"
                                onClick={() => go(`term-${t.id}`)}>#</button>
                      </div>
                      {t.aka.length > 0 && (
                        <div className="label text-[0.7rem] mt-0.5">also: {t.aka.join(" · ")}</div>
                      )}
                      <div className="mt-2">{md(t.plain)}</div>
                      {t.here && (
                        <div className="mt-2">
                          <div className="label text-[0.7rem] uppercase tracking-wide">In this analysis</div>
                          {md(t.here)}
                        </div>
                      )}
                      {t.good && (
                        <div className="mt-2 rounded-md px-3 py-2" style={{ background: "var(--bg)" }}>
                          <div className="label text-[0.7rem] uppercase tracking-wide">A good value looks like</div>
                          {md(t.good)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {view === "figures" && (
        <div className="grid gap-4">
          <p className="label max-w-3xl leading-relaxed">
            Every figure in the analysis, with what it shows, how to read it, and
            the one thing to take from it. Click a figure to enlarge it.
          </p>
          {(docs?.figures ?? []).map((f) => {
            const g = data.figures[f.figure];
            if (!g) return null;
            return (
              <article key={f.figure} id={`fig-${f.figure}`}
                       className="card p-4 grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] scroll-mt-24">
                <button onClick={() => setFig(f)} className="text-left">
                  <div style={{ background: "#fff", borderRadius: 8 }} className="p-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={asset(f.file)} alt={f.title} loading="lazy" className="w-full h-auto" />
                  </div>
                  <div className="label text-[0.68rem] mt-1">{f.figure}</div>
                </button>
                <div className="min-w-0">
                  <h3 className="font-semibold">{f.title}</h3>
                  <div className="mt-2">
                    <div className="label text-[0.7rem] uppercase tracking-wide">What it shows</div>
                    {md(g.shows)}
                  </div>
                  <div className="mt-2">
                    <div className="label text-[0.7rem] uppercase tracking-wide">How to read it</div>
                    {md(g.read)}
                  </div>
                  <div className="mt-3 rounded-md px-3 py-2"
                       style={{ background: "var(--bg)", borderLeft: "3px solid var(--accent)" }}>
                    <div className="label text-[0.7rem] uppercase tracking-wide">Takeaway</div>
                    {md(g.takeaway)}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {fig && <Lightbox fig={fig} onClose={() => setFig(null)} />}
    </div>
  );
}
