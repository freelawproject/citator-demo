/*
In-page links (href="#…") replace the current history entry instead of
adding one, so the browser's Back button always returns to the previous
page, on the tab it was left on. The target still scrolls into view and
receives focus, and a `hashchange` event is dispatched so the opinion
page's tab logic reacts as it would to a real hash change.

Plain script, no Alpine. Runs after a component's own click handler on
the same link (those live on ancestors inside the page), and leaves a
click alone once a handler has called preventDefault.
*/
document.addEventListener('click', (event) => {
  if (event.defaultPrevented || event.button !== 0) return;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest('a[href^="#"]');
  if (!link) return;
  event.preventDefault();

  const hash = link.getAttribute('href').slice(1);
  const base = window.location.pathname + window.location.search;
  history.replaceState(null, '', hash ? `${base}#${hash}` : base);
  window.dispatchEvent(new HashChangeEvent('hashchange'));

  // scroll on the next frame so a panel a component has just shown is laid out
  requestAnimationFrame(() => {
    const target = hash && hash !== 'top' ? document.getElementById(hash) : null;
    if (!target) {
      window.scrollTo({ top: 0 });
      return;
    }
    target.scrollIntoView({ block: 'start' });
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
    target.focus({ preventScroll: true });
  });
});
