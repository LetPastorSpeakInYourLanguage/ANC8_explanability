/**
 * Where the app's files and the prediction service live.
 *
 * The same code serves three ways: `next dev` locally, Vercel, and a static
 * export on GitHub Pages under /<repository>/. A static host has no Python,
 * so there the Predict tab calls the prediction service of another deployment
 * (NEXT_PUBLIC_PREDICT_API, e.g. the Vercel one) or explains that it is
 * unavailable.
 */

export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** A file from app/public, e.g. asset("/analysis.json"). */
export function asset(path: string): string {
  return `${BASE_PATH}${path}`;
}

/** The prediction endpoint, or null when this build has none. */
export const PREDICT_API: string | null =
  process.env.NEXT_PUBLIC_PREDICT_API ??
  (process.env.NEXT_PUBLIC_STATIC_EXPORT === "1" ? null : "/api/predict");
