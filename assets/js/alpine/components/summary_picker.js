document.addEventListener('alpine:init', () => {
  Alpine.data('summaryPicker', (initialView) => ({
    view: initialView || 'most_severe',

    setView(value) {
      this.view = value;
    },

    onKeydown(event) {
      const tabs = Array.from(this.$root.querySelectorAll('[role="tab"]'));
      if (tabs.length === 0) return;
      const currentIdx = tabs.findIndex(
        (t) => t.getAttribute('aria-selected') === 'true'
      );
      let newIdx = currentIdx;
      switch (event.key) {
        case 'ArrowRight':
          newIdx = (currentIdx + 1) % tabs.length;
          break;
        case 'ArrowLeft':
          newIdx = (currentIdx - 1 + tabs.length) % tabs.length;
          break;
        case 'Home':
          newIdx = 0;
          break;
        case 'End':
          newIdx = tabs.length - 1;
          break;
        default:
          return;
      }
      event.preventDefault();
      const target = tabs[newIdx].dataset.view;
      if (target) {
        this.setView(target);
        tabs[newIdx].focus();
      }
    },
  }));
});
