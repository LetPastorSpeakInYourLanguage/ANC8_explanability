import type { HelpGroup } from "./types";

/**
 * The Help's table of contents, light enough for the navigation and the finder to load
 * on every screen. The full text lives in basics.ts, plan.ts, explore.ts and models.ts;
 * lib/help/index.ts checks that the two agree.
 */

export interface TopicEntry {
  key: string;
  label: string;
  group: HelpGroup;
  blurb: string;
}

export const HELP_GROUPS: { key: HelpGroup; label: string }[] = [
  { key: "start", label: "Start here" },
  { key: "plan", label: "Planning tools" },
  { key: "explore", label: "Exploratory analysis" },
  { key: "models", label: "Models" },
];

export const TOPIC_LIST: TopicEntry[] = [
  { key: "start", label: "Getting around", group: "start", blurb: "What the studio is for and the parts of every screen" },
  { key: "controls", label: "Controls and settings", group: "start", blurb: "Modes, scope, cohort, the finder, presenting, sharing a view" },
  { key: "basics-ladder", label: "The ANC ladder", group: "start", blurb: "Antenatal care, contacts, the three rungs and the three cohorts" },
  { key: "basics-numbers", label: "Reading the numbers", group: "start", blurb: "Shares, points, intervals, women per year, associations" },
  { key: "basics-charts", label: "Reading the charts", group: "start", blurb: "Every kind of chart in the studio, and how to read it" },
  { key: "basics-models", label: "How models are judged", group: "start", blurb: "Predictions, held-out women, chance, AP, AUROC, calibration" },
  { key: "terms", label: "Words, A to Z", group: "start", blurb: "Every term the studio uses, in plain language" },
  { key: "overview", label: "Overview", group: "plan", blurb: "The ladder at a glance and four things to act on" },
  { key: "map", label: "Map & regions", group: "plan", blurb: "Where women are lost, and one region's full analysis" },
  { key: "planner", label: "Scenario planner", group: "plan", blurb: "What changes if programmes reach more women" },
  { key: "war", label: "Conflict simulator", group: "plan", blurb: "What a war like Tigray's would do elsewhere" },
  { key: "data", label: "Your data", group: "plan", blurb: "Trends and forecasts from your own ANC counts" },
  { key: "ladder", label: "The ANC ladder (screen)", group: "explore", blurb: "Who reaches each rung, and where they stop" },
  { key: "predictors", label: "Predictor selection", group: "explore", blurb: "From 6,648 survey columns to the few that predict" },
  { key: "models", label: "Models compared", group: "explore", blurb: "Every model, every rung, every predictor set" },
  { key: "cohorts", label: "Cohorts & horizons", group: "explore", blurb: "Does the answer change with who is counted, and when?" },
  { key: "analysis", label: "Model analysis", group: "models", blurb: "One model at a time: accuracy, honesty, how it was built" },
  { key: "predict", label: "Predict", group: "models", blurb: "Score one woman and see why" },
  { key: "screener", label: "First-visit screener", group: "models", blurb: "Twelve questions that rank a register for follow-up" },
  { key: "about", label: "About the study", group: "models", blurb: "The study on one page, and where each finding lives" },
];

export const TOPIC_KEYS = TOPIC_LIST.map((t) => t.key);

export function topicEntry(key: string): TopicEntry | undefined {
  return TOPIC_LIST.find((t) => t.key === key);
}
