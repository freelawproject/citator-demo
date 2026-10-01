/*
"+N" / "less" toggle for a clamped list (citations, "also cited as" forms).
The extra entries are hidden by CSS (.cite-extra) and revealed by the
`is-expanded` class on the enclosing <dd>, so the list keeps no state.

Usage:
  <dd>
    <span class="cite-list">first, second, third<span class="cite-extra">, fourth</span></span>
    <button type="button" x-data="listToggle" x-on:click.stop.prevent="toggle"
            data-more="+1" data-less="less">+1</button>
  </dd>
*/
document.addEventListener('alpine:init', () => {
  Alpine.data('listToggle', () => ({
    toggle(event) {
      const button = event.currentTarget;
      const cell = button.closest('dd');
      if (!cell) return;
      const expanded = cell.classList.toggle('is-expanded');
      button.textContent = expanded ? button.dataset.less : button.dataset.more;
    },
  }));
});
