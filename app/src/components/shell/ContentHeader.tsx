"use client";

import Link from "next/link";
import { ChevronDown, CircleHelp } from "lucide-react";
import { RUNGS, useStudio } from "@/lib/studio";
import { useOpenScope } from "./ScopePicker";

export default function ContentHeader({
  crumb,
  title,
  subtitle,
  actions,
  help,
}: {
  crumb?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  /** This screen's Help topic: a link to its guide sits at the right. */
  help?: string | null;
}) {
  const studio = useStudio();
  const openScope = useOpenScope();
  return (
    <div data-mark="header" className="h-36 border-b border-border flex items-center gap-10 px-12 flex-none bg-panel min-w-0">
      {crumb && <div className="text-10.5 text-faint whitespace-nowrap hidden sm:block">{crumb}</div>}
      <div className="text-13.5 font-semibold whitespace-nowrap overflow-hidden text-ellipsis">{title}</div>
      <div className="flex-1" />
      {subtitle && <div className="text-10.5 text-dim whitespace-nowrap hidden md:block">{subtitle}</div>}
      {actions}
      <button
        data-mark="scope-chip"
        onClick={openScope}
        title="Change the scope: the whole country or one region, the rung and the cohort"
        className="flex items-center gap-4 h-22 px-7 rounded-2 border border-border2 bg-panel2 text-10.5 text-dim hover:text-accent hover:border-accent flex-none min-w-0"
      >
        <span className="w-6 h-6 bg-accent rounded-1 flex-none" />
        <span className="truncate max-w-[28vw] sm:max-w-[160px]">{studio.region || "Ethiopia"}</span>
        <span className="font-mono text-9.5 text-faint flex-none">{RUNGS.find((r) => r.key === studio.rung)?.label}</span>
        <ChevronDown className="size-11 flex-none" />
      </button>
      {help && (
        <Link
          data-mark="help"
          href={`/help/${help}`}
          title="How to use this screen"
          className="flex items-center gap-4 h-22 px-7 rounded-2 border border-border2 bg-panel2 text-10.5 text-dim hover:text-accent hover:border-accent hover:no-underline flex-none"
        >
          <CircleHelp className="size-12" />
          <span className="hidden sm:inline">Help</span>
        </Link>
      )}
    </div>
  );
}
