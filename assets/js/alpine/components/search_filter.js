document.addEventListener('alpine:init', () => {
  Alpine.data('searchFilter', () => ({
    selectedCourts: [],
    filterStop: false,
    filterWarning: false,
    filterCaution: false,
    filterNeutral: false,
    totalCount: 0,
    visibleCount: 0,

    toggleCourt(court, checked) {
      this.selectedCourts = checked
        ? [...this.selectedCourts.filter((c) => c !== court), court]
        : this.selectedCourts.filter((c) => c !== court);
    },

    rowVisible(el) {
      if (this.selectedCourts.length > 0 && !this.selectedCourts.includes(el.dataset.court)) return false;
      const noTierFilter =
        !this.filterStop && !this.filterWarning && !this.filterCaution && !this.filterNeutral;
      if (noTierFilter) return true;
      const sev = el.dataset.severity;
      if (this.filterStop && sev === 'stop') return true;
      if (this.filterWarning && sev === 'warning') return true;
      if (this.filterCaution && sev === 'caution') return true;
      if (this.filterNeutral && sev === 'neutral') return true;
      return false;
    },

    recount() {
      const rows = this.$root.querySelectorAll('[data-severity]');
      let count = 0;
      rows.forEach((row) => {
        if (this.rowVisible(row)) count += 1;
      });
      this.visibleCount = count;
    },

    init() {
      const rows = this.$root.querySelectorAll('[data-severity]');
      this.totalCount = rows.length;
      this.visibleCount = rows.length;
      this.$watch('selectedCourts', () => this.recount());
      this.$watch('filterStop', () => this.recount());
      this.$watch('filterWarning', () => this.recount());
      this.$watch('filterCaution', () => this.recount());
      this.$watch('filterNeutral', () => this.recount());
    },
  }));
});
