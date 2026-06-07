import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0e14",
          900: "#0f141c",
          850: "#141b25",
          800: "#1b2531",
          700: "#26323f",
          600: "#3a4855",
        },
        brand: {
          400: "#38bdf8",
          500: "#0ea5e9",
        },
        bull: "#22c55e",
        bear: "#ef4444",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
