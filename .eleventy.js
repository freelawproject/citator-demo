/**
 * Eleventy configuration.
 *
 *   src/        page templates (.njk)
 *   _includes/  layouts, partials and macros
 *   _data/      JSON written by scripts/build_data.py
 *   assets/     stylesheet source, fonts, Alpine components
 *   _site/      build output (gitignored)
 */
module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("assets/js");
  eleventyConfig.addPassthroughCopy("assets/fonts");
  // The CSP build: templates reference component members only, so the
  // page needs no `unsafe-eval` (same build CourtListener ships).
  eleventyConfig.addPassthroughCopy({
    "node_modules/@alpinejs/csp/dist/cdn.min.js": "assets/js/alpine.min.js",
  });
  // Dates are kept as YYYY-MM-DD in the data (they sort as text) and
  // shown as MM/DD/YYYY: this filter for the pages' own dates, and
  // data_source.short_date for the tab rows' columns.
  eleventyConfig.addFilter("usdate", (iso) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return m ? `${m[2]}/${m[3]}/${m[1]}` : iso || "";
  });

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "../_includes",
      data: "../_data",
    },
    templateFormats: ["njk", "md", "html"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};
