/* Public portfolio demo: intercept /api/* with bundled snapshot when not on local server.py */
(function () {
  'use strict';
  const resolve =
    (typeof window !== 'undefined' && window.MarketDeskPublicHost?.resolve) ||
    null;
  const mode = resolve
    ? resolve(location)
    : {
        // Fallback if public-host-mode.js failed to load — keep production safe.
        demoMode:
          (location.search.includes('demo=1') ||
            location.search.includes('demo=cloud') ||
            /\.vercel\.app$|\.tmp\.now$|\.now\.sh$/i.test(location.hostname) ||
            /sixth-form-stocks/i.test(location.hostname)) &&
          !((location.hostname === 'localhost' || location.hostname === '127.0.0.1') && location.port === '8765') &&
          !(location.search.includes('demo=local') && (location.hostname === 'localhost' || location.hostname === '127.0.0.1')),
        publicHost: /\.vercel\.app$|\.tmp\.now$|\.now\.sh$/i.test(location.hostname) || /sixth-form-stocks/i.test(location.hostname),
      };
  if (!mode.demoMode) return;

  // Mark demo before later head scripts / DOMContentLoaded so wiring + polish can detect it.
  document.documentElement.dataset.demoMode = 'true';
  document.documentElement.dataset.publicPortfolio = mode.publicHost ? 'true' : 'force';

  window.Desk =
    window.Desk ||
    {
      open() {},
      selected() {},
      memory() {},
      reload() {},
      historyChanged() {},
      chartMount() {
        return document.getElementById('desk-chart-mount');
      },
      revealSelected() {},
    };

  let snapshot = null;
  const snapshotReady = fetch('/demo/snapshot.json', { credentials: 'same-origin' })
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      snapshot = data;
      if (window.MarketDeskHost) {
        window.MarketDeskHost.snapshotReady = Boolean(snapshot);
        if (data?.label) window.MarketDeskHost.label = data.label;
      }
      // Seed before any awaiter of whenSnapshotReady continues, so V3/init
      // never hydrates an empty ledger ahead of the bundled practice portfolio.
      seedDemoWorkflow(data);
      return snapshot;
    })
    .catch((error) => {
      console.warn('Demo snapshot could not be loaded:', error);
      return null;
    });

  const start = Date.now();
  const sec = Math.floor(start / 1000);

  function quote(sym) {
    const hit = snapshot?.quotes?.[sym];
    if (hit && Number.isFinite(hit.c) && Number.isFinite(hit.pc) && hit.pc > 0) return hit;
    const row = snapshot?.heatmap?.rows?.find((r) => r.symbol === sym);
    if (row && Number.isFinite(row.price) && row.price > 0 && Number.isFinite(row.change)) {
      const c = row.price;
      const pc = c / (1 + row.change / 100);
      if (Number.isFinite(pc) && pc > 0) return { c, pc };
    }
    const screener = snapshot?.screener?.rows?.find((r) => r.symbol === sym);
    if (screener && Number.isFinite(screener.price) && Number.isFinite(screener.previousClose) && screener.previousClose > 0) {
      return { c: screener.price, pc: screener.previousClose };
    }
    // Unchanged fallback — never invent a flat +1% book move.
    return { c: 96.5, pc: 96.5 };
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

  function clone(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
  }

  function emptyV3State() {
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
      research: { version: 1, initialised: false, projects: [], watchlists: [] },
    };
  }

  function defaultV3State() {
    const seeded = snapshot?.workspace?.v3;
    return seeded ? clone(seeded) : emptyV3State();
  }

  function demoLedgerIds(state) {
    return (state?.ledger || []).map((row) => row?.id).filter(Boolean).join('|');
  }

  function v3Calculate(body) {
    const incoming = body?.state && typeof body.state === 'object' ? body.state : null;
    const state = incoming ? clone(incoming) : defaultV3State();
    const calc = snapshot?.workspace?.v3Calc;
    const seedIds = demoLedgerIds(snapshot?.workspace?.v3);
    const useSeeded = Boolean(calc?.portfolio) && demoLedgerIds(state) === seedIds && seedIds.length > 0;
    if (useSeeded) {
      return {
        state,
        portfolio: {
          ...clone(calc.portfolio),
          notice:
            calc.notice ||
            'Portfolio demo · labelled synthetic holdings · practice ledger only.',
        },
        insights: clone(calc.insights) || { openCostUSD: 0, holdings: [], companies: [], sectors: [] },
        performance: clone(calc.performance) || {
          status: 'insufficient',
          notice: 'Demo sample ledger · checkpoints stay on your Mac.',
        },
        demoMode: true,
      };
    }
    // Edited demo ledgers keep cash/holdings honest without inventing marks.
    const cash = (state.ledger || [])
      .filter((e) => e.kind === 'DEPOSIT')
      .reduce((sum, e) => sum + Number(e.amount || 0), 0);
    return {
      state,
      portfolio: {
        complete: !(state.ledger || []).some((e) => e.kind === 'BUY' || e.kind === 'SELL'),
        cashUSD: cash || 0,
        totalValueUSD: cash || 0,
        realisedUSD: 0,
        knownUnrealisedUSD: 0,
        holdings: [],
        notice:
          'Practice ledger stays in this browser on the public demo. Seeded sample marks apply only to the bundled demo ledger.',
      },
      insights: { openCostUSD: 0, holdings: [], companies: [], sectors: [], notice: 'Open the Mac app for full allocation charts after edits.' },
      performance: {
        status: 'insufficient',
        notice: 'Save dated marks on your Mac to measure performance.',
      },
      demoMode: true,
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

  function changeForHeat(sym) {
    const row = snapshot?.heatmap?.rows?.find((r) => r.symbol === sym);
    return row?.change ?? 0.5;
  }

  function normalizeAlerts(packet) {
    const base = packet || { revision: 1, alerts: [], events: [] };
    const alerts = (base.alerts || []).map((a, index) => ({
      ...a,
      status: a.status || (a.armed ? 'armed' : 'paused'),
      arm: a.arm ?? a.armed ?? 1,
      armed_at: a.armed_at || start - 3600000 - index * 60000,
      created_at: a.created_at || start - 86400000,
      frequency: a.frequency || 'once',
      rule_text:
        a.rule_text ||
        (a.kind === 'cross'
          ? `Crosses ${a.direction === 'above' ? 'above' : 'below'} ${a.target} ${a.unit || 'USD'}`
          : `${a.direction === 'above' ? 'At or above' : 'At or below'} ${a.target} ${a.unit || 'USD'}`),
      evaluation_note: a.evaluation_note || 'Bundled demo alert · not evaluated on the static host.',
    }));
    return { ...base, alerts, events: base.events || [], serverTime: start };
  }

  function historyPoints(sym, sinceMs) {
    const base = quote(sym).c;
    const span = Math.max(3600000, start - sinceMs);
    const step = Math.max(180000, Math.floor(span / 72));
    const points = [];
    for (let t = sinceMs; t <= start; t += step) {
      const progress = (t - sinceMs) / span;
      const jitter = Math.sin(progress * 12) * base * 0.0015;
      points.push({
        t,
        p: +(base * (0.996 + progress * 0.006) + jitter).toFixed(4),
        source: 'demo_fixture',
      });
    }
    if (points.length < 2) {
      points.push(
        { t: start - 2 * 3600000, p: base * 0.998, source: 'demo_fixture' },
        { t: start - 60000, p: base, source: 'demo_fixture' }
      );
    }
    return points;
  }

  function tapePacket(sym, review, sinceMs) {
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
    const floor = Number.isFinite(sinceMs) ? sinceMs : start - 86400000;
    return {
      symbol: sym,
      events: review ? events : events.filter((e) => e.t >= floor),
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
        source: 'Portfolio demo bundle · historical daily closes',
        provider: 'demo',
        cached: true,
        adjusted: true,
        candles: bars,
        notice: snapshot?.label,
        cloudDemo: true,
      };
    }
    const q = quote(sym);
    // Two honest session points only — do not invent a flat multi-month path.
    return {
      status: 'ok',
      source: 'Portfolio demo · session close/prevClose only',
      provider: 'demo',
      cached: true,
      candles: {
        s: 'ok',
        t: [sec - 86400, sec],
        c: [q.pc, q.c],
        o: [q.pc, q.c],
        h: [Math.max(q.pc, q.c), Math.max(q.pc, q.c)],
        l: [Math.min(q.pc, q.c), Math.min(q.pc, q.c)],
      },
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
            portfolio: ws?.portfolio || { capital: 10000, trades: [] },
            preferences: {},
            design: {},
            v3: ws?.v3 ? clone(ws.v3) : defaultV3State(),
            tapeSymbol: 'AAPL',
            analystDrafts: { version: 1, records: [] },
            journal: [],
            research: ws?.research || ws?.v3?.research || { projects: [], watchlists: [] },
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
      const since = Number(qs.get('since') || 0);
      const sinceMs = since > 0 ? since * (since < 1e12 ? 1000 : 1) : start - 86400000;
      return { points: historyPoints(sym, sinceMs), demoMode: true };
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
    if (p === '/api/tape') {
      const sym = qs.get('symbol') || 'AAPL';
      const review = qs.get('last') === '1' || Boolean(qs.get('day'));
      const since = Number(qs.get('since') || 0);
      return tapePacket(sym, review, since || undefined);
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
      const calc = v3Calculate({ state: s });
      const macro = (snapshot?.macro?.series || []).slice(0, 4).map((row) => ({
        title: row.title,
        unit: row.unit,
        latest: row.latest,
      }));
      return {
        state: s,
        portfolio: calc.portfolio,
        events: [
          {
            date: '2025-11-20',
            title: 'Earnings estimate · bundled demo',
            symbol: 'AAPL',
            status: 'estimated',
            origin: 'portfolio demo',
          },
        ],
        accounts: { rows: [] },
        macro,
        notice: 'Portfolio demo home · bundled macro, practice ledger and watchlist.',
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
      // Demo snapshot carries Finnhub TTM margin/growth ratios, not SEC dollar
      // sales/profit. Map honestly — leave revenue/profit null so the UI can hide
      // those columns instead of painting a full table of "Unavailable".
      const rows = screen.rows
        .filter((r) => r.inDirectory)
        .slice(0, 60)
        .map((r) => ({
          symbol: r.symbol,
          name: r.name,
          currency: r.filingCurrency || r.listingCurrency || 'USD',
          start: '',
          end: '',
          revenue: Number.isFinite(r.revenue) ? r.revenue : null,
          profit: Number.isFinite(r.profit) ? r.profit : null,
          margin: Number.isFinite(r.margin) ? r.margin : null,
          growth: Number.isFinite(r.growth) ? r.growth : null,
          source: r.source || 'Portfolio demo · TTM ratios in snapshot (not live Finnhub)',
          notice:
            'Demo sample: TTM margin and sales growth from the bundled snapshot. Dollar annual sales and net profit need SEC accounts on your Mac.',
        }));
      return {
        rows,
        notice:
          'Accounts sample incomplete on the public demo — TTM margin and growth are shown; annual sales and net profit stay on your Mac with SEC accounts.',
        demoMode: true,
        accountsIncomplete: true,
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
      const sym = qs.get('symbol') || 'AAPL';
      return {
        symbol: sym,
        events: [
          {
            symbol: sym,
            title: 'Earnings window · demo estimate',
            timeLabel: 'Nov 2025',
            kindLabel: 'Estimate',
            reason: 'Bundled event for admissions screenshots.',
          },
        ],
        demoMode: true,
      };
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
          ...normalizeAlerts(snapshot?.alerts),
          ok: true,
          notice: 'Alert edits stay in your browser on the demo.',
          demoMode: true,
        };
      }
      return { ...normalizeAlerts(snapshot?.alerts), demoMode: true };
    }
    if (p === '/api/v3/learning') {
      const sym = qs.get('symbol') || 'AAPL';
      const packet = snapshot?.learning?.[sym] || snapshot?.learning?.TTWO;
      if (!packet) return { error: 'No learning bundle for this symbol.', demoMode: true };
      return { ...packet, symbol: sym, demoMode: true };
    }
    if (p === '/api/collector' || p === '/api/collector-pulse') {
      return {
        cursor: 1,
        epoch: 'demo',
        lastTrade: start - 120000,
        status: {
          stream: 'Demo bundle',
          quotes: 'Bundled',
          history: 'Bundled',
          model: 'Illustration only',
        },
        symbols: snapshot?.watchlist || [],
        events: [],
        gap: false,
        notice: 'Background collector runs on your Mac · not on this public demo.',
        demoMode: true,
      };
    }
    if (p === '/api/v3/overnight51') {
      const part = qs.get('part') || 'status';
      if (part === 'morning') {
        return {
          notice: 'Bundled overnight log for the portfolio demo.',
          jobs: [
            { symbol: 'AAPL', kind: 'history', status: 'complete', detail: 'Demo daily closes refreshed' },
            { symbol: 'TTWO', kind: 'training', status: 'complete', detail: 'Bundled evaluation kept' },
          ],
          demoMode: true,
        };
      }
      return {
        notice: 'Overnight schedule is illustrative on the public demo.',
        paused: false,
        inWindow: false,
        databaseBytes: 0,
        lastHistoryAt: start - 86400000,
        lastTrainingAt: start - 172800000,
        jobs: [{ symbol: 'AMD', kind: 'quotes', status: 'skipped', detail: 'Live collection needs server.py' }],
        demoMode: true,
      };
    }
    if (p === '/api/v3/desk50') {
      const sym = qs.get('symbol') || 'AAPL';
      if (qs.get('part') === 'since') {
        const syms = String(qs.get('symbols') || snapshot?.watchlist?.join(',') || 'AAPL').split(',');
        return {
          moves: syms.slice(0, 4).map((s) => ({
            symbol: s,
            start: '2025-11-08',
            end: '2025-11-12',
            returnPct: changeForHeat(s),
          })),
          alerts: [{ symbol: 'TTWO', price: 158.2, rule: 'At or above 155 USD' }],
          graded: [{ symbol: 'TTWO', forecastPrice: 167.0, actualPrice: 168.5, anchorDay: '2025-08-01', targetDay: '2025-08-08' }],
          gaps: [],
          demoMode: true,
        };
      }
      if (qs.get('part') === 'storage') {
        return { databaseBytes: 0, workspaceBytes: 0, backupCount: 0, cleanup: 'Mac backups not available on Vercel.', demoMode: true };
      }
      return {
        detail: `Bundled context for ${sym}.`,
        source: 'Portfolio demo · not a live collector status.',
        demoMode: true,
      };
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
    await snapshotReady;
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

  function seedDemoWorkflow(data) {
    const flag = 'md-demo-workflow-seed-v2';
    try {
      const ws = data?.workspace;
      if (!ws?.v3?.ledger?.length) return;
      let existing = null;
      try {
        existing = JSON.parse(localStorage.getItem('md-reborn-v3') || 'null');
      } catch {
        existing = null;
      }
      const hasLedger = Array.isArray(existing?.ledger) && existing.ledger.length > 0;
      // Re-seed when the flag is missing OR a prior visit left an empty ledger
      // (race / cleared site data) so Practice Portfolio never stays blank.
      if (localStorage.getItem(flag) === '1' && hasLedger) return;
      localStorage.setItem('md-reborn-v3', JSON.stringify(ws.v3));
      if (ws.portfolio && Array.isArray(ws.portfolio.trades)) {
        localStorage.setItem('md-reborn-portfolio', JSON.stringify(ws.portfolio));
      }
      if (Array.isArray(ws.notes) && ws.notes.length) {
        localStorage.setItem('md-reborn-notes', JSON.stringify(ws.notes));
      }
      if (Array.isArray(ws.reports) && ws.reports.length) {
        localStorage.setItem('md-reborn-reports', JSON.stringify(ws.reports));
      }
      localStorage.setItem(flag, '1');
      try {
        localStorage.removeItem('md-demo-workflow-seed-v1');
      } catch {}
    } catch (error) {
      console.warn('Demo workflow seed skipped:', error);
    }
  }

  window.MarketDeskHost = {
    mode: 'cloud-demo',
    demoMode: true,
    publicHost: Boolean(mode.publicHost),
    label: 'Public portfolio · DEMO DATA',
    snapshotReady: false,
    whenSnapshotReady: () => snapshotReady,
    isCloud: () => true,
    getWorkspaceSeed: () => clone(snapshot?.workspace || null),
  };

  function applyChrome() {
    document.documentElement.dataset.demoMode = 'true';
    if (mode.publicHost) document.documentElement.dataset.publicPortfolio = 'true';
    const alert = document.getElementById('global-alert');
    if (alert) {
      alert.textContent =
        'Public portfolio · labelled DEMO DATA snapshot on this host (no ?demo=1 needed) · run server.py on your Mac for live Finnhub research (see README-START-HERE.txt).';
      alert.classList.remove('hidden');
    }
    const bind = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    bind('connection-sub', 'Public portfolio · bundled snapshot · not a live Finnhub feed');
    bind('connection-label', 'Public portfolio data');
    // Honest until P1 live proxy lands — never imply live quotes on snapshot-only host.
    bind('top-status', 'DEMO DATA');
    bind('side-identity-tagline', 'PUBLIC PORTFOLIO · DEMO DATA');
    bind('desk-session-label', 'SAMPLE DATA · NOT LIVE');
    const deskLocal = document.querySelector('.desk-local');
    if (deskLocal) deskLocal.textContent = 'Public portfolio · bundled snapshot';
    bind('desk-edition-label', 'DEMO / 01');
    bind('preferences-state', 'DEMO · BROWSER ONLY');
    const overline = document.querySelector('.top-location-overline');
    if (overline) overline.innerHTML = 'PUBLIC PORTFOLIO <i>◆</i> RESEARCH DESK';
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
    if (mast) mast.innerHTML = 'PUBLIC PORTFOLIO &nbsp; · &nbsp; LABELLED SNAPSHOT, INDEPENDENT RESEARCH';
    const foot = document.querySelector('.side-footer');
    if (foot) foot.textContent = 'PUBLIC PORTFOLIO · 01 / 26';
    const ribbonLeft = document.querySelector('.desk-ribbon-left');
    if (ribbonLeft) {
      ribbonLeft.querySelectorAll('span').forEach((span) => {
        if (span.classList.contains('ribbon-edition')) span.textContent = 'DEMO / 01';
        else if (!span.classList.contains('ribbon-divider') && /LOCAL|FINNHUB|PORTFOLIO|WORKSTATION/i.test(span.textContent)) {
          span.innerHTML = /FINNHUB/i.test(span.textContent)
            ? 'BUNDLED <b>SNAPSHOT</b>'
            : 'PUBLIC <b>PORTFOLIO</b>';
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