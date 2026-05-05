/**
 * Build-time global data. Available as `{{ build.* }}` in any template.
 *
 * - `date` — resolves at build time; powers the footer's "Generated YYYY-MM-DD".
 * - `placeholder_until` — non-null while the site runs on mock fixtures
 *   (issue #4). Cleared in #13 when real inference data lands; the
 *   placeholder banner is conditionally hidden when null.
 */
module.exports = {
  date: new Date().toISOString().slice(0, 10),
  placeholder_until: "May 18",
};
