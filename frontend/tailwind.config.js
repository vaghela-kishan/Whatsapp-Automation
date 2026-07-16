/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
        ink: {
          900: "#0b1220",
          950: "#070b14",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,0.04), 0 8px 24px -12px rgba(15,23,42,0.12)",
        soft: "0 12px 40px -12px rgba(15,23,42,0.18)",
        glow: "0 0 0 1px rgba(16,185,129,0.15), 0 8px 30px -8px rgba(16,185,129,0.35)",
        "inner-top": "inset 0 1px 0 0 rgba(255,255,255,0.6)",
      },
      backgroundImage: {
        "mesh-light":
          "radial-gradient(900px 500px at 100% -10%, rgba(16,185,129,0.10), transparent 60%), radial-gradient(800px 500px at -10% 110%, rgba(99,102,241,0.08), transparent 55%)",
        "brand-gradient": "linear-gradient(135deg, #34d399 0%, #059669 100%)",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "scale(0.94)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
        "gradient-x": {
          "0%,100%": { "background-position": "0% 50%" },
          "50%": { "background-position": "100% 50%" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s cubic-bezier(0.22,1,0.36,1)",
        "pop-in": "pop-in 0.25s cubic-bezier(0.22,1,0.36,1)",
        shimmer: "shimmer 1.6s infinite",
        float: "float 4s ease-in-out infinite",
        "gradient-x": "gradient-x 6s ease infinite",
      },
    },
  },
  plugins: [],
};
