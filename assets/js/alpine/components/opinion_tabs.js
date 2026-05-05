document.addEventListener('alpine:init', () => {
  const VALID_TABS = ['opinion', 'authorities', 'cited-by'];

  Alpine.data('opinionTabs', () => ({
    activeTab: 'opinion',

    setTab(id) {
      if (!VALID_TABS.includes(id)) return;
      this.activeTab = id;
      history.replaceState(null, '', `#${id}`);
    },

    onKeydown(event) {
      const tabs = Array.from(this.$root.querySelectorAll('[role="tab"]'));
      const currentIdx = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
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
      const tabId = tabs[newIdx].id.replace(/^tab-/, '');
      this.setTab(tabId);
      tabs[newIdx].focus();
    },

    init() {
      const hash = window.location.hash.slice(1);
      if (VALID_TABS.includes(hash)) this.activeTab = hash;
      window.addEventListener('hashchange', () => {
        const newHash = window.location.hash.slice(1);
        if (VALID_TABS.includes(newHash)) this.activeTab = newHash;
      });
    },
  }));
});
