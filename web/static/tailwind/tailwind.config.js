/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Scan all Django templates for Tailwind class usage
    "../../templates/**/*.html",
    // Also scan any JS files that might add classes dynamically
    "../js/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Keep the system sans stack; add a mono for data values
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
