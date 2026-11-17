/**
 * Shared public quotes helper for Vercel serverless /api/quote(s).
 * Reads FINNHUB_API_KEY (and optionally MASSIVE_API_KEY presence) from env only.
 * Never echoes secret values. Falls back to site/demo/snapshot.json when keys
 * are missing or the provider errors.
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const FINNHUB_QUOTE = 'https://finnhub.io/api/v1/quote';
const CACHE_TTL_MS = 60_000;
const MAX_SYMBOLS = 12;
const DEFAULT_WATCH = [
  'AAPL',
  'NVDA',
  'MSFT',
  'GOOGL',
  'AMZN',
  'META',
  'TSLA',
  'AMD',
  'PLTR',
  'JPM',
  'KO',
  'DIS',
  'NFLX',
  'BA',
  'TSM',
  'TTWO',
];

/** @type {Map<string, { at: number, item: object }>} */
const quoteCache = new Map();

/** @type {{ symbols: Set<string>, loadedAt: number } | null} */
let allowlistState = null;

function envFlag(env, name) {
  const value = env && typeof env[name] === 'string' ? env[name].trim() : '';
  return Boolean(value);
}

function readKey(env, names) {
  for (const name of names) {
    const raw = env?.[name];
    if (typeof raw === 'string' && raw.trim()) return raw.trim();
  }
  return '';
}

function validSymbol(raw) {
  const sym = String(raw || '')
    .trim()
    .toUpperCase();
  // Match server.py SYMBOL_RE intent — reject path-like input.
  if (!/^[A-Z0-9][A-Z0-9.\-:_]{0,11}$/.test(sym)) return '';
  return sym;
}

function snapshotPath(cwd) {
  return path.join(cwd || process.cwd(), 'site', 'demo', 'snapshot.json');
}

function loadSnapshot(cwd) {
  try {
    const text = fs.readFileSync(snapshotPath(cwd), 'utf8');
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function buildAllowlist(cwd) {
  const now = Date.now();
  if (allowlistState && now - allowlistState.loadedAt < 300_000) return allowlistState.symbols;
  const symbols = new Set(DEFAULT_WATCH);
  const snap = loadSnapshot(cwd);
  for (const sym of snap?.watchlist || []) {
    const v = validSymbol(sym);
    if (v) symbols.add(v);
  }
  for (const sym of Object.keys(snap?.quotes || {})) {
    const v = validSymbol(sym);
    if (v) symbols.add(v);
  }
  for (const row of snap?.heatmap?.rows || []) {
    const v = validSymbol(row?.symbol);
    if (v) symbols.add(v);
  }
  allowlistState = { symbols, loadedAt: now };
  return symbols;
}

function validProviderQuote(result) {
  if (!result || typeof result !== 'object') return false;
  const c = result.c;
  const stamp = result.t;
  const pc = result.pc;
  return (
    typeof c === 'number' &&
    Number.isFinite(c) &&
    c > 0 &&
    c <= 1e9 &&
    typeof stamp === 'number' &&
    Number.isFinite(stamp) &&
    stamp === Math.floor(stamp) &&
    stamp > 946684800 &&
    typeof pc === 'number' &&
    Number.isFinite(pc) &&
    pc > 0
  );
}

function normalizeQuote(raw) {
  const c = Number(raw.c);
  const pc = Number(raw.pc);
  const t = Math.floor(Number(raw.t));
  const o = Number(raw.o);
  const h = Number(raw.h);
  const l = Number(raw.l);
  const dp =
    typeof raw.dp === 'number' && Number.isFinite(raw.dp)
      ? raw.dp
      : pc > 0
        ? ((c - pc) / pc) * 100
        : null;
  return {
    c,
    pc,
    t,
    o: Number.isFinite(o) && o > 0 ? o : c,
    h: Number.isFinite(h) && h > 0 ? h : c,
    l: Number.isFinite(l) && l > 0 ? l : c,
    dp,
  };
}

function snapshotQuoteItem(sym, snap, nowSec) {
  const hit = snap?.quotes?.[sym];
  let c;
  let pc;
  if (hit && Number.isFinite(hit.c) && Number.isFinite(hit.pc) && hit.pc > 0) {
    c = hit.c;
    pc = hit.pc;
  } else {
    const row = snap?.heatmap?.rows?.find((r) => r.symbol === sym);
    if (row && Number.isFinite(row.price) && row.price > 0 && Number.isFinite(row.change)) {
      c = row.price;
      pc = c / (1 + row.change / 100);
    }
  }
  if (!(Number.isFinite(c) && Number.isFinite(pc) && pc > 0 && c > 0)) {
    return {
      symbol: sym,
      quote: null,
      status: 'unavailable',
      source: 'Portfolio demo bundle',
      demoMode: true,
      error: 'Symbol not in bundled snapshot.',
    };
  }
  const quote = {
    c,
    pc,
    t: nowSec,
    o: c - 0.3,
    h: c + 1.5,
    l: c - 1.6,
    dp: ((c - pc) / pc) * 100,
  };
  return {
    symbol: sym,
    quote,
    source: 'Portfolio demo bundle',
    status: 'ok',
    cached: true,
    demoMode: true,
  };
}

function parseSymbols(mode, query, snap) {
  let raw = [];
  if (mode === 'quote') {
    raw = [query.symbol || query.symbols || 'AAPL'];
  } else {
    const joined = query.symbols || (snap?.watchlist || DEFAULT_WATCH).slice(0, MAX_SYMBOLS).join(',');
    raw = String(joined).split(',');
  }
  const out = [];
  const seen = new Set();
  for (const piece of raw) {
    const sym = validSymbol(piece);
    if (!sym || seen.has(sym)) continue;
    seen.add(sym);
    out.push(sym);
    if (out.length >= MAX_SYMBOLS) break;
  }
  return out;
}

async function fetchFinnhubQuote(sym, token, fetchImpl) {
  const url = `${FINNHUB_QUOTE}?symbol=${encodeURIComponent(sym)}&token=${encodeURIComponent(token)}`;
  const res = await fetchImpl(url, {
    headers: {
      Accept: 'application/json',
      'User-Agent': 'MarketDesk-Reborn/public-quotes (+https://github.com/wj82011/sixth-form-stocks)',
    },
  });
  if (res.status === 401 || res.status === 403) {
    const err = new Error('Finnhub rejected the server key.');
    err.status = res.status;
    err.kind = 'auth';
    throw err;
  }
  if (res.status === 429) {
    const err = new Error('Finnhub rate limit reached.');
    err.status = 429;
    err.kind = 'rate_limit';
    throw err;
  }
  if (!res.ok) {
    const err = new Error(`Finnhub HTTP ${res.status}`);
    err.status = res.status;
    err.kind = 'http';
    throw err;
  }
  return res.json();
}

/**
 * Core handler used by Vercel routes and unit tests.
 * @param {{ mode?: 'quote'|'quotes', query?: Record<string,string>, env?: NodeJS.ProcessEnv, fetchImpl?: typeof fetch, now?: number, cwd?: string, cache?: Map }} opts
 */
async function handleQuotesRequest(opts = {}) {
  const mode = opts.mode === 'quote' ? 'quote' : 'quotes';
  const env = opts.env || process.env;
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  const now = opts.now || Date.now();
  const cwd = opts.cwd || process.cwd();
  const cache = opts.cache || quoteCache;
  const snap = loadSnapshot(cwd);
  const allow = buildAllowlist(cwd);
  const symbols = parseSymbols(mode, opts.query || {}, snap);

  if (!symbols.length) {
    return {
      statusCode: 400,
      body: {
        items: [],
        error: 'Request 1–12 symbols at a time.',
        demoMode: true,
        received_at: now,
      },
    };
  }

  const rejected = symbols.filter((sym) => !allow.has(sym));
  if (rejected.length) {
    return {
      statusCode: 400,
      body: {
        items: rejected.map((symbol) => ({
          symbol,
          status: 'error',
          quote: null,
          error: 'Symbol not on the public allowlist.',
          kind: 'not_allowlisted',
        })),
        error: 'One or more symbols are outside the public allowlist.',
        demoMode: true,
        received_at: now,
      },
    };
  }

  const finnhubKey = readKey(env, ['FINNHUB_API_KEY', 'FINNHUB_TOKEN', 'FINNHUB_KEY']);
  const massivePresent = envFlag(env, 'MASSIVE_API_KEY') || envFlag(env, 'POLYGON_API_KEY') || envFlag(env, 'MASSIVE_KEY');
  const meta = {
    provider: finnhubKey ? 'finnhub' : 'snapshot',
    finnhubConfigured: Boolean(finnhubKey),
    massiveConfigured: massivePresent,
    cache_ttl_ms: CACHE_TTL_MS,
    received_at: now,
  };

  if (!finnhubKey) {
    const items = symbols.map((sym) => snapshotQuoteItem(sym, snap, Math.floor(now / 1000)));
    return {
      statusCode: 200,
      body: {
        items,
        ...meta,
        demoMode: true,
        fallback: 'snapshot',
        notice:
          'FINNHUB_API_KEY is not set on this host. Serving labelled DEMO DATA from the bundled snapshot. Add the key in Vercel project env (not Cursor secrets).',
      },
    };
  }

  if (typeof fetchImpl !== 'function') {
    const items = symbols.map((sym) => snapshotQuoteItem(sym, snap, Math.floor(now / 1000)));
    return {
      statusCode: 200,
      body: {
        items,
        ...meta,
        provider: 'snapshot',
        demoMode: true,
        fallback: 'snapshot',
        notice: 'Fetch unavailable in this runtime; using snapshot fallback.',
      },
    };
  }

  const items = [];
  let hardFailure = null;

  for (const sym of symbols) {
    const cached = cache.get(sym);
    if (cached && now - cached.at < CACHE_TTL_MS) {
      items.push({ ...cached.item, cached: true });
      continue;
    }
    if (hardFailure) {
      items.push({
        symbol: sym,
        status: 'skipped',
        quote: null,
        error: 'Not requested because the preceding Finnhub request failed.',
        kind: 'skipped_due_to_provider_failure',
        demoMode: true,
      });
      continue;
    }
    try {
      const raw = await fetchFinnhubQuote(sym, finnhubKey, fetchImpl);
      if (!validProviderQuote(raw)) {
        items.push({
          symbol: sym,
          quote: null,
          status: 'unavailable',
          source: 'Finnhub REST quote',
          error: 'No valid positive price and provider timestamp received.',
        });
        continue;
      }
      const quote = normalizeQuote(raw);
      const item = {
        symbol: sym,
        quote,
        source: 'Finnhub REST quote',
        status: 'ok',
        cached: false,
        stale: Math.floor(now / 1000) - quote.t > 900,
      };
      cache.set(sym, { at: now, item });
      items.push(item);
    } catch (err) {
      const status = err?.status || 502;
      const kind = err?.kind || 'network';
      hardFailure = { status, kind, message: err?.message || 'Provider error' };
      items.push({
        symbol: sym,
        status: 'error',
        quote: null,
        error: hardFailure.message,
        code: status,
        kind,
      });
      if (status === 401 || status === 403 || status === 429 || kind === 'network') {
        // Remaining symbols marked skipped on next loops via hardFailure.
      }
    }
  }

  const liveOk = items.filter((it) => it.status === 'ok' && it.quote && !it.demoMode);
  if (!liveOk.length) {
    // Provider miss / auth / rate limit → labelled snapshot fallback (still HTTP 200 for UI).
    const fallbackItems = symbols.map((sym) => {
      const snapItem = snapshotQuoteItem(sym, snap, Math.floor(now / 1000));
      const live = items.find((it) => it.symbol === sym);
      if (live && live.status !== 'ok') {
        snapItem.provider_error = { status: live.status, kind: live.kind, code: live.code, error: live.error };
      }
      return snapItem;
    });
    const statusCode =
      hardFailure?.status === 401 || hardFailure?.status === 403
        ? 200
        : hardFailure?.status === 429
          ? 200
          : 200;
    return {
      statusCode,
      body: {
        items: fallbackItems,
        ...meta,
        provider: 'snapshot',
        demoMode: true,
        fallback: 'snapshot',
        provider_error: hardFailure
          ? { kind: hardFailure.kind, code: hardFailure.status, error: hardFailure.message }
          : { kind: 'unavailable', error: 'No live quotes returned.' },
        notice:
          'Live quotes unavailable; serving labelled DEMO DATA from the bundled snapshot. Keys are never sent to the browser.',
      },
    };
  }

  // Partial success: fill gaps from snapshot so the desk stays populated.
  const mixed = items.map((it) => {
    if (it.status === 'ok' && it.quote) return it;
    const snapItem = snapshotQuoteItem(it.symbol, snap, Math.floor(now / 1000));
    return {
      ...snapItem,
      status: 'ok',
      mixed: true,
      provider_error: { status: it.status, kind: it.kind, error: it.error },
    };
  });

  return {
    statusCode: 200,
    body: {
      items: mixed,
      ...meta,
      demoMode: false,
      live: true,
      notice: 'Live Finnhub quotes via serverless proxy (short TTL cache).',
    },
  };
}

function createVercelHandler(mode, options = {}) {
  return async function handler(req, res) {
    if (req.method && req.method !== 'GET' && req.method !== 'HEAD') {
      res.statusCode = 405;
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Allow', 'GET, HEAD');
      res.end(JSON.stringify({ error: 'Method not allowed', demoMode: true }));
      return;
    }
    const url = new URL(req.url || '/', 'http://localhost');
    const query = Object.fromEntries(url.searchParams.entries());
    const env = options.env || process.env;
    const result = await handleQuotesRequest({
      mode,
      query,
      env,
      cwd: options.cwd,
      fetchImpl: options.fetchImpl,
      cache: options.cache,
      now: options.now,
    });
    const body = result.body;
    // Defence in depth: never leak env secret values into JSON.
    const rendered = JSON.stringify(body);
    for (const name of ['FINNHUB_API_KEY', 'FINNHUB_TOKEN', 'FINNHUB_KEY', 'MASSIVE_API_KEY', 'POLYGON_API_KEY', 'MASSIVE_KEY']) {
      const secret = env[name];
      if (secret && secret.length >= 8 && rendered.includes(secret)) {
        res.statusCode = 500;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.setHeader('Cache-Control', 'no-store');
        res.end(JSON.stringify({ error: 'Refusing to return a response that contained a secret.', demoMode: true }));
        return;
      }
    }
    res.statusCode = result.statusCode;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', `public, max-age=30, s-maxage=${Math.floor(CACHE_TTL_MS / 1000)}`);
    res.end(rendered);
  };
}

function resetQuotesApiState() {
  quoteCache.clear();
  allowlistState = null;
}

module.exports = {
  CACHE_TTL_MS,
  MAX_SYMBOLS,
  DEFAULT_WATCH,
  handleQuotesRequest,
  createVercelHandler,
  resetQuotesApiState,
  validSymbol,
  validProviderQuote,
  buildAllowlist,
  loadSnapshot,
  readKey,
};
