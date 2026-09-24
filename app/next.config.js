/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV === "development";
// STATIC_EXPORT=1 builds a plain static site in out/ (for GitHub Pages), served
// under BASE_PATH (e.g. /<repository>). There is no Python there: the Predict
// tab uses NEXT_PUBLIC_PREDICT_API if it is set, and says so if it is not.
const isStatic = process.env.STATIC_EXPORT === "1";
const basePath = process.env.BASE_PATH || "";

module.exports = {
  reactStrictMode: true,
  // A separate output folder lets a production build run beside `next dev`
  // without overwriting the dev server's files (NEXT_DIST_DIR=.next-build).
  distDir: process.env.NEXT_DIST_DIR || ".next",
  ...(isStatic ? { output: "export", basePath, trailingSlash: true,
                   images: { unoptimized: true } } : {}),
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_STATIC_EXPORT: isStatic ? "1" : "",
  },
  // In development the Python function is served by scripts/dev_api.py on
  // port 8000. On Vercel, api/predict.py is routed natively and this rewrite
  // is not applied.
  ...(isStatic ? {} : {
    async rewrites() {
      return isDev
        ? [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }]
        : [];
    },
  }),
};
