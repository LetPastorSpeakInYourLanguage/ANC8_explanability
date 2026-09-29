"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { topicForScreen } from "@/lib/help/href";
import { LEGACY_HASH, itemForPath } from "@/lib/nav";
import TopBar from "./TopBar";
import Sidebar from "./Sidebar";
import ContentHeader from "./ContentHeader";
import StatusBar from "./StatusBar";
import Tour from "./Tour";

interface ShellHeader {
  crumb?: string;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

/** Lets a screen override the 36px content header (the house HeaderContext). */
const HeaderContext = createContext<(h: ShellHeader) => void>(() => {});
export function useShellHeader(header: ShellHeader, deps: unknown[] = []) {
  const set = useContext(HeaderContext);
  useEffect(() => {
    set(header);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/**
 * The house application shell: 38px top bar, 236px sidebar, 36px content header,
 * 24px status bar. The content pane is the only thing that scrolls.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const search = useSearchParams();
  const [override, setOverride] = useState<ShellHeader>({});
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setOverride({});
    setDrawerOpen(false);
  }, [pathname]);

  // Links shared before the studio (…/#reports, …/#predict/…) still arrive somewhere.
  useEffect(() => {
    if (pathname !== "/" || !window.location.hash) return;
    const key = window.location.hash.replace(/^#/, "").split("/")[0];
    const to = LEGACY_HASH[key];
    if (to) router.replace(to);
  }, [pathname, router]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  const item = itemForPath(pathname);
  const meta = item?.meta ?? ["", "", ""];
  const helpTopic = topicForScreen(item?.key, pathname, search.get("mode"));

  return (
    <HeaderContext.Provider value={setOverride}>
      <div className="h-dvh w-full grid grid-rows-[38px_1fr_24px] bg-bg overflow-hidden">
        <TopBar onOpenMenu={() => setDrawerOpen(true)} />

        <div className="grid grid-cols-1 md:grid-cols-[236px_1fr] min-h-0 overflow-hidden relative">
          <div className="hidden md:block min-h-0">
            <Sidebar />
          </div>

          {drawerOpen && (
            <>
              <div
                className="md:hidden fixed inset-0 bg-black opacity-40 z-[1300]"
                onClick={() => setDrawerOpen(false)}
                aria-hidden="true"
              />
              <div className="md:hidden fixed left-0 top-38 bottom-24 w-[min(280px,85vw)] z-[1301] border-r border-border">
                <Sidebar onNavigate={() => setDrawerOpen(false)} />
              </div>
            </>
          )}

          <div className="flex flex-col min-w-0 min-h-0 bg-bg overflow-hidden">
            <ContentHeader
              crumb={override.crumb ?? meta[0]}
              title={override.title ?? meta[1]}
              subtitle={override.subtitle ?? meta[2]}
              actions={override.actions}
              help={helpTopic}
            />
            <main className="flex-1 overflow-auto min-h-0" id="content">
              {children}
            </main>
          </div>
        </div>

        <StatusBar />
        <Tour />
      </div>
    </HeaderContext.Provider>
  );
}
