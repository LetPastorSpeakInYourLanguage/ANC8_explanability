import {
  BookOpen,
  Bot,
  Calculator,
  ChartColumnBig,
  ChartNetwork,
  Flame,
  Gauge,
  Layers,
  Microscope,
  LibraryBig,
  ListTree,
  Map as MapIcon,
  NotebookText,
  Scale,
  SlidersHorizontal,
  Split,
  Upload,
  type LucideIcon,
} from "lucide-react";

/**
 * Navigation, organised the house way: by what the reader is DOING, not by which
 * analysis produced a result. Planning comes first because the studio exists for the
 * people who allocate effort across regions; the exploratory analysis, the models and
 * the written record follow for anyone who wants to check the ground under a plan.
 */

export type Mode = "plan" | "explore" | "models" | "library";

export interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
  path: string;
  /** The content header for this screen: crumb, title, subtitle. */
  meta: [string, string, string];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const MODES: { key: Mode; label: string }[] = [
  { key: "plan", label: "Plan" },
  { key: "explore", label: "Explore" },
  { key: "models", label: "Models" },
  { key: "library", label: "Library" },
];

export const NAV: Record<Mode, NavGroup[]> = {
  plan: [
    {
      label: "Start",
      items: [
        { key: "overview", label: "Overview", icon: Gauge, path: "/",
          meta: ["Plan", "Antenatal care in Ethiopia at a glance", "EDHS 2024–25"] },
      ],
    },
    {
      label: "Planning tools",
      items: [
        { key: "map", label: "Map & regions", icon: MapIcon, path: "/map",
          meta: ["Plan", "Where women are lost, region by region", "click a region for its analysis"] },
        { key: "planner", label: "Scenario planner", icon: SlidersHorizontal, path: "/planner",
          meta: ["Plan", "What changes if we work on a factor", "association-based scenarios"] },
        { key: "war", label: "Conflict simulator", icon: Flame, path: "/war",
          meta: ["Plan", "If conflict reaches a region", "built from the Tigray war"] },
        { key: "data", label: "Your data", icon: Upload, path: "/your-data",
          meta: ["Plan", "Trends and forecasts from your own records", "runs in this browser"] },
      ],
    },
  ],
  explore: [
    {
      label: "Exploratory analysis",
      items: [
        { key: "ladder", label: "The ANC ladder", icon: Layers, path: "/explore/ladder",
          meta: ["Explore", "ANC1+, ANC4+ and ANC8+", "who reaches each rung"] },
        { key: "predictors", label: "Predictor selection", icon: ListTree, path: "/explore/predictors",
          meta: ["Explore", "Which predictors carry the prediction", "from 6,648 columns to a few"] },
        { key: "models", label: "Models compared", icon: ChartColumnBig, path: "/explore/models",
          meta: ["Explore", "Every model, every rung, every predictor set", "and what tuning bought"] },
        { key: "cohorts", label: "Cohorts & horizons", icon: Split, path: "/explore/cohorts",
          meta: ["Explore", "Full cohort, ANC entry and the 24-month window", "does the answer change?"] },
      ],
    },
  ],
  models: [
    {
      label: "Models",
      items: [
        { key: "lab", label: "Model lab", icon: ChartNetwork, path: "/lab",
          meta: ["Models", "Networks, attention and forecasting", "benchmarked against the trees"] },
        { key: "predict", label: "Predict", icon: Calculator, path: "/predict",
          meta: ["Models", "Score one woman", "choose an outcome and a model"] },
        { key: "screener", label: "First-visit screener", icon: Bot, path: "/your-data?mode=register",
          meta: ["Models", "First-visit screener", "runs in this browser"] },
        { key: "analysis", label: "Model analysis", icon: Microscope, path: "/models",
          meta: ["Models", "Every model, how it was built and how it beats chance", "switch models to compare"] },
      ],
    },
  ],
  library: [
    {
      label: "Library",
      items: [
        { key: "reports", label: "Reports & figures", icon: LibraryBig, path: "/library",
          meta: ["Library", "Every document and figure", "the written study"] },
        { key: "record", label: "Analysis record", icon: NotebookText, path: "/library/record",
          meta: ["Library", "Every analysis, and how it was tested", "question · test · result"] },
        { key: "glossary", label: "Terms & charts", icon: BookOpen, path: "/library/glossary",
          meta: ["Library", "What every term and chart means", "plain language"] },
        { key: "limits", label: "Limitations", icon: Scale, path: "/library?doc=limitations",
          meta: ["Library", "What this study cannot support", ""] },
      ],
    },
  ],
};

const ALL: (NavItem & { mode: Mode })[] = (Object.keys(NAV) as Mode[]).flatMap((mode) =>
  NAV[mode].flatMap((g) => g.items.map((i) => ({ ...i, mode }))),
);

/** The nav item a pathname belongs to: the longest matching path wins. */
export function itemForPath(pathname: string): (NavItem & { mode: Mode }) | undefined {
  const clean = pathname.replace(/\/+$/, "") || "/";
  let best: (NavItem & { mode: Mode }) | undefined;
  for (const item of ALL) {
    const p = item.path.split("?")[0];
    const hit = p === "/" ? clean === "/" : clean === p || clean.startsWith(p + "/");
    if (hit && (!best || p.length > best.path.split("?")[0].length)) best = item;
  }
  return best;
}

export function modeForPath(pathname: string): Mode {
  return itemForPath(pathname)?.mode ?? "plan";
}

export function allNavItems() {
  return ALL;
}

/** Links from before the studio (#reports, #predict/…) and where they live now. */
export const LEGACY_HASH: Record<string, string> = {
  reports: "/library",
  brief: "/library?doc=brief",
  findings: "/map",
  predictors: "/explore/predictors",
  ladder: "/explore/ladder",
  horizons: "/explore/cohorts",
  wartime: "/war",
  predict: "/predict",
  whatif: "/predict",
  evidence: "/explore/models",
  record: "/library/record",
  journey: "/library/record",
};
