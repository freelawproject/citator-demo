/*
Home page: the search box, the court picker, the severity filters,
"anchor opinions only" and pagination over the filtered cards.

Markup contract (src/index.njk):
  - cards carry data-court, data-tier, data-search, data-dh-severity,
    data-cr-severity
  - the anchors checkbox and the severity toggles carry data-filter (a
    property name)
  - picker tabs and panels carry data-tab-key; court rows carry
    data-court-key and data-court-name; group heads carry data-court-keys
    and data-court-names
Filter state lives in the URL query string (mirrored to sessionStorage
for back-navigation) so a filtered list can be shared and restored.
*/
const PAGE_SIZE = 10;
const STORAGE_KEY = 'citatorSearchFilter';
const DH_FILTERS = ['filterDhStop', 'filterDhWarning', 'filterDhCaution', 'filterDhNeutral'];
const CR_FILTERS = ['filterCrStop', 'filterCrWarning', 'filterCrCaution', 'filterCrNeutral'];
const TIERS = ['stop', 'warning', 'caution', 'neutral'];

function courtKeyOf(el) {
  const holder = el.closest('[data-court-key]');
  return holder ? holder.dataset.courtKey : '';
}

document.addEventListener('alpine:init', () => {
  Alpine.data('searchFilter', () => ({
    query: '',
    // the query reduced to letters and digits, matched against data-search
    queryKey: '',
    selectedCourts: [],
    filterDhStop: false,
    filterDhWarning: false,
    filterDhCaution: false,
    filterDhNeutral: false,
    filterCrStop: false,
    filterCrWarning: false,
    filterCrCaution: false,
    filterCrNeutral: false,
    filterAnchorsOnly: true,
    totalCount: 0,
    visibleCount: 0,
    page: 0,
    pageCount: 1,
    pickerOpen: false,
    pickerTab: 'federal_appellate',
    pickerQuery: '',
    // court key → display name, read off the picker markup in init()
    courtNames: {},

    // ── state changes ──────────────────────────────────────────────────
    // every change resets to the first page and is written to the URL
    changed() {
      this.page = 0;
      this.syncToURL();
      this.recount();
    },

    // typed text is reduced the way build_data.search_text reduces the
    // cards, so "103 F.3d 888" and "103f3d888" match the same case
    normalize(value) {
      return (value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
    },
    setQuery(event) {
      this.query = (event.target.value || '').trim().toLowerCase();
      this.queryKey = this.normalize(this.query);
      this.changed();
    },
    get filterChecked() {
      return this[this.$el.dataset.filter];
    },
    // the severity pill toggles
    get filterOn() {
      return this[this.$el.dataset.filter] ? 'true' : 'false';
    },
    get filterClass() {
      return this[this.$el.dataset.filter] ? 'is-on' : '';
    },
    toggleFilter() {
      const prop = this.$el.dataset.filter;
      this[prop] = !this[prop];
      this.changed();
    },
    setAnchorsOnly(event) {
      this.filterAnchorsOnly = event.target.checked;
      this.changed();
    },
    get hasSeverityFilters() {
      return [...DH_FILTERS, ...CR_FILTERS].some((p) => this[p]);
    },
    clearSeverityFilters() {
      [...DH_FILTERS, ...CR_FILTERS].forEach((p) => {
        this[p] = false;
      });
      this.changed();
    },

    // ── courts ─────────────────────────────────────────────────────────
    setCourts(keys) {
      this.selectedCourts = [...new Set(keys)];
      this.changed();
    },
    get courtSelected() {
      return this.selectedCourts.includes(courtKeyOf(this.$el));
    },
    toggleCourt(event) {
      const key = courtKeyOf(event.target);
      const rest = this.selectedCourts.filter((c) => c !== key);
      this.setCourts(event.target.checked ? [...rest, key] : rest);
    },
    removeCourt() {
      const key = courtKeyOf(this.$el);
      this.setCourts(this.selectedCourts.filter((c) => c !== key));
    },
    get hasSelectedCourts() {
      return this.selectedCourts.length > 0;
    },
    get courtSummary() {
      const n = this.selectedCourts.length;
      if (n === 0) return 'All courts';
      if (n === 1) return this.courtNames[this.selectedCourts[0]] || '1 court';
      return `${n} courts`;
    },
    courtKeysIn(scope) {
      return [...scope.querySelectorAll('[data-court-key]')].map((el) => el.dataset.courtKey);
    },
    checkAllCourts() {
      this.setCourts(this.courtKeysIn(this.$root));
    },
    clearAllCourts() {
      this.setCourts([]);
    },
    currentPanel() {
      return this.$root.querySelector(`[data-tab-key="${this.pickerTab}"]`);
    },
    checkTabCourts() {
      const panel = this.currentPanel();
      if (panel) this.setCourts([...this.selectedCourts, ...this.courtKeysIn(panel)]);
    },
    clearTabCourts() {
      const panel = this.currentPanel();
      if (!panel) return;
      const dropped = new Set(this.courtKeysIn(panel));
      this.setCourts(this.selectedCourts.filter((k) => !dropped.has(k)));
    },

    // a group head (a state, or a federal category) checks all its courts
    groupKeys(el) {
      return (el.dataset.courtKeys || '').split(',').filter(Boolean);
    },
    get groupAllSelected() {
      const keys = this.groupKeys(this.$el);
      return keys.length > 0 && keys.every((k) => this.selectedCourts.includes(k));
    },
    syncGroupBox() {
      const keys = this.groupKeys(this.$el);
      const some = keys.some((k) => this.selectedCourts.includes(k));
      this.$el.indeterminate = some && !keys.every((k) => this.selectedCourts.includes(k));
    },
    toggleGroup(event) {
      const keys = this.groupKeys(event.target);
      if (event.target.checked) {
        this.setCourts([...this.selectedCourts, ...keys]);
      } else {
        const dropped = new Set(keys);
        this.setCourts(this.selectedCourts.filter((k) => !dropped.has(k)));
      }
    },

    // ── picker dialog ──────────────────────────────────────────────────
    openPicker() {
      this.pickerOpen = true;
      document.body.classList.add('is-modal-open');
    },
    closePicker() {
      this.pickerOpen = false;
      this.pickerQuery = '';
      document.body.classList.remove('is-modal-open');
    },
    selectPickerTab() {
      this.pickerTab = this.$el.dataset.tabKey;
    },
    get pickerTabSelected() {
      return this.pickerTab === this.$el.dataset.tabKey ? 'true' : 'false';
    },
    get pickerTabClass() {
      return this.pickerTab === this.$el.dataset.tabKey ? 'is-active' : '';
    },
    get pickerPanelVisible() {
      return this.pickerTab === this.$el.dataset.tabKey;
    },
    setPickerQuery(event) {
      this.pickerQuery = (event.target.value || '').trim().toLowerCase();
    },
    // rows and groups hide while they do not match the typed name
    get courtVisible() {
      return !this.pickerQuery || (this.$el.dataset.courtName || '').includes(this.pickerQuery);
    },
    get groupVisible() {
      return !this.pickerQuery || (this.$el.dataset.courtNames || '').includes(this.pickerQuery);
    },
    get pickerTabEmpty() {
      if (!this.pickerQuery) return false;
      const panel = this.$el.closest('[data-tab-key]');
      if (!panel) return false;
      return ![...panel.querySelectorAll('[data-court-name]')].some((row) =>
        (row.dataset.courtName || '').includes(this.pickerQuery)
      );
    },

    // ── cards ──────────────────────────────────────────────────────────
    // a ticked severity in a group matches the card's value for that question
    tierHit(group, value) {
      return group.some((p, i) => this[p] && TIERS[i] === value);
    },
    rowMatches(el) {
      if (this.filterAnchorsOnly && el.dataset.tier !== 'anchor') return false;
      if (this.selectedCourts.length && !this.selectedCourts.includes(el.dataset.court)) return false;
      // the two severity groups are a union: a card shows when any
      // ticked severity matches its appeal or later treatment
      if (this.hasSeverityFilters) {
        const hit =
          this.tierHit(DH_FILTERS, el.dataset.dhSeverity) ||
          this.tierHit(CR_FILTERS, el.dataset.crSeverity);
        if (!hit) return false;
      }
      if (this.queryKey && !(el.dataset.search || '').includes(this.queryKey)) return false;
      return true;
    },
    // visible = passes the filters and falls on the current page; recount
    // stamps each matching card with its position in the filtered list
    get rowVisible() {
      if (!this.rowMatches(this.$el)) return false;
      const idx = parseInt(this.$el.dataset.pageIndex || '-1', 10);
      return idx >= this.page * PAGE_SIZE && idx < (this.page + 1) * PAGE_SIZE;
    },
    recount() {
      let count = 0;
      this.$root.querySelectorAll('[data-court]').forEach((row) => {
        if (this.rowMatches(row)) {
          row.dataset.pageIndex = String(count);
          count += 1;
        } else {
          row.dataset.pageIndex = '-1';
        }
      });
      this.visibleCount = count;
      this.pageCount = Math.max(1, Math.ceil(count / PAGE_SIZE));
      if (this.page > this.pageCount - 1) this.page = this.pageCount - 1;
    },

    // ── pagination ─────────────────────────────────────────────────────
    get hasPages() {
      return this.pageCount > 1;
    },
    get atFirstPage() {
      return this.page === 0;
    },
    get atLastPage() {
      return this.page >= this.pageCount - 1;
    },
    get pageLabel() {
      if (!this.visibleCount) return 'No opinions match';
      const from = this.page * PAGE_SIZE + 1;
      const to = Math.min(this.visibleCount, (this.page + 1) * PAGE_SIZE);
      return `${from}–${to} of ${this.visibleCount}`;
    },
    goToPage(page) {
      this.page = page;
      this.syncToURL();
      this.recount();
      const list = this.$root.querySelector('[role="list"]');
      if (list) list.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },
    nextPage() {
      if (!this.atLastPage) this.goToPage(this.page + 1);
    },
    prevPage() {
      if (!this.atFirstPage) this.goToPage(this.page - 1);
    },

    // ── URL state ──────────────────────────────────────────────────────
    activeTiers(group) {
      return group.filter((p) => this[p]).map((p) => TIERS[group.indexOf(p)]);
    },
    setTiers(group, tiers) {
      group.forEach((p, i) => {
        this[p] = tiers.includes(TIERS[i]);
      });
    },
    parseFromURL() {
      const params = new URLSearchParams(window.location.search);
      // with no filter params, fall back to the last saved state: the
      // browser can drop the query string on back-navigation
      if (!params.toString()) {
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (saved) new URLSearchParams(saved).forEach((v, k) => params.set(k, v));
      }
      this.query = (params.get('q') || '').trim().toLowerCase();
      this.queryKey = this.normalize(this.query);
      const courts = params.get('courts');
      this.selectedCourts = courts ? courts.split(',').filter(Boolean) : [];
      this.setTiers(DH_FILTERS, (params.get('dh_sev') || '').split(','));
      this.setTiers(CR_FILTERS, (params.get('cr_sev') || '').split(','));
      this.filterAnchorsOnly = params.get('anchors') !== '0';
      this.page = Math.max(0, parseInt(params.get('page') || '1', 10) - 1);
      if (!window.location.search && params.toString()) {
        window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
      }
    },
    syncToURL() {
      const params = new URLSearchParams();
      if (this.query) params.set('q', this.query);
      if (this.selectedCourts.length) params.set('courts', this.selectedCourts.join(','));
      const dh = this.activeTiers(DH_FILTERS);
      if (dh.length) params.set('dh_sev', dh.join(','));
      const cr = this.activeTiers(CR_FILTERS);
      if (cr.length) params.set('cr_sev', cr.join(','));
      if (!this.filterAnchorsOnly) params.set('anchors', '0');
      if (this.page > 0) params.set('page', String(this.page + 1));
      const qs = params.toString();
      if (qs) sessionStorage.setItem(STORAGE_KEY, qs);
      else sessionStorage.removeItem(STORAGE_KEY);
      const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
      if (window.location.pathname + window.location.search !== url) {
        window.history.replaceState(null, '', url);
      }
    },

    init() {
      this.totalCount = this.$root.querySelectorAll('[data-court]').length;
      this.$root.querySelectorAll('li[data-court-key]').forEach((el) => {
        this.courtNames[el.dataset.courtKey] =
          el.querySelector('label')?.textContent.trim() || el.dataset.courtKey;
      });
      this.parseFromURL();
      this.recount();
      // a page restored from the back/forward cache keeps its old state;
      // the URL still carries the saved filters, so read them again
      window.addEventListener('pageshow', (e) => {
        if (e.persisted) {
          this.parseFromURL();
          this.recount();
        }
      });
    },
  }));
});
