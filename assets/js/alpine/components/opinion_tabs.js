/*
Opinion page: the tab bar, the compact case bar, in-page jumps and the
occurrence navigator for citations in the text.

Markup contract (src/opinion.njk):
  - tab buttons carry data-tab; panels carry data-tab
  - the metadata card is x-ref="caseCard"
  - citations in the text are `a.cited-case-wrap[data-group][data-name][data-url]`
    linking to `#authority-N`
  - "Read in the opinion" buttons carry data-quote
Requires composables/highlight.js.
*/
const VALID_TABS = ['opinion', 'authorities', 'cited-by', 'history'];
const ACTIVE_TAB_CLASS = 'border-primary-600 text-primary-700';
const INACTIVE_TAB_CLASS =
  'border-transparent text-greyscale-600 hover:text-greyscale-900 hover:border-greyscale-300';
const QUOTE_FLASH_MS = 3500;
// Inline elements whose text is not opinion prose: citation severity
// markers and footnote marks. Skipped when matching a quote against the text.
const NON_PROSE = '.cited-case__severity, sup.fnref';

document.addEventListener('alpine:init', () => {
  Alpine.data('opinionTabs', () => ({
    activeTab: 'opinion',
    // the page's root element. Handlers on elements inside a nested
    // component scope (the tab lists) see that scope as $root, so the
    // page root is captured once at init.
    pageRoot: null,
    // true once the metadata card has scrolled above the viewport
    caseBarVisible: false,
    // the citation whose mentions are being stepped through
    occNav: { open: false, n: 0, name: '', url: '', index: 0, total: 0 },

    // ── tabs ───────────────────────────────────────────────────────────
    get tabSelected() {
      return this.$el.dataset.tab === this.activeTab ? 'true' : 'false';
    },
    get tabIndex() {
      return this.$el.dataset.tab === this.activeTab ? 0 : -1;
    },
    get tabClass() {
      return this.$el.dataset.tab === this.activeTab ? ACTIVE_TAB_CLASS : INACTIVE_TAB_CLASS;
    },
    get tabCountClass() {
      return this.$el.dataset.tab === this.activeTab ? 'tab-count--active' : '';
    },
    get panelVisible() {
      return this.$el.dataset.tab === this.activeTab;
    },

    showTab(id) {
      if (!VALID_TABS.includes(id)) return;
      this.activeTab = id;
      history.replaceState(null, '', `#${id}`);
    },
    selectTab() {
      this.showTab(this.$el.dataset.tab);
    },
    showOpinionTab() {
      this.activeTab = 'opinion';
    },

    onKeydown(event) {
      const tabs = Array.from(this.pageRoot.querySelectorAll('[role="tab"]'));
      const current = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
      let next = current;
      switch (event.key) {
        case 'ArrowRight':
          next = (current + 1) % tabs.length;
          break;
        case 'ArrowLeft':
          next = (current - 1 + tabs.length) % tabs.length;
          break;
        case 'Home':
          next = 0;
          break;
        case 'End':
          next = tabs.length - 1;
          break;
        default:
          return;
      }
      event.preventDefault();
      this.showTab(tabs[next].dataset.tab);
      tabs[next].focus();
    },

    // ── case bar ───────────────────────────────────────────────────────
    get caseBarClass() {
      return this.caseBarVisible ? 'case-bar--visible' : '';
    },
    get caseBarHidden() {
      return this.caseBarVisible ? 'false' : 'true';
    },

    watchCaseCard() {
      const card = this.$refs.caseCard;
      if (!card || !('IntersectionObserver' in window)) return;
      const observer = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          this.caseBarVisible = !entry.isIntersecting && entry.boundingClientRect.bottom < 0;
        },
        { threshold: 0 }
      );
      observer.observe(card);
    },

    // ── in-page jumps ──────────────────────────────────────────────────
    // The URL hash names a tab, a writing section, an Authorities row, or
    // a quoted passage (`q=`).
    handleHash(hash) {
      if (VALID_TABS.includes(hash)) {
        this.activeTab = hash;
      } else if (hash.startsWith('q=')) {
        let quote = '';
        try {
          quote = decodeURIComponent(hash.slice(2));
        } catch (e) {
          quote = '';
        }
        if (quote) this.flashQuoteInBody(quote);
      } else if (hash.startsWith('section-')) {
        this.activeTab = 'opinion';
        this.$nextTick(() => {
          const el = document.getElementById(hash);
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      } else if (hash.startsWith('authority-')) {
        this.activeTab = 'authorities';
        // scroll after the panel switch has been laid out (two frames), so
        // the centre is computed against the Authorities list
        this.$nextTick(() =>
          requestAnimationFrame(() =>
            requestAnimationFrame(() => highlightElement(document.getElementById(hash), 'row-flash'))
          )
        );
      }
    },

    // a "Read in the opinion" button on an evidence card
    readQuote() {
      this.flashQuoteInBody(this.$el.dataset.quote || '');
    },

    // a citation in the text opens the occurrence navigator; the href
    // still points at the Authorities row for no-script use
    onCitationClick(event) {
      const link = event.target.closest('a.cited-case-wrap');
      if (!link) return;
      const href = link.getAttribute('href') || '';
      if (!href.startsWith('#authority-')) return;
      event.preventDefault();
      this.occOpen(link);
    },

    // ── occurrence navigator ───────────────────────────────────────────
    get occNavOpen() {
      return this.occNav.open;
    },
    get occNavName() {
      return this.occNav.name;
    },
    get occNavUrl() {
      return this.occNav.url;
    },
    get occNavHasUrl() {
      return this.occNav.url !== '';
    },
    get occNavNoUrl() {
      return this.occNav.url === '';
    },
    get occNavCount() {
      if (!this.occNav.total) return '';
      return `Occurrence ${this.occNav.index + 1} of ${this.occNav.total}`;
    },

    // every mention of authority n, in document order
    occMentions(n) {
      return Array.from(this.pageRoot.querySelectorAll(`.opinion-body a.cited-case-wrap[data-group="${n}"]`));
    },

    occOpen(link) {
      const n = parseInt(link.dataset.group, 10);
      const mentions = this.occMentions(n);
      if (!mentions.length) return;
      this.occNav = {
        open: true,
        n,
        name: link.dataset.name || '',
        url: link.dataset.url || '',
        index: Math.max(0, mentions.indexOf(link)),
        total: mentions.length,
      };
      this.occShow();
    },
    occShow() {
      highlightElement(this.occMentions(this.occNav.n)[this.occNav.index], 'mention-flash');
    },
    occNext() {
      if (!this.occNav.total) return;
      this.occNav.index = (this.occNav.index + 1) % this.occNav.total;
      this.occShow();
    },
    occPrev() {
      if (!this.occNav.total) return;
      this.occNav.index = (this.occNav.index - 1 + this.occNav.total) % this.occNav.total;
      this.occShow();
    },
    occToRow() {
      const hash = `authority-${this.occNav.n}`;
      history.replaceState(null, '', `#${hash}`);
      this.handleHash(hash);
    },
    occClose() {
      this.occNav = { open: false, n: 0, name: '', url: '', index: 0, total: 0 };
    },

    // ── quote lookup ───────────────────────────────────────────────────
    // Find a quoted passage in the opinion text, wrap it and flash it.
    // Two passes over every paragraph and block quote: the whole quote
    // first, then only its opening words, so an earlier sentence that
    // merely starts the same way never wins over the exact one.
    flashQuoteInBody(quote) {
      this.activeTab = 'opinion';
      this.$nextTick(() => {
        const body = this.pageRoot.querySelector('.opinion-body');
        if (!body) return;
        const blocks = body.querySelectorAll('p, blockquote');
        let spans = [];
        for (const allowPrefix of [false, true]) {
          for (const block of blocks) {
            spans = wrapQuoteInBlock(block, quote, allowPrefix);
            if (spans.length) break;
          }
          if (spans.length) break;
        }
        if (!spans.length) return;
        spans[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        spans.forEach((s) => s.classList.add('quote-flash'));
        setTimeout(() => unwrapSpans(spans), QUOTE_FLASH_MS);
      });
    },

    init() {
      this.pageRoot = this.$root;
      const hash = window.location.hash.slice(1);
      if (hash) this.handleHash(hash);
      window.addEventListener('hashchange', () => this.handleHash(window.location.hash.slice(1)));
      this.$root.addEventListener('click', (e) => this.onCitationClick(e));
      this.watchCaseCard();
    },
  }));
});

// ── text matching ──────────────────────────────────────────────────────
// Matching is normalised: lower case, straight quotes and dashes, single
// spaces. The map from normalised offsets back to the original text lets
// the matched range be wrapped in place.
function normaliseChar(ch) {
  switch (ch) {
    case '‘': case '’': case '‚': case '′': return "'";
    case '“': case '”': case '„': case '″': return '"';
    case '–': case '—': return '-';
    case ' ': return ' ';
    default: return ch.toLowerCase();
  }
}

function normaliseText(text) {
  const norm = [];
  const map = [];
  let lastSpace = true;
  for (let i = 0; i < text.length; i += 1) {
    let ch = text[i];
    if (/\s/.test(ch)) {
      if (lastSpace) continue;
      ch = ' ';
      lastSpace = true;
    } else {
      lastSpace = false;
      ch = normaliseChar(ch);
    }
    norm.push(ch);
    map.push(i);
  }
  return { text: norm.join(''), map };
}

function normaliseQuote(quote) {
  return normaliseText(quote).text.trim().replace(/^["'“‘]+|["'”’.,;]+$/g, '').trim();
}

// Wrap the part of `block`'s text that matches `quote` in <span>s, one per
// text node the match crosses (a citation link inside the quote splits
// it). Returns the spans, or [] when the quote is not in this block.
function wrapQuoteInBlock(block, quote, allowPrefix) {
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) =>
      n.parentElement && n.parentElement.closest(NON_PROSE) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  });
  const textNodes = [];
  let flat = '';
  let node;
  while ((node = walker.nextNode())) {
    textNodes.push({ node, start: flat.length, end: flat.length + node.textContent.length });
    flat += node.textContent;
  }
  const { text: norm, map } = normaliseText(flat);
  const target = normaliseQuote(quote);
  if (!target) return [];
  let idx = norm.indexOf(target);
  let length = target.length;
  if (idx < 0 && allowPrefix && target.length > 60) {
    const head = target.slice(0, 60);
    idx = norm.indexOf(head);
    length = head.length;
  }
  if (idx < 0) return [];
  const start = map[idx];
  const end = map[idx + length - 1] + 1;

  const spans = [];
  for (const tn of textNodes) {
    if (tn.end <= start || tn.start >= end) continue;
    const text = tn.node.textContent;
    const localStart = Math.max(0, start - tn.start);
    const localEnd = Math.min(text.length, end - tn.start);
    const span = document.createElement('span');
    span.textContent = text.slice(localStart, localEnd);
    const fragment = document.createDocumentFragment();
    if (localStart) fragment.appendChild(document.createTextNode(text.slice(0, localStart)));
    fragment.appendChild(span);
    if (localEnd < text.length) fragment.appendChild(document.createTextNode(text.slice(localEnd)));
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
