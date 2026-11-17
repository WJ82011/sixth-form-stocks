/* Public demo: navigation declutter, Mac-only guards, honest chrome re-assert. */
(function () {
  'use strict';

  function isDemo() {
    if (document.documentElement.dataset.demoMode === 'true') return true;
    if (window.MarketDeskHost?.demoMode) return true;
    // Same helper as cloud-host — works on bare `/` when production hostname auto-enables.
    return Boolean(window.MarketDeskPublicHost?.resolve?.(location)?.demoMode);
  }

  // Thin / Mac-only / crashy on the static host — keep Mac path intact when not in demo.
  const SOFT_HIDE = new Set(['learning', 'accuracy', 'valuation', 'calendar', 'reports', 'indicators']);

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
    ['v3-listing-refresh', 'SEC directory refresh runs on your Mac. Demo search still uses the bundled watchlist slice.'],
    ['v3-refresh-statements', 'Expanded SEC accounts need the Mac server.'],
    ['massive-test', 'Massive history tests stay on your Mac. Charts here use the bundled snapshot.'],
    ['save-key', 'Provider keys are not stored on this public demo.'],
    ['clear-key', 'No Finnhub key is stored on this host.'],
    ['massive-save-key', 'Provider keys are not stored on this public demo.'],
    ['massive-clear-key', 'No Massive key is stored on this host.'],
    ['diagnostic-refresh', 'Connection tests need Finnhub on your Mac. This host uses the bundled snapshot.'],
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

  function softHideNav() {
    document.querySelectorAll('.nav-btn[data-view]').forEach((button) => {
      const view = button.dataset.view;
      if (!SOFT_HIDE.has(view)) return;
      button.classList.add('demo-nav-soft-hidden');
      button.setAttribute('aria-hidden', 'true');
      button.tabIndex = -1;
      button.title = 'Available on the Mac install · soft-hidden on the public demo';
    });
    document.querySelectorAll('.sidebar-group').forEach((group) => {
      const buttons = group.querySelectorAll('.nav-btn[data-view]');
      if (!buttons.length) return;
      const visible = [...buttons].some((b) => !b.classList.contains('demo-nav-soft-hidden'));
      group.classList.toggle('demo-nav-group-empty', !visible);
    });
  }

  function markMacOnlySettings() {
    for (const id of ['api-key', 'massive-api-key', 'save-key', 'massive-save-key']) {
      const el = document.getElementById(id);
      el?.closest('.settings-card')?.classList.add('demo-mac-only');
    }
    const settingsTitle = document.querySelector('#view-settings .page-title > div > p');
    if (settingsTitle && !settingsTitle.dataset.demoWiring) {
      settingsTitle.dataset.demoWiring = '1';
      settingsTitle.textContent =
        'Public portfolio: appearance, guided walkthrough and file check. Provider keys stay on your Mac.';
    }
    const eyebrow = document.querySelector('#view-settings .page-title .eyebrow');
    if (eyebrow) eyebrow.textContent = 'SETTINGS / PUBLIC PORTFOLIO';
  }

  function assertDemoChrome() {
    const bind = (id, text) => {
      const el = document.getElementById(id);
      if (el && el.textContent !== text) el.textContent = text;
    };
    bind('connection-sub', 'Public portfolio · bundled snapshot · not a live Finnhub feed');
    bind('connection-label', 'Public portfolio data');
    bind('top-status', 'DEMO DATA');
    bind('side-identity-tagline', 'PUBLIC PORTFOLIO · DEMO DATA');
    bind('desk-session-label', 'SAMPLE DATA · NOT LIVE');
    bind('desk-edition-label', 'DEMO / 01');
    bind('preferences-state', 'DEMO · BROWSER ONLY');
    const foot = document.querySelector('.side-footer');
    if (foot && !/PUBLIC PORTFOLIO|PORTFOLIO DEMO/.test(foot.textContent)) {
      foot.textContent = 'PUBLIC PORTFOLIO · 01 / 26';
    }
    for (const id of ['connection-dot', 'top-dot']) {
      const dot = document.getElementById(id);
      if (dot) dot.className = 'status-dot amber';
    }
    document.querySelectorAll('#api-key, #massive-api-key, #save-key, #massive-save-key').forEach((el) => {
      if (!el) return;
      el.disabled = true;
      if (el.type === 'password' || el.type === 'text') el.placeholder = 'Not used on public demo';
    });
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

  const FIRST_RUN_KEY = 'md-guided-demo-seen';

  function guidedSeen() {
    try {
      return localStorage.getItem(FIRST_RUN_KEY) === '1';
    } catch {
      return true;
    }
  }

  function markGuidedSeen() {
    try {
      localStorage.setItem(FIRST_RUN_KEY, '1');
    } catch {}
    window.MarketDeskShowcase?.markGuidedSeen?.();
    document.getElementById('demo-first-run-cta')?.remove();
  }

  function openGuidedDemoFromCta() {
    markGuidedSeen();
    if (typeof changeView === 'function') changeView('settings');
    else document.querySelector('.nav-btn[data-view="settings"]')?.click();
    let tries = 0;
    const tick = () => {
      tries += 1;
      if (window.MarketDeskShowcase?.beginGuidedDemo?.()) return;
      const btn = document.getElementById('showcase61-demo');
      if (btn) {
        btn.click();
        document.getElementById('showcase61')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        return;
      }
      if (tries < 50) setTimeout(tick, 100);
    };
    setTimeout(tick, 200);
  }

  function firstRunCta() {
    if (!isDemo() || guidedSeen() || document.getElementById('demo-first-run-cta')) return;
    // Mount inside Overview scroll content so the fixed look43 header cannot intercept clicks.
    const overview = document.getElementById('view-overview');
    if (!overview) return;
    const cue = document.createElement('aside');
    cue.id = 'demo-first-run-cta';
    cue.className = 'demo-first-run-cta';
    cue.setAttribute('role', 'region');
    cue.setAttribute('aria-label', 'Optional guided demo');
    cue.innerHTML =
      '<div class="demo-first-run-copy">' +
      '<strong>Optional walkthrough</strong>' +
      '<p>DEMO DATA only — labelled sample figures, not a live feed. Open Settings for the guided demo (Overview → Heatmap → Stock Browser → Forecast Lab).</p>' +
      '</div>' +
      '<div class="demo-first-run-actions">' +
      '<button type="button" class="primary-btn" id="demo-first-run-start">Start guided demo</button>' +
      '<button type="button" class="ghost-btn" id="demo-first-run-dismiss">Not now</button>' +
      '</div>';
    overview.insertBefore(cue, overview.firstChild);
    document.getElementById('demo-first-run-start')?.addEventListener('click', openGuidedDemoFromCta);
    document.getElementById('demo-first-run-dismiss')?.addEventListener('click', markGuidedSeen);
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
    if (!isDemo()) return;
    document.documentElement.dataset.demoMode = 'true';
    softHideNav();
    markMacOnlySettings();
    assertDemoChrome();
    setupGuards();
    wireDeskShortcuts();
    settingsTour();
    const view = window.E?.view || 'overview';
    syncFocusNav(view);
    window.addEventListener('marketdesk:ready', () => {
      assertDemoChrome();
      syncFocusNav(window.E?.view || 'overview');
      window.MarketDeskDemoPolish?.refresh();
      firstRunCta();
    });
    window.addEventListener('marketdesk:edition-change', assertDemoChrome);
    window.addEventListener('marketdesk:preference-saved', assertDemoChrome);
    const nav = document.getElementById('nav');
    if (nav) {
      new MutationObserver(() => {
        const selected = document.querySelector('#nav .nav-btn.active')?.dataset.view;
        if (selected) syncFocusNav(selected);
      }).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });
    }
    if (window.E?.initialised) firstRunCta();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady);
  else onReady();

  window.MarketDeskDemo = {
    syncFocusNav,
    FOCUS_FOR,
    SOFT_HIDE,
    assertDemoChrome,
    firstRunCta,
    markGuidedSeen,
    FIRST_RUN_KEY,
  };
})();

