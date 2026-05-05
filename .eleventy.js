/**
 * Eleventy configuration.
 *
 * Source layout:
 *   _data/         — JSON data files (opinions/, index.json) consumed by templates
 *   _includes/     — partials (layouts, components)
 *   assets/        — static assets (css, js, images)
 *   src/           — page templates (.njk)
 *   _site/         — build output (gitignored)
 */
module.exports = function (eleventyConfig) {
  // Pass-through copy: assets and bundled JS go straight to _site/.
  eleventyConfig.addPassthroughCopy("assets/js");
  eleventyConfig.addPassthroughCopy("assets/fonts");
  eleventyConfig.addPassthroughCopy({ "node_modules/alpinejs/dist/cdn.min.js": "assets/js/alpine.min.js" });

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
