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

  function deskRows(symbols) {
    const catalog = snapshot?.workspace?.names || {};
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
      const snap = snapshot
        ? {
            watch: snapshot.watchlist,
            names: snapshot.workspace?.names || {},
            notes: [],
            reports: [],
            portfolio: { capital: 10000, trades: [] },
            preferences: {},
            design: {},
            v3: {},
            tapeSymbol: 'AAPL',
            analystDrafts: { version: 1, records: [] },
            journal: [],
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
      const q = quote(sym);
      return {
        symbol: sym,
        events: [{ t: start - 3000, p: q.c, v: 12, receivedAt: start - 3000, id: 1, s: sym }],
        demoMode: true,
      };
    }
    if (p === '/api/search') {
      const q = String(qs.get('q') || '').toUpperCase();
      const names = snapshot?.workspace?.names || {};
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
      return { items: snapshot?.news || [], demoMode: true };
    }
    if (p === '/api/imported-history') return { status: 'no_data', demoMode: true };
    if (p === '/api/desk') {
      const syms = String(qs.get('symbols') || snapshot?.watchlist?.join(',') || 'AAPL').split(',').filter(Boolean);
      return { rows: deskRows(syms), movers: deskRows(syms.slice(0, 4)), demoMode: true };
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
      const syms = String(qs.get('symbols') || 'AAPL,NVDA,MSFT').split(',');
      return {
        rows: syms.map((sym) => ({
          symbol: sym,
          name: snapshot?.workspace?.names?.[sym] || sym,
          price: quote(sym).c,
          changePct: 1.2,
          marketCapMillions: 400000,
          marketCapCurrency: 'USD',
          marketCapFetchedAt: snapshot?.heatmap?.asOf || start,
        })),
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
    if (p === '/api/v3/listings') {
      const q = String(qs.get('q') || '').toUpperCase();
      const names = snapshot?.workspace?.names || {};
      const rows = Object.keys(names)
        .filter((sym) => !q || sym.includes(q) || names[sym].toUpperCase().includes(q))
        .slice(0, 40)
        .map((sym) => ({ symbol: sym, name: names[sym] }));
      return { rows, total: rows.length, source: 'Demo watchlist slice', checkedAt: snapshot?.heatmap?.asOf, demoMode: true };
    }
    if (p === '/api/v3/screen') return { rows: [], notice: 'Full account screen needs your Mac.', demoMode: true };
    if (p === '/api/v3/macro') return { series: [], available: {}, demoMode: true };
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
      const q = quote(sym);
      return {
        symbol: sym,
        status: 'withheld',
        method: 'Demo withholding example',
        observations: 90,
        notice: 'Sample: unchanged price beat the model on later dates — no purple path drawn.',
        rows: [],
        horizons: [{ horizon: 5, status: 'Withheld', testCases: 4 }],
        issuedCount: 0,
        demoMode: true,
        inputs: 'Demo only',
        trainingNote: 'Not fitted on this host.',
        anchorDate: '2025-11-01',
        first: '2025-08-01',
        interpolation: [],
      };
    }
    if (p === '/api/alerts') return { alerts: [], triggered: [], demoMode: true };
    if (isPost) {
      return { ok: true, demoMode: true, notice: 'Saved in your browser only on the public demo.' };
    }
    return {
      error: 'This tool needs the full Mac server.',
      demoMode: true,
      notice: 'Home, Overview, Heatmap, Browser and Settings work on the public demo.',
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
    const foot = document.querySelector('.side-footer');
    if (foot) foot.textContent = 'PORTFOLIO DEMO · 01 / 26';
    const ribbon = document.querySelector('.desk-ribbon-left span:nth-child(3)');
    if (ribbon) ribbon.innerHTML = 'PORTFOLIO <b>DEMO</b>';
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
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyChrome);
  else applyChrome();
})();