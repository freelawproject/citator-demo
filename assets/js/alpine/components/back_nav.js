/*
"Back" control. Goes back one step when the previous page is on this site
(so an opinion's selected tab, kept in the URL hash, is restored);
otherwise goes to the home page.

Usage:
  <a href="/" x-data="backNav" x-on:click.prevent="goBack" class="back-nav">Back</a>
*/
document.addEventListener('alpine:init', () => {
  Alpine.data('backNav', () => ({
    goBack() {
      let sameSite = false;
      try {
        sameSite = document.referrer !== '' && new URL(document.referrer).origin === window.location.origin;
      } catch (e) {
        sameSite = false;
      }
      if (sameSite && window.history.length > 1) {
        window.history.back();
      } else {
        window.location.href = '/';
      }
    },
  }));
});
