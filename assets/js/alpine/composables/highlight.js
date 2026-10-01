/*
Scroll an element into view and flash it with a CSS animation class. The
class is removed and re-added around a forced reflow so the animation
restarts on a repeat call to the same element.
*/
const HIGHLIGHT_MS = 3000;

function highlightElement(el, className, { block = 'center' } = {}) {
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block });
  el.classList.remove(className);
  void el.offsetHeight;
  el.classList.add(className);
  setTimeout(() => el.classList.remove(className), HIGHLIGHT_MS);
}
