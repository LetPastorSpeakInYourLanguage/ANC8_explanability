"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { ArrowLeft, ArrowRight, ExternalLink } from "lucide-react";
import HelpText from "@/components/help/HelpText";
import Shot, { placedMarks, useShots } from "@/components/help/Shot";
import { Note, Panel, Screen, SectionRule, Tag } from "@/components/studio/ui";
import { Input } from "@/components/ui/input";
import {
  TERMS, TOPICS, getTerm, getTopic, helpHref, shotOf, termHref, type HelpCard, type HelpTopic as Topic,
} from "@/lib/help";

/** Scroll to the card or term the address names, and mark it briefly. */
function useAnchor() {
  const pathname = usePathname();
  useEffect(() => {
    const go = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id) return;
      const el = document.getElementById(id);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      el.classList.remove("flash");
      void el.offsetWidth;
      el.classList.add("flash");
    };
    const t = setTimeout(go, 60);
    window.addEventListener("hashchange", go);
    return () => {
      clearTimeout(t);
      window.removeEventListener("hashchange", go);
    };
  }, [pathname]);
}

export default function HelpTopic({ topicKey }: { topicKey: string }) {
  useAnchor();
  const topic = getTopic(topicKey);
  if (!topic) return <Screen><Note tone="bad">There is no Help topic called “{topicKey}”.</Note></Screen>;
  return topic.key === "terms" ? <TermsPage topic={topic} /> : <TopicPage topic={topic} />;
}

function Chips({ topic }: { topic: Topic }) {
  if (!topic.before?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-6">
      <span className="text-10.5 text-dim">New to this? Read first:</span>
      {topic.before.map((k) => {
        const t = getTopic(k);
        return t ? (
          <Link key={k} href={helpHref(k)} className="hover:no-underline">
            <Tag tone="accent">{t.label}</Tag>
          </Link>
        ) : null;
      })}
    </div>
  );
}

function TopicPage({ topic }: { topic: Topic }) {
  const shots = useShots();
  const marks = topic.callouts?.map((c) => c.mark) ?? topic.cards.map((c) => `${topic.key}.${c.id}`);
  const placed = placedMarks(shots.data, topic.key, marks);
  const i = TOPICS.findIndex((t) => t.key === topic.key);
  const prev = TOPICS[i - 1];
  const next = TOPICS[i + 1];

  return (
    <Screen>
      <Panel title={topic.screen ? "What this screen is for" : "What this page covers"}>
        <div className="px-14 py-12 flex flex-col gap-10 max-w-[820px]">
          <p className="text-12.5 leading-relaxed"><HelpText text={topic.purpose} /></p>
          <Chips topic={topic} />
          {topic.screen && (
            <Link
              href={topic.screen}
              className="self-start flex items-center gap-5 h-25 px-11 rounded-3 border border-accent bg-accent text-white text-11.5 font-medium hover:no-underline"
            >
              Open this screen <ExternalLink className="size-12" />
            </Link>
          )}
        </div>
      </Panel>

      {topic.plain?.length ? (
        <Panel title="How it works, in plain words">
          <div className="px-14 py-12 flex flex-col gap-8 max-w-[820px]">
            {topic.plain.map((t, k) => (
              <p key={k} className="text-12 leading-relaxed"><HelpText text={t} /></p>
            ))}
          </div>
        </Panel>
      ) : null}

      {placed.length > 0 && (
        <Panel
          title="The screen at a glance"
          how="A screenshot of the screen as it opens from the button above. Each number marks a panel explained further down this page."
        >
          <div className="grid gap-14 p-14 xl:grid-cols-[minmax(0,1fr)_280px]">
            <Shot id={topic.key} alt={`The ${topic.label} screen`} callouts={placed} />
            <ol className="flex flex-col gap-4 min-w-0">
              {placed.map(({ mark, n }) => {
                const c = topic.callouts?.find((x) => x.mark === mark);
                const card = topic.cards.find((x) => `${topic.key}.${x.id}` === mark);
                const text = c?.text ?? card?.title ?? mark;
                const href = c?.href ?? (card ? `#${card.id}` : undefined);
                return (
                  <li key={mark} className="flex items-start gap-8 text-11.5 leading-snug">
                    <span className="size-18 flex-none rounded-full bg-accent text-white text-10 font-semibold font-mono flex items-center justify-center">
                      {n}
                    </span>
                    {href ? (
                      <a href={href} className="text-text hover:text-accent pt-1">{text}</a>
                    ) : (
                      <span className="pt-1">{text}</span>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        </Panel>
      )}

      {topic.recipes?.length ? (
        <div>
          <SectionRule label="Get the best out of it" />
          <div className="grid gap-10 md:gap-14 lg:grid-cols-2 mt-8">
            {topic.recipes.map((r) => (
              <Panel key={r.title} title={r.title}>
                <ol className="px-14 py-10 flex flex-col gap-6">
                  {r.steps.map((s, k) => (
                    <li key={k} className="grid grid-cols-[20px_minmax(0,1fr)] gap-6 text-11.5 leading-relaxed">
                      <span className="font-mono text-10.5 text-accent font-semibold pt-1">{k + 1}</span>
                      <span><HelpText text={s} /></span>
                    </li>
                  ))}
                </ol>
              </Panel>
            ))}
          </div>
        </div>
      ) : null}

      {topic.cards.length > 0 && (
        <div className="flex flex-col gap-10 md:gap-14">
          <SectionRule label={topic.screen ? "Panel by panel" : "Step by step"} />
          {topic.cards.map((c) => (
            <CardBlock key={c.id} topic={topic} card={c} n={placed.find((p) => p.mark === `${topic.key}.${c.id}`)?.n} />
          ))}
        </div>
      )}

      {topic.faq?.length ? (
        <Panel title="Common questions">
          <div className="flex flex-col">
            {topic.faq.map((f) => (
              <div key={f.q} className="px-14 py-10 border-b border-border last:border-b-0">
                <div className="text-11.5 font-semibold">{f.q}</div>
                <div className="text-11.5 text-dim leading-relaxed mt-2"><HelpText text={f.a} /></div>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}

      <PrevNext prev={prev} next={next} />
    </Screen>
  );
}

function CardBlock({ topic, card, n }: { topic: Topic; card: HelpCard; n?: number }) {
  const shotId = shotOf(topic, card);
  const shots = useShots();
  const shot = shotId ? shots.data?.shots[shotId] : undefined;
  const hasShot = !!shot;
  // A wide, short crop (a row of tiles) reads better full width, above the text.
  const wide = !!shot && shot.w / shot.h > 3.2;
  return (
    <section id={card.id} className="scroll-mt-14 bg-panel border border-border rounded-3 min-w-0">
      <div className="flex items-center gap-8 px-14 py-8 border-b border-border min-h-36">
        {n != null && (
          <span className="size-18 flex-none rounded-full bg-accent text-white text-10 font-semibold font-mono flex items-center justify-center">
            {n}
          </span>
        )}
        <h3 className="text-12.5 font-semibold flex-1 min-w-0">{card.title}</h3>
        <a href={`#${card.id}`} title="Link to this explanation" className="text-10.5 text-faint hover:text-accent font-mono">#</a>
      </div>
      <div className={`grid ${hasShot && !wide ? "lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]" : ""}`}>
        {hasShot && (
          <div className={`p-14 border-border min-w-0 ${wide ? "border-b" : "lg:border-r"}`}>
            <Shot id={shotId!} alt={card.title} />
          </div>
        )}
        <div className="px-14 py-12 flex flex-col gap-10 min-w-0 max-w-[760px]">
          <p className="text-12 leading-relaxed"><HelpText text={card.shows} /></p>
          <div>
            <div className="text-9.5 uppercase tracking-label text-faint font-semibold mb-4">How to read it</div>
            <ul className="flex flex-col gap-5">
              {card.read.map((r, k) => (
                <li key={k} className="grid grid-cols-[10px_minmax(0,1fr)] gap-6 text-11.5 leading-relaxed">
                  <span className="text-accent pt-1">•</span>
                  <span><HelpText text={r} /></span>
                </li>
              ))}
            </ul>
          </div>
          {card.plain?.length ? (
            <div className="border-l-2 border-accent pl-10">
              <div className="text-9.5 uppercase tracking-label text-faint font-semibold mb-4">In plain words</div>
              <div className="flex flex-col gap-6">
                {card.plain.map((t, k) => (
                  <p key={k} className="text-11.5 leading-relaxed"><HelpText text={t} /></p>
                ))}
              </div>
            </div>
          ) : null}
          {card.watch && <Note tone="warn"><HelpText text={card.watch} /></Note>}
          {card.tryIt?.length ? (
            <div className="flex flex-wrap items-center gap-8">
              <span className="text-9.5 uppercase tracking-label text-faint font-semibold">Try it</span>
              {card.tryIt.map((t) => (
                <Link key={t.href} href={t.href} className="flex items-center gap-4 text-11 text-accent hover:underline">
                  {t.text} <ArrowRight className="size-11" />
                </Link>
              ))}
            </div>
          ) : null}
          {card.terms?.length ? (
            <div className="flex flex-wrap items-center gap-5">
              <span className="text-9.5 uppercase tracking-label text-faint font-semibold mr-2">Words</span>
              {card.terms.map((id) => {
                const t = getTerm(id);
                return t ? (
                  <Link key={id} href={termHref(id)} title={t.plain} className="hover:no-underline">
                    <Tag>{t.name}</Tag>
                  </Link>
                ) : null;
              })}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function PrevNext({ prev, next }: { prev?: Topic; next?: Topic }) {
  return (
    <div className="flex items-stretch gap-10">
      {prev ? (
        <Link href={helpHref(prev.key)} className="flex-1 border border-border bg-panel rounded-3 px-14 py-10 hover:bg-panel2 hover:no-underline text-text min-w-0">
          <div className="text-9.5 uppercase tracking-label text-faint font-semibold flex items-center gap-4"><ArrowLeft className="size-11" /> Previous</div>
          <div className="text-12 font-semibold mt-2 truncate">{prev.label}</div>
        </Link>
      ) : <div className="flex-1" />}
      {next ? (
        <Link href={helpHref(next.key)} className="flex-1 border border-border bg-panel rounded-3 px-14 py-10 hover:bg-panel2 hover:no-underline text-text text-right min-w-0">
          <div className="text-9.5 uppercase tracking-label text-faint font-semibold flex items-center justify-end gap-4">Next <ArrowRight className="size-11" /></div>
          <div className="text-12 font-semibold mt-2 truncate">{next.label}</div>
        </Link>
      ) : <div className="flex-1" />}
    </div>
  );
}

function TermsPage({ topic }: { topic: Topic }) {
  const [q, setQ] = useState("");
  const sorted = useMemo(() => [...TERMS].sort((a, b) => a.name.localeCompare(b.name)), []);
  const shown = sorted.filter((t) => {
    const s = q.trim().toLowerCase();
    return !s || [t.name, t.plain, t.example ?? "", ...(t.aka ?? [])].join(" ").toLowerCase().includes(s);
  });
  const letters = [...new Set(sorted.map((t) => t.name[0].toUpperCase()))];
  const i = TOPICS.findIndex((t) => t.key === topic.key);
  return (
    <Screen>
      <Panel title="What this page covers">
        <div className="px-14 py-12 flex flex-col gap-10 max-w-[820px]">
          <p className="text-12.5 leading-relaxed">{topic.purpose}</p>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a word, e.g. AUROC, bootstrap, lever…" aria-label="Find a word" className="max-w-[420px]" />
          <div className="flex flex-wrap gap-4">
            {letters.map((l) => (
              <a key={l} href={`#letter-${l}`} className="font-mono text-11 w-22 h-22 flex items-center justify-center border border-border2 rounded-2 text-dim hover:text-accent hover:no-underline">
                {l}
              </a>
            ))}
          </div>
        </div>
      </Panel>
      <Panel>
        <div className="grid md:grid-cols-2">
          {shown.map((t, k) => {
            const first = k === 0 || shown[k - 1].name[0].toUpperCase() !== t.name[0].toUpperCase();
            return (
              <div key={t.id} id={`term-${t.id}`} className="scroll-mt-14 px-14 py-10 border-b border-border md:odd:border-r min-w-0">
                {first && <span id={`letter-${t.name[0].toUpperCase()}`} className="scroll-mt-14" />}
                <div className="flex items-baseline gap-8">
                  <span className="text-12.5 font-semibold flex-1">{t.name}</span>
                  <a href={`#term-${t.id}`} className="text-10.5 text-faint hover:text-accent font-mono" title="Link to this word">#</a>
                </div>
                {t.aka?.length ? <div className="text-10 text-faint mt-1">also: {t.aka.join(" · ")}</div> : null}
                <p className="text-11.5 leading-relaxed mt-4"><HelpText text={t.plain} /></p>
                {t.example && <p className="text-11 text-dim leading-relaxed mt-4"><HelpText text={t.example} /></p>}
              </div>
            );
          })}
          {!shown.length && <p className="px-14 py-12 text-11.5 text-dim">No word matches “{q}”.</p>}
        </div>
      </Panel>
      <PrevNext prev={TOPICS[i - 1]} next={TOPICS[i + 1]} />
    </Screen>
  );
}
