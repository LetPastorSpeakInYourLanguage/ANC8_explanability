import type { Config } from "tailwindcss";
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12161c",
        paper: "#fbfaf8",
        v1: "#7c6f9c",
        v2: "#2f7d70",
      },
    },
  },
  plugins: [],
} satisfies Config;
