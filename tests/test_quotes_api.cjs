/* Unit tests for serverless quotes helper — no real provider keys required. */
'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

const root = path.join(__dirname, '..');
const {
  handleQuotesRequest,
  resetQuotesApiState,
  createVercelHandler,
  CACHE_TTL_MS,
  MAX_SYMBOLS,
  validSymbol,
} = require(path.join(root, 'lib/quotes-api.js'));

function fakeFetchFactory(handler) {
  return async function fakeFetch(url) {
    return handler(String(url));
  };
}

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return body;
    },
  };
}

async function main() {
  resetQuotesApiState();

  assert.equal(validSymbol('aapl'), 'AAPL');
  assert.equal(validSymbol('../../etc'), '');
  assert.ok(CACHE_TTL_MS >= 30_000);
  assert.equal(MAX_SYMBOLS, 12);

  // No keys → snapshot fallback, demo honesty, distinct watchlist moves.
  {
    const result = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'AAPL,NVDA,MSFT' },
      env: {},
      cwd: root,
      cache: new Map(),
      now: 1_700_000_000_000,
    });
    assert.equal(result.statusCode, 200);
    assert.equal(result.body.demoMode, true);
    assert.equal(result.body.fallback, 'snapshot');
    assert.equal(result.body.finnhubConfigured, false);
    assert.equal(result.body.items.length, 3);
    const pcts = result.body.items.map((it) => {
      assert.equal(it.status, 'ok');
      assert.equal(it.demoMode, true);
      assert.ok(it.quote.c > 0 && it.quote.pc > 0);
      return +(((it.quote.c - it.quote.pc) / it.quote.pc) * 100).toFixed(2);
    });
    assert.ok(new Set(pcts).size >= 2, 'fallback quotes must stay distinct across symbols');
    const blob = JSON.stringify(result.body);
    assert.ok(!blob.includes('token='));
    assert.ok(!/FINNHUB_API_KEY\s*[:=]\s*\S+/.test(blob));
  }

  // Single-symbol route shape.
  {
    const result = await handleQuotesRequest({
      mode: 'quote',
      query: { symbol: 'TTWO' },
      env: {},
      cwd: root,
      cache: new Map(),
    });
    assert.equal(result.body.items.length, 1);
    assert.equal(result.body.items[0].symbol, 'TTWO');
    assert.equal(result.body.demoMode, true);
    assert.ok(result.body.items[0].quote?.c > 0, 'TTWO must have a DEMO DATA price');
  }

  // Missing site/demo/snapshot.json (Vercel lambda FS) → embedded watchlist fallback still prices TTWO.
  {
    resetQuotesApiState();
    const result = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'TTWO,AAPL,NVDA,MSFT' },
      env: {},
      cwd: path.join(root, 'does-not-exist-for-snapshot'),
      cache: new Map(),
    });
    assert.equal(result.statusCode, 200);
    assert.equal(result.body.demoMode, true);
    assert.equal(result.body.fallback, 'snapshot');
    for (const sym of ['TTWO', 'AAPL', 'NVDA', 'MSFT']) {
      const item = result.body.items.find((it) => it.symbol === sym);
      assert.ok(item, sym);
      assert.equal(item.status, 'ok');
      assert.ok(item.quote && item.quote.c > 0 && item.quote.pc > 0, sym + ' needs embedded DEMO DATA quote');
    }
  }

  // Allowlist rejects unknown tickers (valid format, not in snapshot/directory).
  {
    const result = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'ZZZZTOP' },
      env: { FINNHUB_API_KEY: 'test-key-should-never-appear-in-body-xyz' },
      cwd: root,
      cache: new Map(),
      fetchImpl: fakeFetchFactory(() => {
        throw new Error('should not call provider for rejected symbols');
      }),
    });
    assert.equal(result.statusCode, 400);
    assert.match(result.body.error || '', /allowlist/i);
    assert.ok(!JSON.stringify(result.body).includes('test-key-should-never-appear-in-body-xyz'));
  }

  // Live Finnhub success path (mocked fetch) — never echo the key.
  {
    const secret = 'fh-secret-unit-test-do-not-leak-001';
    const cache = new Map();
    const calls = [];
    const fetchImpl = fakeFetchFactory((url) => {
      calls.push(url);
      assert.ok(url.includes('token='));
      assert.ok(!url.includes(secret) || url.includes(`token=${encodeURIComponent(secret)}`));
      const sym = new URL(url).searchParams.get('symbol');
      const prices = { AAPL: { c: 190.5, pc: 188.0, t: 1_700_000_100 }, NVDA: { c: 880.2, pc: 870.1, t: 1_700_000_100 } };
      const q = prices[sym];
      return jsonResponse(200, { c: q.c, pc: q.pc, t: q.t, o: q.c - 1, h: q.c + 2, l: q.c - 2, dp: ((q.c - q.pc) / q.pc) * 100 });
    });
    const result = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'AAPL,NVDA' },
      env: { FINNHUB_API_KEY: secret, MASSIVE_API_KEY: 'massive-secret-also-hidden' },
      cwd: root,
      cache,
      fetchImpl,
      now: 1_700_000_200_000,
    });
    assert.equal(result.statusCode, 200);
    assert.equal(result.body.demoMode, false);
    assert.equal(result.body.live, true);
    assert.equal(result.body.finnhubConfigured, true);
    assert.equal(result.body.massiveConfigured, true);
    assert.equal(result.body.items.length, 2);
    assert.ok(result.body.items.every((it) => it.status === 'ok' && it.quote.c > 0));
    const pctA = +(((result.body.items[0].quote.c - result.body.items[0].quote.pc) / result.body.items[0].quote.pc) * 100).toFixed(2);
    const pctB = +(((result.body.items[1].quote.c - result.body.items[1].quote.pc) / result.body.items[1].quote.pc) * 100).toFixed(2);
    assert.notEqual(pctA, pctB, 'live quotes must be distinct');
    const blob = JSON.stringify(result.body);
    assert.ok(!blob.includes(secret), 'must never echo FINNHUB_API_KEY');
    assert.ok(!blob.includes('massive-secret-also-hidden'), 'must never echo MASSIVE_API_KEY');
    assert.equal(calls.length, 2);

    // Cache hit — second call should not re-fetch.
    const again = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'AAPL,NVDA' },
      env: { FINNHUB_API_KEY: secret },
      cwd: root,
      cache,
      fetchImpl,
      now: 1_700_000_200_000 + 10_000,
    });
    assert.equal(again.body.items.every((it) => it.cached === true), true);
    assert.equal(calls.length, 2, 'TTL cache should avoid extra Finnhub calls');
  }

  // Provider 429 → structured fallback to snapshot (still usable UI payload).
  {
    const secret = 'fh-secret-rate-limit-test';
    const result = await handleQuotesRequest({
      mode: 'quotes',
      query: { symbols: 'AAPL,NVDA' },
      env: { FINNHUB_API_KEY: secret },
      cwd: root,
      cache: new Map(),
      fetchImpl: fakeFetchFactory(() => jsonResponse(429, { error: 'rate limit' })),
      now: Date.now(),
    });
    assert.equal(result.statusCode, 200);
    assert.equal(result.body.demoMode, true);
    assert.equal(result.body.fallback, 'snapshot');
    assert.equal(result.body.provider_error?.code, 429);
    assert.ok(result.body.items.every((it) => it.demoMode && it.quote));
    assert.ok(!JSON.stringify(result.body).includes(secret));
  }

  // Provider 401 → snapshot fallback, no key leak.
  {
    const secret = 'fh-secret-unauthorized-test';
    const result = await handleQuotesRequest({
      mode: 'quote',
      query: { symbol: 'AAPL' },
      env: { FINNHUB_API_KEY: secret },
      cwd: root,
      cache: new Map(),
      fetchImpl: fakeFetchFactory(() => jsonResponse(401, { error: 'invalid' })),
    });
    assert.equal(result.body.demoMode, true);
    assert.equal(result.body.provider_error?.code, 401);
    assert.ok(!JSON.stringify(result.body).includes(secret));
  }

  // Vercel handler wiring smoke (mock res) — empty env so no real keys are used.
  {
    const handler = createVercelHandler('quotes', { env: {}, cwd: root, cache: new Map() });
    let statusCode = 0;
    let body = '';
    const headers = {};
    await handler(
      { method: 'GET', url: '/api/quotes?symbols=AAPL' },
      {
        set statusCode(v) {
          statusCode = v;
        },
        get statusCode() {
          return statusCode;
        },
        setHeader(k, v) {
          headers[k] = v;
        },
        end(text) {
          body = text;
        },
      }
    );
    assert.equal(statusCode, 200);
    const parsed = JSON.parse(body);
    assert.equal(parsed.demoMode, true);
    assert.equal(parsed.items[0].symbol, 'AAPL');
    assert.equal(headers['Content-Type'], 'application/json; charset=utf-8');
  }

  // Repo wiring checks.
  assert.ok(fs.existsSync(path.join(root, 'api/quotes.js')));
  assert.ok(fs.existsSync(path.join(root, 'api/quote.js')));
  const cloud = fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8');
  assert.ok(cloud.includes('tryLiveQuoteApi'), 'cloud-host prefers live /api/quotes');
  assert.ok(cloud.includes('usableQuoteItem'), 'live probe requires usable quote payloads');
  assert.ok(cloud.includes('LIVE QUOTES (CACHED)'), 'live honesty label');
  assert.ok(cloud.includes('quoteSource'), 'tracks quote source');
  const wiring = fs.readFileSync(path.join(root, 'site/demo-wiring.js'), 'utf8');
  assert.ok(wiring.includes("quoteSource === 'live'"), 'wiring respects live quotes chrome');
  const deploy = fs.readFileSync(path.join(root, 'docs/DEPLOY-VERCEL.md'), 'utf8');
  assert.ok(deploy.includes('Cursor Cloud Agent secrets ≠ Vercel'));
  assert.ok(deploy.includes('FINNHUB_API_KEY'));
  assert.ok(deploy.includes('Environment Variables'));
  assert.ok(deploy.includes('No saved price'), 'deploy doc covers blank quote symptom');
  const vercel = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
  assert.equal(vercel.outputDirectory, 'site');
  assert.ok(vercel.functions['api/quotes.js']);
  assert.ok(vercel.functions['api/quote.js']);
  assert.match(String(vercel.functions['api/quotes.js'].includeFiles || ''), /demo-quotes-fallback/);
  assert.match(String(vercel.functions['api/quote.js'].includeFiles || ''), /snapshot\.json/);
  assert.ok(fs.existsSync(path.join(root, 'lib/demo-quotes-fallback.json')), 'embedded DEMO DATA quotes present');
  const embedded = JSON.parse(fs.readFileSync(path.join(root, 'lib/demo-quotes-fallback.json'), 'utf8'));
  assert.ok(embedded.quotes?.TTWO?.c > 0, 'fallback includes TTWO');
  assert.ok(embedded.quotes?.AAPL?.c > 0, 'fallback includes AAPL');

  console.log('quotes API tests OK · no real keys used');
}

globalThis.quotesApiTestResult = main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
  throw err;
});
