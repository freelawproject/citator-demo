/*
The Authorities and Cited By lists: the search box, sort dropdown and
filter menu above the list. One factory registers both components; they differ only in the
columns they can sort by.

Markup contract (partials/treatment-list.njk):
  - rows carry data-row-id, data-severity (the most serious treatment on
    the row), data-applied-severity, data-rec-severity, data-validation
    and one data-*-index rank per sortable column
  - rows carry data-search: name and citations, letters and digits only
  - filter checkboxes carry data-filter (a property name below)
  - the sort <select>'s option values are column keys
Each row carries its rank under every sort key (the rank already encodes
the direction: most severe, first appearance, A, newest or most cited
first), so reordering is a CSS `order` away and filtering is a class,
never a rebuild of the list.
*/
const SEVERITY_FILTERS = ['filterStop', 'filterWarning', 'filterCaution', 'filterNeutral', 'filterPositive'];
const RECOGNIZED_FILTERS = [
  'filterRecStop', 'filterRecWarning', 'filterRecCaution', 'filterRecNeutral', 'filterRecPositive',
];
const VALIDATION_FILTERS = ['filterAgree', 'filterUnverified', 'filterDisagree'];
const TIER_OF_FILTER = {
  filterStop: 'stop', filterWarning: 'warning', filterCaution: 'caution', filterNeutral: 'neutral',
  filterPositive: 'positive',
  filterRecStop: 'stop', filterRecWarning: 'warning', filterRecCaution: 'caution',
  filterRecNeutral: 'neutral', filterRecPositive: 'positive',
  filterAgree: 'agree', filterUnverified: 'unverified', filterDisagree: 'disagree',
};

// column key → the row's data attribute (camelCase) holding its rank
const AUTHORITIES_SORT_KEYS = {
  severity: 'severityIndex',
  date: 'dateIndex',
  mentions: 'mentionsIndex',
  name: 'nameIndex',
  appearance: 'appearanceIndex',
};
const CITED_BY_SORT_KEYS = {
  severity: 'severityIndex',
  recency: 'recencyIndex',
  mentions: 'mentionsIndex',
  name: 'nameIndex',
};

function treatmentList(sortKeys) {
  const state = {
    sortKeys,
    sortKey: 'severity',
    // the search box, reduced to letters and digits like data-search
    queryKey: '',
    totalCount: 0,
    visibleCount: 0,

    setQuery(event) {
      this.queryKey = (event.target.value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
      this.recount();
    },

    // ── filters ────────────────────────────────────────────────────────
    get filterChecked() {
      return this[this.$el.dataset.filter];
    },
    toggleFilter() {
      const prop = this.$el.dataset.filter;
      this[prop] = !this[prop];
    },
    get hasFilters() {
      return [...SEVERITY_FILTERS, ...RECOGNIZED_FILTERS, ...VALIDATION_FILTERS].some((p) => this[p]);
    },
    get filterSummaryClass() {
      return this.hasFilters ? 'list-filter__on' : '';
    },
    clearFilters() {
      [...SEVERITY_FILTERS, ...RECOGNIZED_FILTERS, ...VALIDATION_FILTERS].forEach((p) => {
        this[p] = false;
      });
    },

    // the ticked boxes of a group, and whether a value is one of them
    active(group) {
      return group.filter((p) => this[p]);
    },
    matches(active, value) {
      return active.some((p) => TIER_OF_FILTER[p] === value);
    },
    // The applied and recognized sections are a union: a row shows when
    // its applied treatment OR a treatment it recognizes has a ticked
    // severity (all rows when neither section has a tick). The
    // validation section narrows that further.
    rowVisible(el) {
      if (this.queryKey && !(el.dataset.search || '').includes(this.queryKey)) return false;
      const applied = this.active(SEVERITY_FILTERS);
      const recognized = this.active(RECOGNIZED_FILTERS);
      if (applied.length || recognized.length) {
        const hit =
          this.matches(applied, el.dataset.appliedSeverity) ||
          this.matches(recognized, el.dataset.recSeverity || 'none');
        if (!hit) return false;
      }
      const validation = this.active(VALIDATION_FILTERS);
      return !validation.length || this.matches(validation, el.dataset.validation);
    },
    // visibility is a class, not x-show: the rows also bind a style for
    // sorting, and Alpine's style bookkeeping would undo x-show's display
    get rowClass() {
      return this.rowVisible(this.$el) ? '' : 'row-hidden';
    },

    // ── sorting ────────────────────────────────────────────────────────
    setSort(event) {
      if (event.target.value in this.sortKeys) this.sortKey = event.target.value;
    },
    // the object form: a style string would rewrite the whole attribute
    get rowStyle() {
      return { order: parseInt(this.$el.dataset[this.sortKeys[this.sortKey]] || '0', 10) };
    },

    recount() {
      const rows = this.$root.querySelectorAll('[data-row-id]');
      this.visibleCount = Array.from(rows).filter((row) => this.rowVisible(row)).length;
    },

    init() {
      const rows = this.$root.querySelectorAll('[data-row-id]');
      this.totalCount = rows.length;
      this.visibleCount = rows.length;
      // keep the list at its first-rendered height so filtering rows out
      // does not reflow the page; the list may sit in a hidden tab panel
      // at init, so wait until it has a height
      const list = this.$root.querySelector('[role="list"]');
      if (list && typeof ResizeObserver !== 'undefined') {
        const observer = new ResizeObserver((entries) => {
          for (const e of entries) {
            if (e.contentRect.height > 0) {
              list.style.minHeight = `${e.contentRect.height}px`;
              observer.disconnect();
              return;
            }
          }
        });
        observer.observe(list);
      }
      [...SEVERITY_FILTERS, ...RECOGNIZED_FILTERS, ...VALIDATION_FILTERS].forEach((p) =>
        this.$watch(p, () => this.recount())
      );
    },
  };
  [...SEVERITY_FILTERS, ...RECOGNIZED_FILTERS, ...VALIDATION_FILTERS].forEach((p) => {
    state[p] = false;
  });
  return state;
}

document.addEventListener('alpine:init', () => {
  Alpine.data('authoritiesFilter', () => treatmentList(AUTHORITIES_SORT_KEYS));
  Alpine.data('citedByFilter', () => treatmentList(CITED_BY_SORT_KEYS));
});
