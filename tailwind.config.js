/**
 * Tailwind config. Tokens (colors, type scale, spacing) will be ported from
 * the new CourtListener front-end design as part of issue #5. This is a
 * placeholder set just to make `npm run build:css` succeed.
 */
module.exports = {
  content: [
    "./src/**/*.{njk,md,html}",
    "./_includes/**/*.{njk,md,html}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
