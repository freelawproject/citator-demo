document.addEventListener('alpine:init', () => {
  Alpine.data('searchFilter', () => ({
    query: '',
    selectedCourts: [],
    // Severity filters are split by direction (Direct history vs Citing
    // reference). Both sets are independent — a row must satisfy any
    // active filter in each direction it's filtered on.
    filterDhStop: false,
    filterDhWarning: false,
    filterDhCaution: false,
    filterDhNeutral: false,
    filterCrStop: false,
    filterCrWarning: false,
    filterCrCaution: false,
    filterCrNeutral: false,
    totalCount: 0,
    visibleCount: 0,

    setQuery(value) {
      this.query = (value || '').trim().toLowerCase();
      this.syncToURL();
      this.recount();
    },

    toggleCourt(court, checked) {
      this.selectedCourts = checked
        ? [...this.selectedCourts.filter((c) => c !== court), court]
        : this.selectedCourts.filter((c) => c !== court);
      this.syncToURL();
      this.recount();
    },

    setSevFilter(prop, checked) {
      this[prop] = checked;
      this.syncToURL();
      this.recount();
    },

    // ── Court-category bulk helpers ────────────────────────────────────
    isCategoryAll(keys) {
      return keys.length > 0 && keys.every((k) => this.selectedCourts.includes(k));
    },

    isCategoryPartial(keys) {
      const some = keys.some((k) => this.selectedCourts.includes(k));
      const all = this.isCategoryAll(keys);
      return some && !all;
    },

    toggleCategory(keys, checked) {
      if (checked) {
        const next = new Set([...this.selectedCourts, ...keys]);
        this.selectedCourts = [...next];
      } else {
        const dropped = new Set(keys);
        this.selectedCourts = this.selectedCourts.filter(
          (k) => !dropped.has(k)
        );
      }
      this.syncToURL();
      this.recount();
    },

    // ── Court-category collapse state ──────────────────────────────────
    expandedCategories: [],

    isExpanded(category) {
      return this.expandedCategories.includes(category);
    },

    toggleExpanded(category) {
      this.expandedCategories = this.isExpanded(category)
        ? this.expandedCategories.filter((c) => c !== category)
        : [...this.expandedCategories, category];
    },

    rowVisible(el) {
      if (
        this.selectedCourts.length > 0 &&
        !this.selectedCourts.includes(el.dataset.court)
      ) {
        return false;
      }
      if (this.hasDhFilters()) {
        const sev = el.dataset.dhSeverity;
        const match =
          (this.filterDhStop && sev === 'stop') ||
          (this.filterDhWarning && sev === 'warning') ||
          (this.filterDhCaution && sev === 'caution') ||
          (this.filterDhNeutral && sev === 'neutral');
        if (!match) return false;
      }
      if (this.hasCrFilters()) {
        const sev = el.dataset.crSeverity;
        const match =
          (this.filterCrStop && sev === 'stop') ||
          (this.filterCrWarning && sev === 'warning') ||
          (this.filterCrCaution && sev === 'caution') ||
          (this.filterCrNeutral && sev === 'neutral');
        if (!match) return false;
      }
      if (this.query) {
        const name = el.dataset.caseName || '';
        if (!name.includes(this.query)) return false;
      }
      return true;
    },

    hasDhFilters() {
      return (
        this.filterDhStop || this.filterDhWarning ||
        this.filterDhCaution || this.filterDhNeutral
      );
    },

    hasCrFilters() {
      return (
        this.filterCrStop || this.filterCrWarning ||
        this.filterCrCaution || this.filterCrNeutral
      );
    },

    recount() {
      const rows = this.$root.querySelectorAll('[data-court]');
      let count = 0;
      rows.forEach((row) => {
        if (this.rowVisible(row)) count += 1;
      });
      this.visibleCount = count;
    },

    // ── URL state sync ─────────────────────────────────────────────────
    parseFromURL() {
      const params = new URLSearchParams(window.location.search);
      // If the URL has no filter params, fall back to sessionStorage —
      // covers the case where back-navigation lands on `/` after the
      // browser drops the previously-set query string from history.
      if (!params.toString()) {
        const saved = sessionStorage.getItem('citatorSearchFilter');
        if (saved) {
          try {
            const restored = new URLSearchParams(saved);
            restored.forEach((v, k) => params.set(k, v));
          } catch (_) { /* ignore malformed sessionStorage value */ }
        }
      }
      this.query = (params.get('q') || '').trim().toLowerCase();
      const courts = params.get('courts');
      this.selectedCourts = courts ? courts.split(',').filter(Boolean) : [];

      const dhTiers = (params.get('dh_sev') || '').split(',').filter(Boolean);
      this.filterDhStop = dhTiers.includes('stop');
      this.filterDhWarning = dhTiers.includes('warning');
      this.filterDhCaution = dhTiers.includes('caution');
      this.filterDhNeutral = dhTiers.includes('neutral');

      const crTiers = (params.get('cr_sev') || '').split(',').filter(Boolean);
      this.filterCrStop = crTiers.includes('stop');
      this.filterCrWarning = crTiers.includes('warning');
      this.filterCrCaution = crTiers.includes('caution');
      this.filterCrNeutral = crTiers.includes('neutral');

      // Sync URL back if we restored from storage but URL is empty.
      if (!window.location.search && params.toString()) {
        const url = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState(null, '', url);
      }
    },

    syncToURL() {
      const params = new URLSearchParams();
      if (this.query) params.set('q', this.query);
      if (this.selectedCourts.length) {
        params.set('courts', this.selectedCourts.join(','));
      }

      const dhTiers = [];
      if (this.filterDhStop) dhTiers.push('stop');
      if (this.filterDhWarning) dhTiers.push('warning');
      if (this.filterDhCaution) dhTiers.push('caution');
      if (this.filterDhNeutral) dhTiers.push('neutral');
      if (dhTiers.length) params.set('dh_sev', dhTiers.join(','));

      const crTiers = [];
      if (this.filterCrStop) crTiers.push('stop');
      if (this.filterCrWarning) crTiers.push('warning');
      if (this.filterCrCaution) crTiers.push('caution');
      if (this.filterCrNeutral) crTiers.push('neutral');
      if (crTiers.length) params.set('cr_sev', crTiers.join(','));

      const qs = params.toString();
      const url = qs
        ? `${window.location.pathname}?${qs}`
        : window.location.pathname;
      // Mirror to sessionStorage so the state survives any back-nav
      // quirk that drops the URL query string.
      if (qs) sessionStorage.setItem('citatorSearchFilter', qs);
      else sessionStorage.removeItem('citatorSearchFilter');
      // Skip the replaceState call if the URL hasn't changed — avoids
      // redundant history-state writes on hydration.
      const currentUrl = window.location.pathname + window.location.search;
      if (currentUrl === url) return;
      window.history.replaceState(null, '', url);
    },

    init() {
      const rows = this.$root.querySelectorAll('[data-court]');
      this.totalCount = rows.length;
      this.visibleCount = rows.length;

      this.parseFromURL();

      // Initial recount after URL hydration. State changes from user
      // interactions go through setQuery / toggleCourt / toggleCategory /
      // setSevFilter, which each call syncToURL + recount directly —
      // that's more reliable than $watch on array reassignment in the
      // CSP Alpine build.
      this.recount();

      // Re-hydrate from URL on bfcache restore (back/forward nav). When
      // the browser restores the page from cache, init() doesn't re-run,
      // but the URL still carries the persisted filter params — read
      // them again so the UI reflects the saved state.
      window.addEventListener('pageshow', (e) => {
        if (e.persisted) {
          this.parseFromURL();
          this.recount();
        }
      });
    },
  }));
});
