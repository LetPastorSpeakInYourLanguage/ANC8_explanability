"use client";

import { useEffect, useRef, useState } from "react";
import { fetchCurrent, saveNow, useOffline } from "@/lib/offline";

/**
 * The status bar's offline control: a small progress bar while the studio is being saved
 * in this browser, "available offline" when it is, "offline" without a connection.
 * Clicking it opens a menu: fetch the current version from the server, or save now.
 */
export default function OfflineStatus() {
  const off = useOffline();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);

  if (off.phase === "off" && off.online) return null;
  const pct = off.total ? Math.round((100 * off.saved) / off.total) : 0;
  const label = !off.online ? "offline"
    : off.phase === "ready" ? "available offline"
    : off.phase === "saving" ? `saving for offline ${pct}%`
    : off.phase === "skipped" ? "save for offline"
    : "preparing offline copy";

  return (
    <div ref={box} className="flex-none">
      <button
        onClick={() => setOpen((o) => !o)}
        title="The studio's offline copy in this browser"
        aria-expanded={open}
        className={`flex items-center gap-6 whitespace-nowrap text-topfg hover:opacity-100 ${off.online ? "opacity-85" : "font-semibold"}`}
      >
        {off.phase === "saving" && off.online && (
          <span className="w-44 h-4 bg-white/25 rounded-1 overflow-hidden hidden sm:block" aria-hidden="true">
            <span className="block h-full bg-white" style={{ width: `${pct}%` }} />
          </span>
        )}
        <span className={off.online && off.phase !== "skipped" ? "hidden sm:inline" : ""}>{label}</span>
        {off.online && off.phase === "saving" && <span className="sm:hidden font-mono">{pct}%</span>}
      </button>

      {open && (
        <div className="fixed bottom-26 left-10 z-[1400] w-260 border border-border2 bg-panel text-text shadow-lg">
          <div className="px-12 pt-10 pb-8 border-b border-border">
            <div className="text-9.5 uppercase tracking-label text-faint font-semibold">Offline copy</div>
            <div className="text-11 mt-4 leading-normal">
              {!off.online
                ? "No connection: the saved copy is showing. Predict needs the connection."
                : off.phase === "ready"
                  ? "Every screen, the data and the pictures are saved in this browser."
                  : off.phase === "saving"
                    ? `Saving: ${off.saved} of ${off.total} files. Model and analysis data first, Help pictures last.`
                    : off.phase === "skipped"
                      ? "Data saver is on, so nothing is saved in the background."
                      : "The saved copy starts once this screen has loaded."}
            </div>
            {off.phase === "saving" && (
              <div className="mt-6 h-4 bg-panel3 rounded-1 overflow-hidden" aria-hidden="true">
                <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
              </div>
            )}
          </div>
          <div className="flex flex-col py-4">
            <button
              disabled={!off.online || busy}
              onClick={async () => { setBusy(true); await fetchCurrent(); }}
              className="text-left px-12 py-6 text-11 hover:bg-panel2 disabled:text-faint"
            >
              Fetch current version
              <span className="block text-9.5 text-faint">Drop the saved copy and reload from the server</span>
            </button>
            {off.phase !== "ready" && off.phase !== "saving" && (
              <button
                disabled={!off.online}
                onClick={() => { saveNow(); setOpen(false); }}
                className="text-left px-12 py-6 text-11 hover:bg-panel2 disabled:text-faint"
              >
                Save for offline now
                <span className="block text-9.5 text-faint">Every screen, the data and the pictures (about 21 MB)</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
