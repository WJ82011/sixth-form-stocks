/* Look43 candle toggle + OHLC load path for public/demo hosts. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..');
const lookSrc = fs.readFileSync(path.join(root, 'site/look43.js'), 'utf8');
const cloudSrc = fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8');
const chartSrc = fs.readFileSync(path.join(root, 'site/chart43.js'), 'utf8');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'site/demo/snapshot.json'), 'utf8'));

assert.match(lookSrc, /\/api\/saved-daily/);
assert.match(lookSrc, /\/api\/candles/);
assert.match(lookSrc, /whenSnapshotReady/);
assert.match(lookSrc, /chart43-series/);
assert.match(lookSrc, /setChartRange\('1M'\)/);
assert.match(lookSrc, /Ask48|changeView\('intelligence'\)/);
assert.match(lookSrc, /Desk68|changeView\(map/);
assert.match(cloudSrc, /\/api\/v3\/annotate60/);
assert.match(chartSrc, /marketdesk:layout/);
assert.match(chartSrc, /No chart prices to reset yet/);
assert.ok(snapshot.dailyBars.AAPL.o.length > 50, 'snapshot OHLC for candles');

const calls = [];
const nodes = new Map();
function el(id) {
  if (nodes.has(id)) return nodes.get(id);
  const node = {
    id,
    dataset: {},
    style: {},
    hidden: false,
    textContent: '',
    innerHTML: '',
    children: [],
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    attrs: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k]; },
    querySelector() { return null; },
    querySelectorAll(sel) {
      if (sel.includes('data-look-series')) return seriesButtons;
      if (sel.includes('data-look-range')) return [];
      return [];
    },
    append(...kids) { this.children.push(...kids); },
    prepend(...kids) { this.children.unshift(...kids); },
    after(node) { this._after = node; },
    before() {},
    replaceChildren(...kids) { this.children = kids; },
    addEventListener() {},
    remove() { nodes.delete(this.id); },
    closest() { return null; },
  };
  nodes.set(id, node);
  return node;
}

const seriesButtons = [
  { dataset: { lookSeries: 'line' }, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } },
  { dataset: { lookSeries: 'candles' }, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } },
];

for (const id of [
  'look43-tools', 'look43-head', 'look43-coverage', 'look43-feed', 'look43-watch',
  'look43-heat', 'look43-tape', 'look43-events', 'overview-ranges', 'home43',
  'main-chart-panel', 'overview-chart', 'chart-observed-summary', 'overview-chart-note',
  'chart-forecast-legend', 'chart-data-coverage',
]) el(id);

const body = {
  classList: { add() {}, contains() { return true; } },
  dataset: { edition: 'signal', look: 'standard' },
  append() {},
};

const E = {
  selected: 'AAPL',
  range: '1D',
  watch: ['AAPL', 'NVDA'],
  names: { AAPL: 'Apple' },
  savedSession: false,
  chartPoints: [{ t: Date.now() - 86400000, p: 100 }, { t: Date.now(), p: 101 }],
  demoMode: true,
  verifiedAt: 0,
  backgroundCollector: false,
  quotes: new Map(),
};

let chartDraws = 0;
const rangesSet = [];

const context = {
  console,
  window: {},
  document: {
    body,
    readyState: 'complete',
    documentElement: { dataset: { demoMode: 'true' } },
    getElementById: (id) => el(id),
    querySelector: (sel) => (sel === '.view.active' ? { id: 'view-home' } : null),
    querySelectorAll: (sel) => {
      if (sel.includes('data-look-series')) return seriesButtons;
      if (sel.includes('#overview-ranges button')) return [];
      if (sel.includes('#look43-mode')) return [];
      if (sel.includes('#look43-rail')) return [];
      return [];
    },
    createElement: (tag) => ({
      tagName: tag,
      id: '',
      className: '',
      dataset: {},
      style: {},
      innerHTML: '',
      textContent: '',
      children: [],
      attrs: {},
      setAttribute(k, v) { this.attrs[k] = String(v); },
      append(...kids) { this.children.push(...kids); },
      prepend(...kids) { this.children.unshift(...kids); },
      addEventListener() {},
      querySelector() { return null; },
      querySelectorAll(sel) {
        if (sel.includes('data-look-series')) return seriesButtons;
        return [];
      },
    }),
    addEventListener() {},
    visibilityState: 'visible',
  },
  localStorage: {
    store: { 'md-look-series': 'line' },
    getItem(k) { return this.store[k] || null; },
    setItem(k, v) { this.store[k] = String(v); },
  },
  sessionStorage: { getItem() { return null; }, setItem() {} },
  E,
  Map,
  Set,
  Math,
  Date,
  Number,
  String,
  Array,
  Object,
  JSON,
  Promise,
  setInterval() {},
  setTimeout: (fn) => fn(),
  clearTimeout() {},
  escapeHtml: (s) => String(s),
  quoteFor: () => ({ p: 190, change: 1.2 }),
  changeView() {},
  setSelected(sym) { E.selected = sym; },
  setChartRange(range) { rangesSet.push(range); E.range = range; },
  loadChart() {},
  drawChart() { chartDraws += 1; },
  toast() {},
  api: async (url) => {
    calls.push(url);
    const sym = new URL('http://x' + url).searchParams.get('symbol') || 'AAPL';
    const bars = snapshot.dailyBars[sym] || snapshot.dailyBars.AAPL;
    return {
      status: 'ok',
      source: 'Portfolio demo bundle · historical daily closes',
      candles: bars,
      cloudDemo: true,
    };
  },
  MarketDeskHost: {
    demoMode: true,
    whenSnapshotReady: async () => snapshot,
  },
  STOCK_DIRECTORY: [{ symbol: 'AAPL', name: 'Apple', listingName: 'Apple Inc' }],
  DIRECTORY_BY_SYMBOL: { AAPL: { symbol: 'AAPL' } },
  CustomEvent: class CustomEvent {
    constructor(type, init) { this.type = type; this.detail = init?.detail; }
  },
};

context.window = context;
context.addEventListener = () => {};
context.window.addEventListener = () => {};
vm.runInNewContext(lookSrc, context);
const Look43 = context.Look43;
assert.ok(Look43, 'Look43 exported');

(async () => {
  await Look43.loadCandles(true);
  assert.ok(Look43.bars.length > 50, 'loaded OHLC bars from snapshot path');
  assert.ok(calls.some((u) => u.includes('/api/saved-daily')), 'uses saved-daily first');

  E.range = '1D';
  await Look43.setSeries('candles');
  assert.equal(Look43.series, 'candles');
  assert.equal(E.range, '1M', 'candles bump off intraday 1D');
  assert.equal(rangesSet.at(-1), '1M');
  assert.equal(context.localStorage.getItem('md-look-series'), 'candles');

  const from = Look43.bars[0].t;
  const to = Look43.bars.at(-1).t;
  const shown = Look43.candleBars(from, to);
  assert.ok(shown && shown.length > 10, 'candleBars returns OHLC for daily range');

  E.range = '1D';
  assert.equal(Look43.candleBars(from, to), null, 'intraday keeps line (no fake minute OHLC)');

  await Look43.setSeries('line');
  assert.equal(Look43.series, 'line');
  E.range = '1M';
  assert.equal(Look43.candleBars(from, to), null, 'line mode suppresses candles');

  console.log('PASS look43 candles', { bars: Look43.bars.length, source: Look43.barsSource, draws: chartDraws });
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
