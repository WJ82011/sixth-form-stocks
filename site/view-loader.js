/* Lazy view bundles for faster first paint on static hosts. Mac server.py unchanged. */
(function () {
  'use strict';

  const norm = (url) => String(url).split('?', 1)[0];

  const BOOT_SCRIPTS = [
    '/navigation.js',
    '/market-hours.js',
    '/chart-research.js',
    '/shell43.js?v=6.8.0',
    '/look43.js?v=6.8.0',
    '/design.js?v=6.8.0',
    '/desk68.js?v=6.8.0',
    '/signal.js',
    '/pro.js',
    '/terminal.js?v=4.3.2',
    '/desk.js?v=4.0.0',
    '/v3.js?v=4.6.0',
    '/desk50.js?v=6.5.0',
    '/overview60.js?v=6.0.0b',
    '/workspace60.js?v=6.0.0b',
    '/annotate60.js?v=6.0.0c',
    '/chart43.js?v=6.4.1',
    '/move44.js?v=4.5.0r',
    '/replay43.js?v=6.7.0',
    '/practice67.js?v=6.7.0',
    '/events42.js?v=6.6.0',
    '/v43.js?v=4.3.14',
  ];

  const BOOT_STYLES = [
    '/desk.css?v=4.0.0',
    '/design.css?v=4.0.0',
    '/v3.css?v=4.6.0',
  ];

  const BUNDLES = {
    heatmap: {
      scripts: ['/heatmap.js?v=4.5.0'],
      styles: ['/heatmap.css'],
    },
    screener: {
      scripts: ['/screener.js'],
      styles: ['/screener.css'],
    },
    crypto: {
      scripts: ['/crypto38.js?v=5.6.0', '/crypto57.js?v=5.7.0'],
      styles: ['/crypto38.css?v=5.7.0'],
    },
    tape: {
      scripts: ['/tape.js?v=4.3.16'],
      styles: ['/tape.css'],
      after: () => { if (typeof tapeSetup === 'function') tapeSetup(); },
    },
    intelligence: {
      scripts: ['/intelligence.js', '/ai-research.js', '/ask48.js?v=6.8.0'],
      styles: ['/intelligence.css?v=6.7.0', '/ai-research.css'],
    },
    alerts: {
      scripts: ['/alerts.js?v=4.8.0'],
      styles: ['/alerts.css'],
      after: () => { if (typeof PriceAlerts !== 'undefined') PriceAlerts.setup(); },
    },
    learning: {
      scripts: ['/workbench40.js?v=4.5.0'],
      styles: [],
    },
    company: {
      scripts: ['/financial-health.js?v=4.0.0', '/earnings62.js?v=6.2.0b'],
      styles: ['/financial-health.css?v=4.0.0'],
    },
    comparison: {
      scripts: ['/compare.js', '/compare52.js?v=5.2.0', '/desk61.js?v=6.4.1'],
      styles: ['/desk61.css?v=6.0.0e'],
    },
    'forecast-lab': {
      scripts: ['/v19-models.js', '/v19.js'],
      styles: ['/v19.css', '/research-v17.css', '/research-v18.css'],
      after: () => {
        if (typeof setupV19 === 'function') setupV19();
        if (typeof setupResearchV17 === 'function') setupResearchV17();
      },
    },
    reports: {
      scripts: ['/reports.js'],
      styles: [],
      after: () => { if (typeof reportsOnView === 'function') reportsOnView(); },
    },
    macro: {
      scripts: ['/macro.js'],
      styles: [],
      after: () => { if (typeof setupResearchV18 === 'function') setupResearchV18(); },
    },
    research: {
      scripts: [
        '/projects32.js?v=3.2.1',
        '/research35.js?v=4.0.0',
        '/truth36.js?v=4.0.0',
        '/journal49.js?v=6.5.0',
        '/overnight51.js?v=5.1.0',
        '/scenario53.js?v=5.3.0b',
        '/strategy54.js?v=5.4.0',
        '/scanner55.js?v=6.0.0d',
        '/pack59.js?v=5.9.0',
        '/stress58.js?v=5.8.0',
        '/tracker65.js?v=6.5.0',
      ],
      styles: [
        '/projects32.css?v=3.2.1',
        '/research35.css?v=4.0.0',
        '/truth36.css?v=4.0.0',
      ],
    },
    settings: {
      scripts: ['/showcase61.js?v=6.1.0c'],
      styles: ['/desk61.css?v=6.0.0e'],
    },
    markets: {
      scripts: [],
      styles: ['/stock-directory.css'],
    },
    smoke: {
      scripts: ['/smoke431.js?v=6.8.0'],
      styles: [],
    },
  };

  const VIEW_BUNDLES = {
    home: [],
    calendar: [],
    sources: [],
    overview: [],
    learning: ['learning'],
    heatmap: ['heatmap'],
    crypto: ['crypto'],
    screener: ['screener'],
    intelligence: ['intelligence'],
    alerts: ['alerts'],
    markets: ['markets'],
    tape: ['tape'],
    company: ['company'],
    comparison: ['comparison'],
    macro: ['macro'],
    accuracy: ['macro'],
    indicators: ['forecast-lab'],
    valuation: ['forecast-lab'],
    portfolio: ['forecast-lab'],
    forecast: ['forecast-lab'],
    news: [],
    research: ['research', 'forecast-lab'],
    reports: ['reports', 'forecast-lab'],
    settings: ['settings'],
  };

  /** Scripts that used to ship in index.html — tests can grep this list. */
  const LEGACY_INDEX_SCRIPTS = [
    '/market-hours.js',
    '/chart-research.js',
    '/tape.js',
    '/compare.js',
    '/reports.js',
    '/macro.js',
    '/app.js',
    '/signal.js',
    '/pro.js',
    '/terminal.js',
  ];

  const loadedScripts = new Set();
  const loadedStyles = new Set();
  const bundlePromises = new Map();
  let bootPromise = null;

  function loadScript(src) {
    const key = norm(src);
    if (loadedScripts.has(key)) return Promise.resolve();
    loadedScripts.add(key);
    return new Promise((resolve, reject) => {
      const el = document.createElement('script');
      el.src = src;
      el.defer = true;
      el.onload = () => resolve();
      el.onerror = () => reject(new Error('Could not load ' + src));
      document.head.appendChild(el);
    });
  }

  function loadStyle(href) {
    const key = norm(href);
    if (loadedStyles.has(key)) return Promise.resolve();
    loadedStyles.add(key);
    return new Promise((resolve, reject) => {
      const el = document.createElement('link');
      el.rel = 'stylesheet';
      el.href = href;
      el.onload = () => resolve();
      el.onerror = () => reject(new Error('Could not load ' + href));
      document.head.appendChild(el);
    });
  }

  async function loadBundle(name) {
    if (bundlePromises.has(name)) return bundlePromises.get(name);
    const bundle = BUNDLES[name];
    if (!bundle) return;
    const job = (async () => {
      for (const href of bundle.styles || []) await loadStyle(href);
      for (const src of bundle.scripts || []) await loadScript(src);
      if (typeof bundle.after === 'function') bundle.after();
    })();
    bundlePromises.set(name, job);
    return job;
  }

  async function ensureView(view) {
    const names = VIEW_BUNDLES[view] || [];
  const jobs = names.map((name) => loadBundle(name));
    await Promise.all(jobs);
  }

  async function boot() {
    if (bootPromise) return bootPromise;
    bootPromise = (async () => {
      await Promise.all(BOOT_STYLES.map(loadStyle));
      for (const src of BOOT_SCRIPTS) await loadScript(src);
      if (new URLSearchParams(location.search).get('smoke') === '431') await loadBundle('smoke');
      if (typeof requestIdleCallback === 'function') {
        requestIdleCallback(() => {
          loadBundle('heatmap').catch(() => {});
          loadBundle('markets').catch(() => {});
        }, { timeout: 4000 });
      }
    })();
    return bootPromise;
  }

  window.MarketDeskViews = {
    boot,
    ensureView,
    loadBundle,
    LEGACY_INDEX_SCRIPTS,
    BOOT_SCRIPTS,
    BUNDLES,
  };

  bootPromise = boot();
})();