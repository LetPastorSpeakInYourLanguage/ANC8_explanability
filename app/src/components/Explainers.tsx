"use client";

import { useMemo, useState } from "react";

/**
 * Three small hands-on explainers for readers without a statistics
 * background. They use 100 simulated women, 19 of whom reach ANC8+ (the
 * national rate), scored by an imaginary model about as good as ours
 * (AUROC near 0.78). The numbers are illustrative, not survey data, and the
 * page says so.
 */

type Woman = { id: number; attained: boolean; score: number };

/** Small deterministic generator, so every reader sees the same 100 women. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(r: () => number) {
  const u = Math.max(r(), 1e-9);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r());
}

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

function makeWomen(): Woman[] {
  const r = rng(2026);
  const out: Woman[] = [];
  for (let i = 0; i < 100; i++) {
    const attained = i < 19;
    // Attainers sit higher on the log-odds scale; the overlap is what keeps
    // the ranking imperfect.
    const z = (attained ? -0.7 : -1.6) + normal(r);
    out.push({ id: i, attained, score: sigmoid(z) });
  }
  return out.sort((a, b) => b.score - a.score);
}

function metrics(women: Woman[], threshold: number) {
  const flagged = women.filter((w) => w.score >= threshold);
  const tp = flagged.filter((w) => w.attained).length;
  const pos = women.filter((w) => w.attained).length;
  const tn = women.filter((w) => !w.attained && w.score < threshold).length;
  return {
    flagged: flagged.length,
    tp,
    accuracy: (tp + tn) / women.length,
    precision: flagged.length ? tp / flagged.length : null,
    recall: tp / pos,
  };
}

function averagePrecision(women: Woman[]) {
  let hits = 0;
  let sum = 0;
  women.forEach((w, i) => {
    if (w.attained) {
      hits += 1;
      sum += hits / (i + 1);
    }
  });
  return sum / hits;
}

function auroc(women: Woman[]) {
  const pos = women.filter((w) => w.attained);
  const neg = women.filter((w) => !w.attained);
  let wins = 0;
  for (const p of pos) for (const n of neg) wins += p.score > n.score ? 1 : p.score === n.score ? 0.5 : 0;
  return wins / (pos.length * neg.length);
}

const pc = (v: number | null) => (v == null ? "—" : `${Math.round(v * 100)}%`);

function Box({ title, children, note }: { title: string; children: React.ReactNode; note: React.ReactNode }) {
  return (
    <div className="card p-4 sm:p-5">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-3">{children}</div>
      <p className="label mt-3 leading-relaxed">{note}</p>
    </div>
  );
}

function Readout({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg px-3 py-2" style={{ border: "1px solid var(--line)" }}>
      <div className="label text-[0.7rem]">{label}</div>
      <div className="text-lg font-semibold tabular" style={{ color: tone ?? "var(--fg)" }}>
        {value}
      </div>
    </div>
  );
}

/** 1. Why accuracy misleads, and what precision and recall measure. */
function Threshold({ women }: { women: Woman[] }) {
  const [t, setT] = useState(0.3);
  const m = metrics(women, t);
  const ap = averagePrecision(women);
  return (
    <Box
      title="1 · Why we don't use accuracy"
      note={
        <>
          Each dot is one woman, sorted by the model&apos;s score (highest first,
          reading across). Filled dots reached eight contacts. A ring means the
          model flags her at the chosen cut-off. Drag the slider to the far
          right, so no one is flagged: accuracy stays at 81% even though the
          model finds nobody. That is why this analysis reports AP ({ap.toFixed(2)} for
          these 100 women, against a floor of 0.19) and AUROC instead.
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-[auto_1fr] items-start">
        <svg viewBox="0 0 200 200" className="w-full max-w-[220px]" role="img"
             aria-label="100 women sorted by score">
          {women.map((w, i) => {
            const x = 10 + (i % 10) * 20;
            const y = 10 + Math.floor(i / 10) * 20;
            const flagged = w.score >= t;
            return (
              <g key={w.id}>
                {flagged && <circle cx={x} cy={y} r={8.5} fill="none" stroke="var(--warn)" strokeWidth={1.6} />}
                <circle cx={x} cy={y} r={5.5}
                        fill={w.attained ? "var(--accent)" : "transparent"}
                        stroke={w.attained ? "var(--accent)" : "var(--muted)"} strokeWidth={1.2} />
              </g>
            );
          })}
        </svg>
        <div>
          <label className="label block">
            Flag women whose score is at least <b className="tabular">{Math.round(t * 100)}%</b>
          </label>
          <input type="range" min={0} max={1} step={0.01} value={t}
                 onChange={(e) => setT(Number(e.target.value))}
                 className="w-full mt-2" aria-label="cut-off" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
            <Readout label="flagged" value={`${m.flagged} of 100`} />
            <Readout label="accuracy" value={pc(m.accuracy)} tone="var(--muted)" />
            <Readout label="precision" value={pc(m.precision)} tone="var(--accent)" />
            <Readout label="recall" value={pc(m.recall)} tone="var(--accent)" />
          </div>
          <p className="label mt-3 leading-relaxed">
            <b>Precision</b>: of the {m.flagged} flagged, {m.tp} really reached eight.{" "}
            <b>Recall</b>: of the 19 who reached eight, the model found {m.tp}.
            Flagging more women raises recall and usually lowers precision.
          </p>
        </div>
      </div>
    </Box>
  );
}

/** 2. AUROC as "pick a pair: did the model rank them right?" */
function Pairs({ women }: { women: Woman[] }) {
  const pos = useMemo(() => women.filter((w) => w.attained), [women]);
  const neg = useMemo(() => women.filter((w) => !w.attained), [women]);
  const exact = useMemo(() => auroc(women), [women]);
  const [draws, setDraws] = useState<{ p: Woman; n: Woman }[]>([]);
  const [r] = useState(() => rng(7));

  const draw = (k: number) => {
    const next = [...draws];
    for (let i = 0; i < k; i++) {
      next.push({ p: pos[Math.floor(r() * pos.length)], n: neg[Math.floor(r() * neg.length)] });
    }
    setDraws(next);
  };
  const right = draws.filter((d) => d.p.score > d.n.score).length;
  const last = draws[draws.length - 1];

  return (
    <Box
      title="2 · What AUROC measures"
      note={
        <>
          AUROC is simply the share of such pairs the model gets right. Draw
          enough pairs and the running share settles on the exact value for
          these women, {exact.toFixed(2)}. A coin flip would settle on 0.50. Our
          real models score 0.76 to 0.83. Because every pair has one woman of
          each kind, AUROC does not depend on how common the outcome is, which is
          why it is used to compare ANC1+, ANC4+ and ANC8+.
        </>
      }
    >
      <p className="label leading-relaxed">
        Pick one woman who reached eight contacts and one who did not, at random.
        Did the model give the first woman the higher score?
      </p>
      <div className="flex flex-wrap gap-2 mt-3">
        <button onClick={() => draw(1)} className="rounded px-3 py-1.5 text-sm"
                style={{ background: "var(--accent)", color: "#fff" }}>Draw a pair</button>
        <button onClick={() => draw(100)} className="rounded px-3 py-1.5 text-sm"
                style={{ border: "1px solid var(--line)" }}>Draw 100 pairs</button>
        {draws.length > 0 && (
          <button onClick={() => setDraws([])} className="label px-2">reset</button>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
        <Readout label="reached eight" value={last ? pc(last.p.score) : "—"} tone="var(--accent)" />
        <Readout label="did not" value={last ? pc(last.n.score) : "—"} tone="var(--muted)" />
        <Readout label="this pair"
                 value={last ? (last.p.score > last.n.score ? "ranked right" : "ranked wrong") : "—"}
                 tone={last ? (last.p.score > last.n.score ? "var(--accent)" : "var(--warn)") : undefined} />
        <Readout label={`right so far (${draws.length} pairs)`}
                 value={draws.length ? (right / draws.length).toFixed(2) : "—"} />
      </div>
    </Box>
  );
}

/** 3. Calibration: can the score be read as a rate? */
function Calibration() {
  const [mode, setMode] = useState<"good" | "over">("good");
  const bins = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65];
  // Overconfident: predictions are more extreme than reality (slope ~0.6).
  const observed = (p: number) => {
    if (mode === "good") return p;
    const logit = Math.log(p / (1 - p));
    return sigmoid(-0.6 + 0.6 * (logit + 1));
  };
  const X = (v: number) => 30 + v * 240;
  const Y = (v: number) => 190 - v * 240;
  return (
    <Box
      title="3 · Calibration: can the score be read as a rate?"
      note={
        <>
          Women are grouped by their predicted chance. Each dot shows a
          group&apos;s prediction (across) against the share who really reached
          eight contacts (up). On the dashed diagonal, &ldquo;30%&rdquo; means 30 in
          100. An overconfident model&apos;s dots flatten away from the diagonal:
          it says 60% where the truth is nearer 40%. Its calibration slope is
          below 1. Our shipped model has a slope of 0.99 after correction.
        </>
      }
    >
      <div className="flex gap-2 mb-2">
        {(["good", "over"] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} className="rounded px-3 py-1.5 text-sm"
                  style={mode === m
                    ? { background: "var(--accent)", color: "#fff" }
                    : { border: "1px solid var(--line)" }}>
            {m === "good" ? "Well calibrated" : "Overconfident"}
          </button>
        ))}
      </div>
      <svg viewBox="0 0 290 215" className="w-full max-w-[360px]" role="img"
           aria-label="calibration example">
        <line x1={X(0)} y1={Y(0)} x2={X(0.7)} y2={Y(0.7)} stroke="var(--muted)" strokeDasharray="4 4" />
        <line x1={X(0)} y1={Y(0)} x2={X(0.7)} y2={Y(0)} stroke="var(--line)" />
        <line x1={X(0)} y1={Y(0)} x2={X(0)} y2={Y(0.7)} stroke="var(--line)" />
        {[0, 0.2, 0.4, 0.6].map((v) => (
          <g key={v}>
            <text x={X(v)} y={Y(0) + 13} fontSize={9} textAnchor="middle" fill="var(--muted)">{v * 100}%</text>
            <text x={X(0) - 4} y={Y(v) + 3} fontSize={9} textAnchor="end" fill="var(--muted)">{v * 100}%</text>
          </g>
        ))}
        <polyline fill="none" stroke="var(--accent)" strokeWidth={2}
                  points={bins.map((b) => `${X(b)},${Y(observed(b))}`).join(" ")} />
        {bins.map((b) => (
          <circle key={b} cx={X(b)} cy={Y(observed(b))} r={4} fill="var(--accent)" />
        ))}
        <text x={X(0.35)} y={212} fontSize={9.5} textAnchor="middle" fill="var(--muted)">predicted chance</text>
      </svg>
    </Box>
  );
}

export default function Explainers() {
  const women = useMemo(makeWomen, []);
  return (
    <div className="grid gap-4">
      <p className="label leading-relaxed max-w-3xl">
        Try these before reading the terms. They use 100 imaginary women, 19 of
        whom reach eight contacts (the national rate), scored by an imaginary
        model about as good as the real ones. The numbers here are
        illustrations, not survey results.
      </p>
      <Threshold women={women} />
      <Pairs women={women} />
      <Calibration />
    </div>
  );
}
