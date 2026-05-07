document.addEventListener('alpine:init', () => {
  Alpine.data('citedByFilter', () => ({
    filterStop: false,
    filterWarning: false,
    filterCaution: false,
    filterNeutral: false,
    filterAgree: false,
    filterUnverified: false,
    filterDisagree: false,
    sortBy: 'severity',
    totalCount: 0,
    visibleCount: 0,

    toggleFilter(prop) {
      this[prop] = !this[prop];
    },

    setSort(value) {
      this.sortBy = value;
    },

    rowVisible(el) {
      const sev = el.dataset.severity;
      const val = el.dataset.validation;
      const noSevFilter =
        !this.filterStop && !this.filterWarning && !this.filterCaution && !this.filterNeutral;
      const noValFilter = !this.filterAgree && !this.filterUnverified && !this.filterDisagree;

      if (!noSevFilter) {
        const sevMatch =
          (this.filterStop && sev === 'stop') ||
          (this.filterWarning && sev === 'warning') ||
          (this.filterCaution && sev === 'caution') ||
          (this.filterNeutral && sev === 'neutral');
        if (!sevMatch) return false;
      }

      if (!noValFilter) {
        const valMatch =
          (this.filterAgree && val === 'agree') ||
          (this.filterUnverified && val === 'unverified') ||
          (this.filterDisagree && val === 'disagree');
        if (!valMatch) return false;
      }

      return true;
    },

    rowOrder(el) {
      if (this.sortBy === 'recency') {
        return `order: ${el.dataset.recencyIndex}`;
      }
      return '';
    },

    recount() {
      const rows = this.$root.querySelectorAll('[data-row-id]');
      let count = 0;
      rows.forEach((row) => {
        if (this.rowVisible(row)) count += 1;
      });
      this.visibleCount = count;
    },

    init() {
      const rows = this.$root.querySelectorAll('[data-row-id]');
      this.totalCount = rows.length;
      this.visibleCount = rows.length;

      const list = this.$root.querySelector('ul[role="list"]');
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

      const watch = (prop) => this.$watch(prop, () => this.recount());
      ['filterStop', 'filterWarning', 'filterCaution', 'filterNeutral',
       'filterAgree', 'filterUnverified', 'filterDisagree'].forEach(watch);
    },
  }));
});
