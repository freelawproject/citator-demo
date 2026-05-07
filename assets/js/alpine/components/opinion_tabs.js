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
          if (!p.textContent.toLowerCase().includes(lower)) continue;

          // Wrap each text-node slice that falls within the quote range
          // in its own .quote-flash span. Handles quotes that cross
          // inline elements (e.g., a cross-citation rendered as <a>).
          const spans = wrapQuoteAcrossTextNodes(p, quote);
          if (spans.length === 0) return;
          spans[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
          // Force reflow before adding the class so the animation
          // restarts when the same quote is clicked twice in a row.
          spans.forEach((s) => s.classList.remove('quote-flash'));
          void spans[0].offsetHeight;
          spans.forEach((s) => s.classList.add('quote-flash'));
          setTimeout(() => {
            spans.forEach((s) => s.classList.remove('quote-flash'));
            unwrapSpans(spans);
          }, 3500);
          return;
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

// Walk a paragraph's text nodes, find where `quote` lies in the
// concatenated text, and wrap each text-node slice that falls within
// the quote range in its own <span>. Handles quotes that cross inline
// elements (e.g., a cross-citation rendered as <a>) by producing one
// span per crossed text node, all of which animate together.
function wrapQuoteAcrossTextNodes(p, quote) {
  const lower = quote.toLowerCase();
  const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  let flatText = '';
  let node;
  while ((node = walker.nextNode())) {
    textNodes.push({
      node,
      start: flatText.length,
      end: flatText.length + node.textContent.length,
    });
    flatText += node.textContent;
  }

  const startIdx = flatText.toLowerCase().indexOf(lower);
  if (startIdx < 0) return [];
  const endIdx = startIdx + quote.length;

  const spans = [];
  // Iterate over a snapshot — we mutate the DOM (replaceChild) during
  // the loop, but each entry's `node` reference is stable.
  for (const tn of textNodes) {
    if (tn.end <= startIdx || tn.start >= endIdx) continue;

    const localStart = Math.max(0, startIdx - tn.start);
    const localEnd = Math.min(
      tn.node.textContent.length,
      endIdx - tn.start
    );
    const text = tn.node.textContent;
    const before = text.slice(0, localStart);
    const match = text.slice(localStart, localEnd);
    const after = text.slice(localEnd);

    const span = document.createElement('span');
    span.textContent = match;
    const fragment = document.createDocumentFragment();
    if (before) fragment.appendChild(document.createTextNode(before));
    fragment.appendChild(span);
    if (after) fragment.appendChild(document.createTextNode(after));
    tn.node.parentNode.replaceChild(fragment, tn.node);
    spans.push(span);
  }
  return spans;
}

function unwrapSpans(spans) {
  for (const span of spans) {
    const parent = span.parentNode;
    if (!parent) continue;
    while (span.firstChild) parent.insertBefore(span.firstChild, span);
    parent.removeChild(span);
    parent.normalize();
  }
}
