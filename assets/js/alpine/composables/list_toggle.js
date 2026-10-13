/*
"+N" / "less" toggle for a clamped list (citations, case numbers).
The extra entries are hidden by CSS (.cite-extra, and .cite-fit-hidden set
by assets/js/cite_fit.js) and revealed by the `is-expanded` class on the
enclosing cell, the nearest ancestor carrying `data-cite-cell`, so the
list keeps no state. Collapsing dispatches `cite-list:collapse` on the
cell, which cite_fit.js listens for.

Usage:
  <dd data-cite-cell>
    <span class="cite-list">first, second, third<span class="cite-extra">, fourth</span></span>
    <button type="button" x-data="listToggle" x-on:click.stop.prevent="toggle"
            data-more="+1" data-less="less">+1</button>
  </dd>
*/
document.addEventListener('alpine:init', () => {
  Alpine.data('listToggle', () => ({
    toggle(event) {
      const button = event.currentTarget;
      const cell = button.closest('[data-cite-cell]');
      if (!cell) return;
      const expanded = cell.classList.toggle('is-expanded');
      button.textContent = expanded ? button.dataset.less : button.dataset.more;
      if (!expanded) cell.dispatchEvent(new CustomEvent('cite-list:collapse', { bubbles: true }));
    },
  }));
});
