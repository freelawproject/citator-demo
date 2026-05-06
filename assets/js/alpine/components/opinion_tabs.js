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

    handleHash(hash) {
      if (VALID_TABS.includes(hash)) {
        this.activeTab = hash;
      } else if (hash.startsWith('section-')) {
        this.activeTab = 'opinion';
        this.$nextTick(() => {
          const el = document.getElementById(hash);
          if (!el) return;
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Re-trigger the flash animation even when navigating to the
          // same section twice in a row.
          el.classList.remove('section-flash');
          void el.offsetHeight;
          el.classList.add('section-flash');
        });
      }
    },

    flashQuoteInBody(quote) {
      this.activeTab = 'opinion';
      this.$nextTick(() => {
        const body = this.$root.querySelector('.opinion-body');
        if (!body) return;
        const lower = quote.toLowerCase();
        const paragraphs = body.querySelectorAll('p');
        for (const p of paragraphs) {
          if (p.textContent.toLowerCase().includes(lower)) {
            p.scrollIntoView({ behavior: 'smooth', block: 'start' });
            p.classList.remove('quote-flash');
            void p.offsetHeight;
            p.classList.add('quote-flash');
            setTimeout(() => p.classList.remove('quote-flash'), 1800);
            return;
          }
        }
      });
    },

    init() {
      const hash = window.location.hash.slice(1);
      if (hash) this.handleHash(hash);
      window.addEventListener('hashchange', () => {
        this.handleHash(window.location.hash.slice(1));
      });
      this.$root.addEventListener('quote-click', (e) => {
        if (e.detail && e.detail.quote) this.flashQuoteInBody(e.detail.quote);
      });
    },
  }));
});
