/* Public demo: wire navigation affordances and no-op Mac-only actions with clear copy. */
(function () {
  'use strict';
  if (document.documentElement.dataset.demoMode !== 'true') return;

  const FOCUS_FOR = {
    home: 'home',
    overview: 'home',
    sources: 'home',
    settings: 'home',
    heatmap: 'markets',
    screener: 'markets',
    crypto: 'markets',
    tape: 'markets',
    news: 'markets',
    macro: 'markets',
    markets: 'markets',
    learning: 'markets',
    company: 'company',
    intelligence: 'company',
    forecast: 'company',
    comparison: 'company',
    indicators: 'company',
    valuation: 'company',
    accuracy: 'company',
    research: 'research',
    reports: 'research',
    portfolio: 'research',
    alerts: 'research',
    calendar: 'research',
  };

  function syncFocusNav(view) {
    const focus = FOCUS_FOR[view] || view;
    document.querySelectorAll('[data-focus-view]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.focusView === focus));
    });
    const nav = document.querySelector('.focus-nav');
    const pill = document.getElementById('nav-indicator');
  const button = nav?.querySelector(`[data-focus-view="${focus}"]`);
    if (pill && nav && button) {
      const box = button.getBoundingClientRect();
      const parent = nav.getBoundingClientRect();
      pill.style.width = box.width + 'px';
      pill.style.transform = 'translateX(' + (box.left - parent.left) + 'px)';
      pill.style.opacity = '1';
    }
  }

  function toast(msg) {
    if (typeof window.toast === 'function') window.toast(msg);
  }

  const MAC_ONLY = new Map([
    ['heat-refresh', 'Directory history is already in this demo bundle. Load all company history runs on your Mac.'],
    ['learning40-refresh', 'Training from live prices needs server.py on your Mac.'],
    ['learning40-train', 'Evaluate from saved prices needs your Mac ledger. Browse Overview and Heatmap here.'],
    ['v3-listing-refresh', 'SEC directory refresh runs on your Mac. Demo search still uses the bundled watchlist slice.'],
    ['v3-refresh-statements', 'Expanded SEC accounts need the Mac server.'],
    ['massive-test', 'Massive history tests stay on your Mac. Charts here use the bundled snapshot.'],
    ['save-key', 'Provider keys are not stored on this public demo.'],
    ['clear-key', 'No Finnhub key is stored on this host.'],
    ['massive-save-key', 'Provider keys are not stored on this public demo.'],
    ['massive-clear-key', 'No Massive key is stored on this host.'],
  ]);

  function setupGuards() {
    document.addEventListener(
      'click',
      (event) => {
        const button = event.target.closest('button, .primary-btn, .ghost-btn, .link-btn');
        if (!button || button.disabled) return;
        const id = button.id;
        if (MAC_ONLY.has(id)) {
          event.preventDefault();
          event.stopImmediatePropagation();
          toast(MAC_ONLY.get(id));
          return;
        }
        if (id === 'local-audit-run') {
          event.preventDefault();
          event.stopImmediatePropagation();
          const out = document.getElementById('local-audit-output');
          if (out) {
            out.replaceChildren();
            for (const row of [
              ['✓', 'Demo snapshot', 'Bundled heatmap, quotes and charts'],
              ['✓', 'Website files', 'Static portfolio host'],
              ['—', 'Mac database', 'Run server.py locally for full checks'],
            ]) {
              const line = document.createElement('div');
              line.className = 'audit-line';
              const title = document.createElement('strong');
              title.textContent = row[0] + ' ' + row[1];
              const detail = document.createElement('span');
              detail.textContent = row[2];
              line.append(title, detail);
              out.append(line);
            }
            const note = document.createElement('p');
            note.textContent = 'Public demo file check · no Mac database attached.';
            out.append(note);
          }
          return;
        }
      },
      true
    );
  }

  function wireDeskShortcuts() {
    const jumpHeat = document.getElementById('desk-open-heat');
    jumpHeat?.addEventListener('click', () => {
      if (typeof changeView === 'function') changeView('heatmap');
    });
    document.querySelectorAll('[data-pro-nav]').forEach((button) => {
      button.addEventListener('click', () => {
        const view = button.dataset.proNav;
        if (view && typeof changeView === 'function') changeView(view);
      });
    });
  }

  function settingsTour() {
    try {
      if (localStorage.getItem('md-demo-settings-hint') === '1') return;
    } catch {
      return;
    }
    const observer = new MutationObserver(() => {
      const active = document.querySelector('.view.active')?.id === 'view-settings';
      if (!active) return;
      observer.disconnect();
      try {
        localStorage.setItem('md-demo-settings-hint', '1');
      } catch {}
      const showcase = document.getElementById('showcase61');
      showcase?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      window.MarketDeskDemoPolish?.refresh();
      toast('Sixth-form walkthrough: use Start guided demo, then explore Overview and Heatmap.');
    });
    for (const view of document.querySelectorAll('.view')) {
      observer.observe(view, { attributes: true, attributeFilter: ['class'] });
    }
  }

  function onReady() {
    setupGuards();
    wireDeskShortcuts();
    settingsTour();
    const view = window.E?.view || 'overview';
    syncFocusNav(view);
    window.addEventListener('marketdesk:ready', () => syncFocusNav(window.E?.view || 'overview'));
    const nav = document.getElementById('nav');
    if (nav) {
      new MutationObserver(() => {
        const selected = document.querySelector('#nav .nav-btn.active')?.dataset.view;
        if (selected) syncFocusNav(selected);
      }).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady);
  else onReady();

  window.MarketDeskDemo = { syncFocusNav, FOCUS_FOR };
})();