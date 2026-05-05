/**
 * Build-time global data. Available as `{{ build.* }}` in any template.
 *
 * `date` resolves at build time so the footer's "Generated YYYY-MM-DD"
 * reflects when Netlify last built the site.
 */
module.exports = {
  date: new Date().toISOString().slice(0, 10),
};
