import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        win95: {
          bg: "#c0c0c0",
          teal: "#008080",
          blue: "#000080",
          cyan: "#1084d0",
          dark: "#808080",
          darker: "#404040",
          light: "#ffffff",
          green: "#008000",
          red: "#cc0000",
        },
      },
    },
  },
  plugins: [],
};
export default config;
