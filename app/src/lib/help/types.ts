/**
 * The shape of the studio's Help: topics (one per screen, plus the basics), each a list
 * of cards (one per panel). Text is plain strings; `**bold**` and `[label](/path)` are
 * the only markup (see components/help/HelpText.tsx).
 */

export type HelpGroup = "start" | "plan" | "explore" | "models";

export interface HelpCard {
  /** Unique within its topic. `<topic>.<id>` is the help id a Panel carries. */
  id: string;
  title: string;
  /** One or two sentences: what the panel shows. */
  shows: string;
  /** How to read it, one point per line. */
  read: string[];
  /** Links that open the screen in a state that shows the point. */
  tryIt?: { text: string; href: string }[];
  /** The caveat that belongs with it. */
  watch?: string;
  /** Glossary term ids (lib/help/terms.ts). */
  terms?: string[];
  /** The screenshot crop to show: default `<topic>.<id>`; another help id to borrow one; false for none. */
  shot?: string | false;
}

export interface HelpRecipe {
  title: string;
  steps: string[];
}

export interface HelpTopic {
  /** Equal to the screen's nav key, so a screen and its help find each other. */
  key: string;
  label: string;
  group: HelpGroup;
  /** One line for lists and search results. */
  blurb: string;
  /** The screen this topic explains, with any state its screenshot uses. */
  screen?: string;
  /** Two or three sentences: what the screen is for. */
  purpose: string;
  /** Basics topics worth reading first. */
  before?: string[];
  /** Numbered marks on the screen's full screenshot. Without them, every card whose
   *  panel is in view is marked, in card order. `mark` is a help id or a named mark
   *  recorded by scripts/capture_help_shots.mjs. */
  callouts?: { mark: string; text: string; href?: string }[];
  recipes?: HelpRecipe[];
  cards: HelpCard[];
  faq?: { q: string; a: string }[];
}

export interface HelpTerm {
  id: string;
  name: string;
  aka?: string[];
  plain: string;
  /** Where the term turns up in the studio, or a worked example. */
  example?: string;
}
