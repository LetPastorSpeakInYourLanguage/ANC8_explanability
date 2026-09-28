/**
 * Colour ramps for the maps and heatmaps, in the house palette.
 *
 * Five classes rather than a continuous ramp: a reader can match a region to a
 * legend box, which a smooth gradient does not allow. "good" metrics run from
 * soft blue to the top-bar blue, "bad" metrics from soft red to the house red, and
 * gaps diverge through a neutral middle. Each has a light and a dark version so a
 * region reads the same against either background.
 */

import type { Scale } from "@/lib/metrics";

const RAMPS: Record<"light" | "dark", Record<"good" | "bad", string[]> & { diverging: string[] }> = {
  light: {
    good: ["#e1eefa", "#a9cbe9", "#5d9ed4", "#1a72b8", "#0a4e86"],
    bad: ["#f8e4e5", "#eeb2b4", "#d97a7d", "#bd4a4e", "#8f2528"],
    diverging: ["#a83236", "#dd9597", "#e7eef5", "#86c3ae", "#12735c"],
  },
  dark: {
    good: ["#132b3b", "#1d4e6f", "#2f78a8", "#4fa6e8", "#9fd2f7"],
    bad: ["#31191b", "#5a2729", "#8e3a3d", "#c7575b", "#f0999b"],
    diverging: ["#e0696d", "#8e3a3d", "#26313c", "#2b7a63", "#3eae8e"],
  },
};

export const NO_DATA = { light: "#dfe5ec", dark: "#1f2830" };

export interface Classes {
  breaks: number[]; // 4 inner breaks -> 5 classes
  colors: string[];
  min: number;
  max: number;
}

/** Five classes over the values shown: quantiles by default, equal intervals if asked;
 *  diverging scales are symmetric about 0. */
export function classify(
  values: (number | null)[],
  scale: Scale,
  theme: "light" | "dark",
  quantile = true,
): Classes {
  const v = values.filter((x): x is number => x != null && Number.isFinite(x));
  const colors = RAMPS[theme][scale];
  if (!v.length) return { breaks: [], colors, min: 0, max: 0 };
  let min = Math.min(...v);
  let max = Math.max(...v);
  if (scale === "diverging") {
    const a = Math.max(Math.abs(min), Math.abs(max)) || 1;
    min = -a;
    max = a;
    // the middle class is "about as expected": within a fifth of the widest gap
    return { breaks: [-0.6 * a, -0.2 * a, 0.2 * a, 0.6 * a], colors, min, max };
  }
  if (max === min) max = min + 1e-9;
  if (quantile) {
    // Quantile classes: about the same number of regions in each shade, so one
    // outlier (Addis Ababa on ANC8+) cannot push every other region into the
    // palest box. The legend shows the actual range of each class.
    const s = [...v].sort((a, b) => a - b);
    const at = (q: number) => {
      const pos = q * (s.length - 1);
      const lo = Math.floor(pos);
      return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (pos - lo);
    };
    return { breaks: [0.2, 0.4, 0.6, 0.8].map(at), colors, min, max };
  }
  const step = (max - min) / 5;
  return { breaks: [1, 2, 3, 4].map((i) => min + i * step), colors, min, max };
}

export function colorOf(v: number | null, c: Classes, theme: "light" | "dark"): string {
  if (v == null || !Number.isFinite(v) || !c.breaks.length) return NO_DATA[theme];
  let i = 0;
  while (i < c.breaks.length && v > c.breaks[i]) i++;
  return c.colors[i];
}

/** Text colour that stays readable on a class colour. */
export function inkOn(classIndexOrColor: string, theme: "light" | "dark"): string {
  const hex = classIndexOrColor.replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16), g = parseInt(hex.slice(2, 4), 16), b = parseInt(hex.slice(4, 6), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? "#0d1922" : theme === "dark" && lum > 0.45 ? "#0d1922" : "#ffffff";
}
