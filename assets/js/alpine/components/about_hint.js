/*
First-visit hint on the header's "About this citator" link: a small
callout under the link until it is dismissed, the link is followed, or
the About page is opened. Remembered in localStorage.

Usage (layouts/base.njk):
  <div x-data="aboutHint" class="about-hint">
    <a href="/about/" x-bind:class="hintLinkClass" x-on:click="dismiss">…</a>
    <div x-show="open" x-cloak class="about-hint__bubble">
      … <button x-on:click="dismiss">…</button>
    </div>
  </div>
*/
const ABOUT_SEEN_KEY = 'citator-about-seen';

document.addEventListener('alpine:init', () => {
  Alpine.data('aboutHint', () => ({
    open: false,

    get hintLinkClass() {
      return this.open ? 'about-hint__link--active' : '';
    },

    dismiss() {
      this.open = false;
      try {
        localStorage.setItem(ABOUT_SEEN_KEY, '1');
      } catch (e) {
        // storage unavailable: the hint simply shows again next time
      }
    },

    init() {
      if (window.location.pathname === '/about/') {
        this.dismiss();
        return;
      }
      let seen = '1';
      try {
        seen = localStorage.getItem(ABOUT_SEEN_KEY);
      } catch (e) {
        seen = '1';
      }
      this.open = !seen;
    },
  }));
});
