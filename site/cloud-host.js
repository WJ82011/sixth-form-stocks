/* Public portfolio demo: intercept /api/* with bundled snapshot when not on local server.py */
(function () {
  'use strict';
  const params = new URLSearchParams(location.search);
  const host = location.hostname;
  const port = location.port;
  const localPython = (host === 'localhost' || host === '127.0.0.1') && port === '8765';
  const forceLocal = params.get('demo') === 'local';
  const forceDemo = params.get('demo') === '1' || params.get('demo') === 'cloud';
  const isVercel = host.endsWith('.vercel.app') || host.includes('sixth-form-stocks');
  const demoMode = (forceDemo || isVercel) && !localPython && !forceLocal;
  if (!demoMode) return;

  window.Desk =
    window.Desk ||
    {
      selected() {},
      memory() {},
      reload() {},
      historyChanged() {},
      chartMount() {
        return document.getElementById('desk-chart-mount');
      },
    };

  let snapshot = null;
  try {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', '/demo/snapshot.json', false);
    xhr.send();
    if (xhr.status === 200) snapshot = JSON.parse(xhr.responseText);
  } catch (error) {
    console.warn('Demo snapshot could not be loaded:', error);
  }

  const start = Date.now();
  const sec = Math.floor(start / 1000);

  function quote(sym) {
    const hit = snapshot?.quotes?.[sym];
    if (hit) return hit;
    const fallback = 96.5;
    return { c: fallback, pc: fallback * 0.99 };
  }

  function quoteItems(symbols) {
    return symbols
      .filter(Boolean)
      .map((sym) => {
        const q = quote(sym);
        return {
          symbol: sym,
          quote: { c: q.c, t: sec, pc: q.pc, o: q.c - 0.3, h: q.c + 1.5, l: q.c - 1.6, dp: ((q.c - q.pc) / q.pc) * 100 },
          source: 'Portfolio demo bundle',
          status: 'ok',
          cached: true,
        };
      });
  }

  function defaultV3State() {
    return {
      version: 3,
      ledger: [],
      marks: [],
      checkpoints: [],
      events: [],
      manualStatements: [],
      home: { order: ['watchlist', 'portfolio', 'events', 'economy', 'research'], hidden: [] },
      benchmark: 'SPY',
      researchFocus: '',
      analyst: { snapshots: [] },
      briefing: { checkpoints: [] },
      research: { projects: [] },
    };
  }

  function v3Calculate(body) {
    const state = body?.state && typeof body.state === 'object' ? body.state : defaultV3State();
    return {
      state,
      portfolio: {
        complete: true,
        cashUSD: 10000,
        totalValueUSD: 10000,
        realisedUSD: 0,
        knownUnrealisedUSD: 0,
        holdings: [],
        notice: 'Practice ledger stays in your browser on the public demo.',
      },
      insights: { openCostUSD: 0, holdings: [], concentration: [], currency: [] },
      performance: { status: 'insufficient', notice: 'Save dated marks on your Mac to measure performance.' },
    };
  }

  function heatmapPacket(period) {
    if (!snapshot?.heatmap) return { rows: [], error: 'Demo snapshot missing heatmap data.' };
    const scale = period === '3D' ? 1.7 : period === '1W' ? 2.4 : 1;
    const rows = snapshot.heatmap.rows.map((row) => ({
      ...row,
      period,
      change: row.change === null ? null : +(row.change * scale).toFixed(2),
    }));
    return { ...snapshot.heatmap, period, rows, cloudDemo: true };
  }

  function catalogNames() {
    return snapshot?.workspace?.names || {};
  }

  function screenerPacket() {
    const base =
      snapshot?.screener || {
        asOf: snapshot?.heatmap?.asOf || start,
        directoryCount: snapshot?.heatmap?.rows?.length || 0,
        rows: [],
        notice: 'Demo screener bundle missing.',
      };
    const quoteMs = start - 45 * 60000;
    return {
      ...base,
      asOf: start,
      rows: (base.rows || []).map((r) => ({
        ...r,
        quoteTime: quoteMs,
        quoteFetchedAt: start,
        financialsFetchedAt: start,
        profileFetchedAt: start,
      })),
    };
  }

  function deskRows(symbols) {
    const catalog = catalogNames();
    return symbols.map((sym) => {
      const q = quote(sym);
      return {
        symbol: sym,
        name: catalog[sym] || sym,
        price: q.c,
        listingCurrency: 'USD',
        quoteTime: snapshot?.heatmap?.asOf || start,
        changePct: +(((q.c - q.pc) / q.pc) * 100).toFixed(2),
      };
    });
  }

  function tapePacket(sym, review) {
    const saved = snapshot?.tape?.[sym];
    let events = saved?.events || [
      { t: start - 3000, p: quote(sym).c, v: 12, receivedAt: start - 3000, id: 1, s: sym },
    ];
    if (events.length && start - events[events.length - 1].t > 86400000 * 7) {
      const span = Math.max(1000, events[events.length - 1].t - events[0].t);
      const anchor = start - Math.min(span, 6 * 3600000);
      events = events.map((e, index) => {
        const offset = e.t - events[0].t;
        const t = anchor + offset;
        return { ...e, t, receivedAt: t + 12, id: index + 1, s: sym };
      });
    }
    return {
      symbol: sym,
      events: review ? events : events.filter((e) => e.t >= start - 86400000),
      recordingDays: saved?.recordingDays || [{ date: '2025-11-12', count: events.length }],
      source: 'Portfolio demo · synthetic tape',
      complete_market_tape: false,
      notice: 'Illustrative captured trades on the public demo.',
      coverage: { label: 'Demo partial tape', gaps: 0 },
      demoMode: true,
    };
  }

  function newsItems(sym) {
    if (sym && snapshot?.newsBySymbol?.[sym]) return snapshot.newsBySymbol[sym];
    return snapshot?.news || [];
  }

  function shiftCryptoPacket(packet) {
    if (!packet) return packet;
    const cloned = { ...packet, fetchedAt: start };
    if (packet.points?.length) {
      const last = packet.points[packet.points.length - 1].t;
      if (start - last > 86400000 * 2) {
        const delta = start - last;
        cloned.points = packet.points.map((p) => ({ ...p, t: p.t + delta }));
        cloned.start = (packet.start || 0) + delta;
        cloned.end = (packet.end || 0) + delta;
      }
    }
    if (packet.time && start - packet.time > 86400000 * 2) {
      cloned.time = start - 15000;
    }
    if (packet.price === undefined && packet.points?.length) {
      cloned.price = packet.points[packet.points.length - 1].p;
    }
    return cloned;
  }

  function dailyResponse(sym) {
    const bars = snapshot?.dailyBars?.[sym];
    if (bars) {
      return {
        status: 'ok',
        source: 'Portfolio demo bundle · synthetic daily path',
        provider: 'demo',
        cached: true,
        adjusted: true,
        candles: bars,
        notice: snapshot?.label,
        cloudDemo: true,
      };
    }
    const base = quote(sym).c;
    const days = 120;
    const t = [];
    const c = [];
    for (let i = days; i >= 0; i--) {
      t.push(sec - i * 86400);
      c.push(+(base * (0.92 + ((days - i) / days) * 0.14)).toFixed(4));
    }
    return {
      status: 'ok',
      source: 'Portfolio demo · generated path',
      provider: 'demo',
      cached: true,
      candles: { s: 'ok', t, c },
      cloudDemo: true,
    };
  }

  function route(path, options) {
    const parsed = new URL(String(path), location.origin);
    const p = parsed.pathname;
    const qs = parsed.searchParams;
    const body = options?.body ? JSON.parse(options.body) : null;
    const isPost = String(options?.method || 'GET').toUpperCase() === 'POST';

    if (p === '/api/status') {
      return {
        configured: true,
        massive_configured: true,
        api_used_last_60s: 0,
        api_budget: 48,
        backgroundCollector: false,
        cloudDemo: true,
        demoMode: true,
      };
    }
    if (p === '/api/session') return { token: 'DEMO_ONLY', local_only: false, demoMode: true };
    if (p === '/api/diagnose') {
      return {
        ok: true,
        kind: 'quote_received',
        latency_ms: 8,
        tls_trust: 'Static portfolio host',
        checked_at: start,
        quote_time_ms: start - 120000,
        message: 'Demo bundle quote check · not a live Finnhub test.',
        demoMode: true,
      };
    }
    if (p === '/api/workspace') {
      if (isPost) return { ok: true, updated_at: start, demoMode: true, notice: 'Browser-only on public demo.' };
      const ws = snapshot?.workspace;
      const snap = snapshot
        ? {
            watch: snapshot.watchlist,
            names: ws?.names || {},
            notes: ws?.notes || [],
            reports: ws?.reports || [],
            portfolio: { capital: 10000, trades: [] },
            preferences: {},
            design: {},
            v3: {},
            tapeSymbol: 'AAPL',
            analystDrafts: { version: 1, records: [] },
            journal: [],
            research: ws?.research || { projects: [], watchlists: [] },
          }
        : null;
      return { snapshot: snap, updated_at: snap ? start : 0, cloudDemo: true };
    }
    if (p === '/api/selftest') {
      return {
        ok: true,
        checks: [
          { name: 'Demo snapshot', ok: Boolean(snapshot), detail: snapshot ? snapshot.generated : 'missing' },
          { name: 'Website files', ok: true, detail: 'Static Vercel bundle' },
        ],
        notice: 'Public demo file check · no Mac database attached.',
        demoMode: true,
      };
    }
    if (p === '/api/quotes' || p === '/api/quote') {
      const syms =
        p === '/api/quote' ? [qs.get('symbol')] : String(qs.get('symbols') || snapshot?.watchlist?.join(',') || 'AAPL').split(',');
      return { items: quoteItems(syms), demoMode: true };
    }
    if (p === '/api/saved-quotes') {
      const syms = String(qs.get('symbols') || '').split(',');
      return { items: quoteItems(syms), demoMode: true };
    }
    if (p === '/api/history') {
      const sym = qs.get('symbol') || 'AAPL';
      const q = quote(sym);
      return {
        points: [
          { t: start - 2 * 3600000, p: q.pc, source: 'demo_fixture' },
          { t: start - 40 * 60000, p: q.c * 0.998, source: 'demo_fixture' },
          { t: start - 60000, p: q.c, source: 'demo_fixture' },
        ],
        demoMode: true,
      };
    }
    if (p === '/api/candles' || p === '/api/saved-daily') return dailyResponse(qs.get('symbol') || 'AAPL');
    if (p === '/api/massive-diagnose') {
      return {
        ok: true,
        kind: 'daily_bars_received',
        count: 120,
        latency_ms: 5,
        latest_bar_time_ms: start - 86400000,
        message: 'Demo daily history ready for charts.',
        demoMode: true,
      };
    }
    if (p === '/api/massive-token' || p === '/api/token' || p === '/api/ticks') {
      return {
        ok: true,
        configured: true,
        demoMode: true,
        notice: 'API keys are not stored on the public demo host. Run server.py on your Mac for live Finnhub.',
      };
    }
    if (p === '/api/collector-pulse') {
      return { cursor: 1, epoch: 'demo', status: { stream: 'Disconnected' }, symbols: [], events: [], gap: false, demoMode: true };
    }
    if (p === '/api/tape') {
      const sym = qs.get('symbol') || 'AAPL';
      const review = qs.get('last') === '1' || Boolean(qs.get('day'));
      return tapePacket(sym, review);
    }
    if (p === '/api/search') {
      const q = String(qs.get('q') || '').toUpperCase();
      const names = catalogNames();
      const result = Object.keys(names)
        .filter((sym) => !q || sym.includes(q) || names[sym].toUpperCase().includes(q))
        .slice(0, 12)
        .map((sym) => ({ symbol: sym, description: names[sym], type: 'Common Stock' }));
      return { result, demoMode: true };
    }
    if (p === '/api/company') {
      const sym = qs.get('symbol') || 'AAPL';
      const q = quote(sym);
      const name = snapshot?.workspace?.names?.[sym] || sym;
      return {
        symbol: sym,
        profile: {
          name,
          ticker: sym,
          exchange: 'NASDAQ',
          currency: 'USD',
          country: 'US',
          marketCapitalization: 1200000,
          weburl: 'https://example.com',
          finnhubIndustry: 'Technology',
          ipo: '2010-01-01',
        },
        metrics: { metric: { peTTM: 22.1, '52WeekHigh': q.c * 1.18, '52WeekLow': q.c * 0.72 } },
        demoMode: true,
      };
    }
    if (p === '/api/news' || p === '/api/saved-news') {
      const sym = qs.get('symbol');
      return { items: newsItems(sym), demoMode: true };
    }
    if (p === '/api/intelligence') {
      const sym = qs.get('symbol') || 'AAPL';
      const packet = snapshot?.intelligence?.[sym] || snapshot?.intelligence?.AAPL;
      if (!packet) return { error: 'No intelligence bundle for this symbol.', demoMode: true };
      return { ...packet, demoMode: true };
    }
    if (p === '/api/imported-history') return { status: 'no_data', demoMode: true };
    if (p === '/api/desk') {
      const syms = String(qs.get('symbols') || snapshot?.watchlist?.join(',') || 'AAPL').split(',').filter(Boolean);
      const screen = screenerPacket();
      const bySym = Object.fromEntries(screen.rows.map((r) => [r.symbol, r]));
      return {
        ...screen,
        rows: syms.map((sym) => bySym[sym] || deskRows([sym])[0]),
        movers: deskRows(syms.slice(0, 4)),
        demoMode: true,
      };
    }
    if (p === '/api/v3/heatmap') return heatmapPacket(qs.get('period') || '1D');
    if (p === '/api/v3/heatmap-sync') {
      return {
        status: 'complete',
        completed: 6,
        required: 6,
        message: 'Demo bundle already includes directory history.',
        demoMode: true,
      };
    }
    if (p === '/api/screener') {
      return { ...screenerPacket(), demoMode: true };
    }
    if (p === '/api/screener/refresh') {
      return {
        symbol: body?.symbol || 'AAPL',
        warnings: ['Public demo does not call Finnhub. Figures stay on the bundled snapshot.'],
        stop: false,
        notice: 'Refresh simulated on the demo host.',
        demoMode: true,
      };
    }
    if (p === '/api/v3/overview60') {
      return { ...(snapshot?.overview60 || {}), demoMode: true };
    }
    if (p === '/api/v3/crypto-chart') {
      const product = qs.get('product') || 'BTC-USD';
      const range = qs.get('range') || '1D';
      const chart = snapshot?.crypto?.charts?.[`${product}|${range}`];
      if (!chart) return { error: 'Crypto chart not in demo bundle.', demoMode: true };
      return { ...shiftCryptoPacket(chart), demoMode: true };
    }
    if (p === '/api/v3/crypto-quote') {
      const product = qs.get('product') || 'BTC-USD';
      const row = snapshot?.crypto?.quotes?.[product];
      if (!row) return { error: 'Crypto quote not in demo bundle.', demoMode: true };
      return { ...shiftCryptoPacket(row), demoMode: true };
    }
    if (p === '/api/v3/crypto-board') {
      return { ...(snapshot?.crypto?.board || { rows: [] }), demoMode: true };
    }
    if (p === '/api/v3/crypto-follow') {
      return { followed: body?.products || snapshot?.crypto?.followed || [], demoMode: true };
    }
    if (p === '/api/v3/equity-session') {
      return {
        symbol: qs.get('symbol') || 'AAPL',
        status: 'demo',
        session: '2025-11-12',
        notice: 'Bundled session label for the public demo.',
        demoMode: true,
      };
    }
    if (p === '/api/v3/state') return { state: defaultV3State(), demoMode: true };
    if (p === '/api/v3/calculate' && isPost) return { ...v3Calculate(body), demoMode: true };
    if (p === '/api/v3/overview') {
      const s = defaultV3State();
      return {
        state: s,
        portfolio: v3Calculate({ state: s }).portfolio,
        events: [],
        accounts: { rows: [] },
        macro: [],
        demoMode: true,
      };
    }
    if (p === '/api/v3/events') return { events: [], demoMode: true };
    if (p === '/api/v3/listings-refresh') {
      return {
        ok: true,
        notice: 'SEC directory refresh needs your Mac. Demo search uses the bundled watchlist slice.',
        demoMode: true,
      };
    }
    if (p === '/api/v3/listings') {
      const q = String(qs.get('q') || '').toUpperCase();
      const names = catalogNames();
      const rows = Object.keys(names)
        .filter((sym) => !q || sym.includes(q) || names[sym].toUpperCase().includes(q))
        .slice(0, 100)
        .map((sym) => ({ symbol: sym, name: names[sym] }));
      return {
        rows,
        total: Object.keys(names).length,
        source: 'Bundled directory names',
        checkedAt: snapshot?.heatmap?.asOf,
        demoMode: true,
      };
    }
    if (p === '/api/v3/screen') {
      const screen = screenerPacket();
      return {
        rows: screen.rows.filter((r) => r.inDirectory).slice(0, 60),
        notice: screen.notice,
        demoMode: true,
      };
    }
    if (p === '/api/v3/macro') {
      return { ...(snapshot?.macro || { series: [], available: {} }), demoMode: true };
    }
    if (p === '/api/macro') {
      return { items: snapshot?.macro?.series || [], demoMode: true };
    }
    if (p === '/api/v3/sources') {
      return {
        accounts: { count: 0, latestFetch: null },
        listings: { count: snapshot?.heatmap?.rows?.length || 0, checkedAt: snapshot?.heatmap?.asOf },
        macro: [],
        limits: ['Public demo uses a bundled snapshot.', 'Live Finnhub, SEC refresh and AI run on your Mac with server.py.'],
        demoMode: true,
      };
    }
    if (p === '/api/v3/statements' || p === '/api/financials') {
      return { symbol: qs.get('symbol') || 'AAPL', books: [], notice: 'SEC accounts need the Mac server.', demoMode: true };
    }
    if (p === '/api/v3/chart-compare') {
      return { status: 'insufficient', notice: 'Open Overview charts on the demo bundle instead.', demoMode: true };
    }
    if (p === '/api/v3/events42') {
      return { symbol: qs.get('symbol'), events: [], notice: 'Events need the Mac server.', demoMode: true };
    }
    if (p === '/api/v3/forecast61') {
      const sym = qs.get('symbol') || 'AAPL';
      const packet = snapshot?.forecasts?.[sym] || snapshot?.forecasts?.AMD;
      if (!packet) {
        return {
          symbol: sym,
          status: 'withheld',
          rows: [],
          notice: 'No forecast bundle for this symbol.',
          demoMode: true,
        };
      }
      return { ...packet, symbol: sym, demoMode: true };
    }
    if (p === '/api/v3/forecast-journal') {
      return {
        asOf: start,
        rows: [],
        summary: { all: { count: 0 }, nonOverlapping: { count: 0 } },
        notice: 'Forecast journal needs your Mac.',
        demoMode: true,
      };
    }
    if (p === '/api/v3/drafts-validate' && isPost) {
      const drafts = body?.drafts;
      return {
        records: Array.isArray(drafts?.records) ? drafts.records : [],
        demoMode: true,
      };
    }
    if (p === '/api/ai/status') {
      return {
        ready: false,
        configured: false,
        models: [],
        message: 'Local AI is not available on the public demo host.',
        demoMode: true,
      };
    }
    if (p === '/api/ai/library') {
      return { documents: [], runs: [], demoMode: true };
    }
    if (p === '/api/alerts') {
      if (isPost) {
        return {
          ok: true,
          notice: 'Alert edits stay in your browser on the demo.',
          demoMode: true,
        };
      }
      return { ...(snapshot?.alerts || { alerts: [], events: [] }), demoMode: true };
    }
    if (isPost) {
      return { ok: true, demoMode: true, notice: 'Saved in your browser only on the public demo.' };
    }
    return {
      error: 'This tool needs the full Mac server.',
      demoMode: true,
      notice:
        'Overview, Heatmap, Screener, Browser, Tape, Crypto, Intelligence, Research and Settings use the bundled demo snapshot.',
    };
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async function cloudFetch(url, options) {
    const text = String(url);
    if (!text.includes('/api/')) return nativeFetch(url, options);
    let pathname = text;
    try {
      const u = new URL(text, location.origin);
      pathname = u.pathname + u.search;
    } catch {
      /* ignore */
    }
    if (!pathname.startsWith('/api/')) return nativeFetch(url, options);
    const payload = route(pathname, options);
    const ok = !payload.error;
    return {
      ok,
      status: ok ? 200 : 503,
      json: async () => payload,
      text: async () => JSON.stringify(payload),
    };
  };

  class DemoSocket extends EventTarget {
    static OPEN = 1;
    constructor() {
      super();
      this.readyState = 0;
      setTimeout(() => {
        this.readyState = 1;
        this.dispatchEvent(new Event('open'));
      }, 50);
    }
    send() {}
    close() {
      this.readyState = 3;
      this.dispatchEvent(new Event('close'));
    }
  }
  window.WebSocket = DemoSocket;

  window.MarketDeskHost = {
    mode: 'cloud-demo',
    demoMode: true,
    label: snapshot?.label || 'Portfolio demo',
    snapshotReady: Boolean(snapshot),
    isCloud: () => true,
  };

  function applyChrome() {
    document.documentElement.dataset.demoMode = 'true';
    const alert = document.getElementById('global-alert');
    if (alert) {
      alert.textContent =
        'Portfolio demo · labelled snapshot on this host · run server.py on your Mac for live Finnhub research (see README-START-HERE.txt).';
      alert.classList.remove('hidden');
    }
    const bind = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    bind('connection-sub', 'Demo bundle · not a live Finnhub feed');
    bind('connection-label', 'Portfolio demo data');
    bind('top-status', 'DEMO DATA');
    bind('side-identity-tagline', 'PORTFOLIO ADMISSIONS DEMO');
    bind('desk-session-label', 'SAMPLE DATA · NOT LIVE');
    const deskLocal = document.querySelector('.desk-local');
    if (deskLocal) deskLocal.textContent = 'Portfolio demo · bundled snapshot';
    bind('desk-edition-label', 'DEMO / 01');
    bind('preferences-state', 'DEMO · BROWSER ONLY');
    const overline = document.querySelector('.top-location-overline');
    if (overline) overline.innerHTML = 'PORTFOLIO DEMO <i>◆</i> RESEARCH DESK';
    const ribbonRight = document.querySelector('.desk-ribbon-right');
    if (ribbonRight && !ribbonRight.dataset.demoRibbon) {
      ribbonRight.dataset.demoRibbon = '1';
      const session = document.getElementById('desk-session-label');
      ribbonRight.innerHTML =
        '<span class="ribbon-diamond">◆</span> LABELLED SNAPSHOT · NOT LIVE MARKET DATA <span class="ribbon-divider"></span>' +
        (session ? session.outerHTML : '<span id="desk-session-label">SAMPLE DATA · NOT LIVE</span>');
    }
    const ticker = document.querySelector('.ticker-placeholder');
    if (ticker) ticker.textContent = 'Sample watchlist quotes from the bundled snapshot';
    const mast = document.querySelector('.masthead-caption');
    if (mast) mast.innerHTML = 'ADMISSIONS WALKTHROUGH &nbsp; · &nbsp; LABELLED SNAPSHOT, INDEPENDENT RESEARCH';
    const foot = document.querySelector('.side-footer');
    if (foot) foot.textContent = 'PORTFOLIO DEMO · 01 / 26';
    const ribbonLeft = document.querySelector('.desk-ribbon-left');
    if (ribbonLeft) {
      ribbonLeft.querySelectorAll('span').forEach((span) => {
        if (span.classList.contains('ribbon-edition')) span.textContent = 'DEMO / 01';
        else if (!span.classList.contains('ribbon-divider') && /LOCAL|FINNHUB/i.test(span.textContent)) {
          span.innerHTML = /FINNHUB/i.test(span.textContent)
            ? 'BUNDLED <b>SNAPSHOT</b>'
            : 'PORTFOLIO <b>DEMO</b>';
        }
      });
    }
    for (const id of ['connection-dot', 'top-dot']) {
      const dot = document.getElementById(id);
      if (dot) dot.className = 'status-dot amber';
    }
    document.querySelectorAll('#api-key, #massive-api-key, #save-key, #massive-save-key').forEach((el) => {
      if (el) {
        el.disabled = true;
        if (el.type === 'password' || el.type === 'text') el.placeholder = 'Not used on public demo';
      }
    });
    const warn = document.querySelector('.massive-card .warning-note, .settings-grid .warning-note');
    if (warn) {
      warn.textContent =
        'Provider keys stay on your Mac. This URL is a read-only admissions demo with a bundled snapshot.';
    }
    const prefs = document.querySelector('.pro-preferences > p');
    if (prefs && !prefs.dataset.demoCopy) {
      prefs.dataset.demoCopy = '1';
      prefs.textContent =
        'Choose how your desk looks on this demo. The full Signal and Pro experience with live Finnhub runs when you start server.py on your Mac.';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyChrome);
  else applyChrome();
})();