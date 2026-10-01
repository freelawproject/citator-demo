/**
 * Build-time global data. Available as `{{ build.* }}` in any template.
 *
 * - `date` — resolves at build time; powers the footer's "Generated YYYY-MM-DD".
 * - `stamp` — a per-build token appended to script and stylesheet URLs
 *   (`?v=…`) so browsers never reuse a cached copy after a rebuild (the
 *   local server sends no cache headers).
 */
module.exports = {
  date: new Date().toISOString().slice(0, 10),
  stamp: Date.now().toString(36),
};
