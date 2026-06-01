/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Scan all Django templates for Tailwind class usage (includes cotton/ components)
    "../../templates/**/*.html",
    // Also scan any JS files that might add classes dynamically
    "../js/**/*.js",
    // Scan app Python files for dynamic class strings
    "../../apps/**/*.py",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Keep the system sans stack; add a mono for data values
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        default: {
          "color-scheme": "light",
          "primary": "#059669",          // emerald-600 — energy-domain accent
          "secondary": "#0284c7",        // sky-600
          "accent": "#10b981",
          "neutral": "#1f2937",
          "base-100": "#ffffff",
          "base-200": "#f1f5f9",
          "base-300": "#e2e8f0",
          "info": "#0284c7",
          "success": "#16a34a",
          "warning": "#d97706",
          "error": "#dc2626",
        },
        dark: {
          "color-scheme": "dark",
          "primary": "#10b981",
          "secondary": "#38bdf8",
          "accent": "#34d399",
          "neutral": "#0f172a",
          "base-100": "#0f172a",         // slate-900
          "base-200": "#1e293b",
          "base-300": "#334155",
          "info": "#38bdf8",
          "success": "#22c55e",
          "warning": "#f59e0b",
          "error": "#ef4444",
        },
        "high-contrast": {
          "color-scheme": "light",
          "primary": "#0a4ad9",          // strong blue for WCAG AAA contrast on white
          "secondary": "#000000",
          "accent": "#0a4ad9",
          "neutral": "#000000",
          "base-100": "#ffffff",
          "base-200": "#ffffff",
          "base-300": "#000000",         // strong borders
          "info": "#000000",
          "success": "#006400",
          "warning": "#cc6600",
          "error": "#cc0000",
        },
      },
    ],
    darkTheme: "dark",
    base: true,
    styled: true,
    utils: true,
  },
};
