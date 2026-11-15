/* Single release label for user-visible chrome (keep in sync with server.py VERSION). */
(function () {
  'use strict';
  const version = '6.8.0';
  window.MarketDeskRelease = { version, name: 'Market Desk' };

  function stampVersion() {
    document.querySelectorAll('[data-md-version], .brand-version').forEach((el) => {
      el.textContent = version;
    });
    if (document.title.startsWith('Market Desk')) {
      document.title = 'Market Desk ' + version + ' — Your research workspace';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', stampVersion);
  else stampVersion();
})();