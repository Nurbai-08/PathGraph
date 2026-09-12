import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211b",
        moss: "#245c3f",
        cream: "#f6f4ec",
        lime: "#c9f27b",
      },
      boxShadow: {
        soft: "0 20px 60px rgba(23, 33, 27, 0.10)",
      },
    },
  },
  plugins: [],
} satisfies Config;

