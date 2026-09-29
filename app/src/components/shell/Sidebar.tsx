"use client";

import { usePathname, useRouter } from "next/navigation";
import { X } from "lucide-react";
import { MODES, NAV, itemForPath, modeForPath } from "@/lib/nav";
import { COHORTS, useStudio } from "@/lib/studio";

/**
 * The house sidebar. The scope block says what everything on screen is about: the
 * whole country or one region, and which cohort of women. Both are part of the shared
 * URL state, so every screen follows them.
 */
export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const studio = useStudio();
  const mode = modeForPath(pathname);
  const activeKey = itemForPath(pathname)?.key;
  const cohort = COHORTS.find((c) => c.key === studio.cohort) ?? COHORTS[0];

  const go = (path: string) => {
    router.push(studio.href(path));
    onNavigate?.();
  };

  return (
    <div className="bg-panel2 md:border-r border-border flex flex-col min-h-0 h-full overflow-hidden">
      <div className="md:hidden border-b border-border p-8 flex gap-4 flex-none">
        {MODES.map((m) => {
          const on = mode === m.key;
          return (
            <button
              key={m.key}
              onClick={() => go(NAV[m.key][0].items[0].path)}
              style={{
                background: on ? "var(--accent)" : "var(--panel)",
                color: on ? "#fff" : "var(--dim)",
                borderColor: on ? "var(--accent)" : "var(--border2)",
              }}
              className="flex-1 border h-30 rounded-3 text-11.5 font-medium"
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div data-mark="scope" className="px-12 pt-9 pb-9 border-b border-border flex-none">
        <div className="text-9.5 uppercase tracking-label text-faint font-semibold">Scope</div>
        <div className="flex items-center gap-6 mt-4">
          <div className="w-6 h-6 bg-accent rounded-1 flex-none" />
          <div className="text-12 font-semibold leading-snug flex-1 min-w-0 truncate">
            {studio.region || "Ethiopia"}
          </div>
          {studio.region && (
            <button
              onClick={() => studio.set({ region: "" })}
              title="Back to the whole country"
              aria-label="Clear region"
              className="text-faint hover:text-text flex-none"
            >
              <X className="size-12" />
            </button>
          )}
        </div>
        <div className="text-10.5 text-dim mt-2 font-mono">
          {studio.region ? "one of 14 regions" : "14 regions"} · {cohort.n.toLocaleString()} women
        </div>

        <div className="text-9.5 uppercase tracking-label text-faint font-semibold mt-10 mb-4">Cohort</div>
        <div data-mark="cohort" className="flex overflow-hidden rounded-2 border border-border2" role="radiogroup" aria-label="Cohort">
          {COHORTS.map((c) => {
            const on = c.key === studio.cohort;
            return (
              <button
                key={c.key}
                role="radio"
                aria-checked={on}
                title={c.blurb}
                onClick={() => studio.set({ cohort: c.key })}
                className={`flex-1 h-22 border-r border-border2 last:border-r-0 text-10 font-medium ${
                  on ? "bg-accent text-white" : "bg-panel text-dim hover:text-text"
                }`}
              >
                {c.short}
              </button>
            );
          })}
        </div>
        <div className="text-10 text-faint mt-4 leading-normal">{cohort.blurb}.</div>
      </div>

      <nav data-mark="screens" className="flex-1 overflow-y-auto overflow-x-hidden pt-6 pb-10" aria-label={`${mode} screens`}>
        {NAV[mode].map((group) => (
          <div key={group.label} className="mb-9">
            <div className="text-9.5 uppercase tracking-label text-faint font-semibold px-12 pt-4 pb-3">
              {group.label}
            </div>
            {group.items.map((item) => {
              const on = item.key === activeKey;
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  onClick={() => go(item.path)}
                  aria-current={on ? "page" : undefined}
                  style={{
                    borderLeftColor: on ? "var(--accent)" : "transparent",
                    background: on ? "var(--sel)" : "transparent",
                    color: on ? "var(--text)" : "var(--dim)",
                    fontWeight: on ? 600 : 400,
                  }}
                  className="w-full text-left border-0 border-l-2 text-12 pl-10 pr-12 py-6 md:py-4 flex items-center gap-7 leading-relaxed hover:bg-panel3"
                >
                  <Icon className="size-13 opacity-75 flex-none" />
                  <span className="flex-1 whitespace-nowrap overflow-hidden text-ellipsis">{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-12 py-8 flex-none text-9.5 text-faint leading-normal">
        Ethiopia DHS 2024–25. Boundaries: UN OCHA COD-AB 2025 (CC BY-IGO).
      </div>
    </div>
  );
}
