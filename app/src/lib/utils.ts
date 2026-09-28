import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * The ASTU type scale, as it appears in class names (`text-10.5`, `text-13.5`, …). Mirrors
 * the `--text-*` entries `globals.css` adds to `@theme`; the token there spells the decimal
 * with a hyphen (`--text-10-5`) but the class keeps the dot.
 *
 * tailwind-merge has to be told about these. Its built-in `font-size` group only recognises
 * t-shirt sizes (`text-sm`), while its `text-color` group matches ANY `text-*` — so a custom
 * numeric size was being classified as a colour, and a later colour on the same element then
 * won and DELETED the size. `cn("text-10.5 … text-faint")` really did return
 * "font-semibold uppercase tracking-label text-faint", which is why every <Label> rendered at
 * the inherited body size instead of 10.5px.
 *
 * This affects the whole vendored shadcn layer, since those components all merge a base class
 * string against a caller's className, so the fix belongs here rather than at any one call
 * site. Any size added to `@theme` must be added here too.
 */
const FONT_SIZES = [
  "8.5", "9.5", "10", "10.5", "11", "11.5", "12", "12.5",
  "13", "13.5", "14", "15", "17", "19", "21", "26", "30",
];

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: FONT_SIZES }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
