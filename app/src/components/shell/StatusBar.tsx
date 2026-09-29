"use client";

import Link from "next/link";
import { COHORTS, useStudio } from "@/lib/studio";

/** The house status bar: what the screen is about on the left, the standing caveat
 *  on the right. The caveat never leaves the screen, because every number in the
 *  studio is an association in one survey round. */
export default function StatusBar() {
  const studio = useStudio();
  const cohort = COHORTS.find((c) => c.key === studio.cohort) ?? COHORTS[0];
  return (
    <div data-mark="status" className="bg-top text-topfg flex items-center gap-8 md:gap-12 px-10 text-10.5 flex-none min-w-0 overflow-hidden">
      <span className="opacity-85 whitespace-nowrap flex-none">EDHS 2024–25</span>
      <span aria-hidden="true" className="flex-none">|</span>
      <span className="opacity-85 whitespace-nowrap flex-none hidden sm:inline">survey-weighted</span>
      <span aria-hidden="true" className="flex-none hidden sm:inline">|</span>
      <span className="opacity-85 whitespace-nowrap flex-none max-w-[40vw] overflow-hidden text-ellipsis">
        {studio.region || "Ethiopia"} · {cohort.label.toLowerCase()}
      </span>
      <Link href={studio.href("/about")} className="opacity-85 hover:opacity-100 whitespace-nowrap flex-none hover:no-underline text-topfg">
        About the study
      </Link>
      <div className="flex-1 min-w-8" />
      <span className="whitespace-nowrap overflow-hidden text-ellipsis min-w-0">
        <span className="hidden lg:inline">
          Associations, not causes · a prediction describes women like her, not her
        </span>
        <span className="lg:hidden">Associations, not causes</span>
      </span>
    </div>
  );
}
