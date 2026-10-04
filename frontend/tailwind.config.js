/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pine: { DEFAULT: "#0E2B2B", 2: "#16403F", 3: "#245654", text: "#CFE0DC", dim: "#8FAAA5" },
        paper: "#F4F6F5",
        line: "#DCE3E0",
        ink: { DEFAULT: "#142321", muted: "#56665F" },
        signal: { DEFAULT: "#D98E04", soft: "#FCF1DC" },
        hot: { DEFAULT: "#B93A0E", soft: "#FBE9E2" },
        high: { DEFAULT: "#9A6408", soft: "#FBF0DA" },
        medium: { DEFAULT: "#2B6A88", soft: "#E3EFF5" },
        low: { DEFAULT: "#5E6B68", soft: "#ECEFEE" },
        ok: { DEFAULT: "#1F7A4D", soft: "#E2F3EA" },
        danger: { DEFAULT: "#B42318", soft: "#FDECEA" },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      fontSize: { "2xs": ["0.6875rem", "1rem"] },
    },
  },
  plugins: [],
};
