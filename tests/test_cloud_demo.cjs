/* Snapshot + shim wiring checks for the public Vercel demo (no network). */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'site/demo/snapshot.json'), 'utf8'));
const shim = fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8');

assert.ok(snapshot.version >= 3, 'snapshot version');
assert.ok(snapshot.learning.TTWO.rows.length >= 3, 'learning TTWO rows');
assert.ok(snapshot.alerts.alerts.some((a) => a.status === 'armed'), 'demo armed alert');
assert.ok(snapshot.alerts.events.length >= 1, 'demo alert history');
assert.equal(snapshot.heatmap.rows.length, snapshot.screener.rows.length, 'heatmap/screener parity');
assert.ok(snapshot.heatmap.rows.length >= 200, 'directory heatmap rows');
const coloured = snapshot.heatmap.rows.filter((r) => Number.isFinite(r.change));
assert.ok(coloured.length >= 180, 'most tiles should have a period change');
assert.ok(snapshot.dailyBars.AAPL.c.length > 100, 'AAPL daily chart series');
assert.ok(snapshot.overview60.equity.included > 50, 'overview60 equity included');
assert.ok(snapshot.crypto.board.rows.length >= 6, 'crypto board rows');
// Quotes must be distinct session moves — never a flat ~+1.01% book.
{
  const watch = snapshot.watchlist || Object.keys(snapshot.quotes || {});
  const pcts = watch.map((sym) => {
    const q = snapshot.quotes[sym];
    assert.ok(q && q.c > 0 && q.pc > 0, `quote pair for ${sym}`);
    return +(((q.c - q.pc) / q.pc) * 100).toFixed(2);
  });
  assert.ok(new Set(pcts).size >= Math.min(8, pcts.length), 'watchlist % moves must differ across symbols');
  assert.notEqual(
    +(((snapshot.quotes.AAPL.c - snapshot.quotes.AAPL.pc) / snapshot.quotes.AAPL.pc) * 100).toFixed(2),
    +(((snapshot.quotes.NVDA.c - snapshot.quotes.NVDA.pc) / snapshot.quotes.NVDA.pc) * 100).toFixed(2),
    'AAPL and NVDA day % must differ'
  );
  const flat101 = pcts.filter((p) => Math.abs(p - 1.01) < 0.05).length;
  assert.ok(flat101 < pcts.length / 2, 'must not apply ~+1.01% to most symbols');
}
assert.match(String(snapshot.label || ''), /DEMO DATA|not live/i, 'snapshot stays honestly labelled');
assert.ok(!fs.readFileSync(path.join(root, 'tools/export-demo-snapshot.py'), 'utf8').includes("price(sym) * 0.99"), 'exporter must not force pc=c*0.99');
assert.ok(fs.existsSync(path.join(root, 'tools/demo_fixtures/equity_bars.json')), 'equity fixture present');
assert.ok(fs.existsSync(path.join(root, 'tools/demo_data_sources.py')), 'free-provider helper present');
assert.ok(snapshot.tape.AAPL.events.length > 20, 'tape events');
assert.ok(snapshot.intelligence.TTWO.hour.count > 0, 'intelligence hour points');
assert.equal(snapshot.forecasts.TTWO.status, 'learned', 'TTWO shown forecast');
assert.equal(snapshot.forecasts.AMD.status, 'withheld', 'AMD withheld forecast');
assert.ok(Object.keys(snapshot.workspace.names).length >= 200, 'workspace name index');
assert.ok(Array.isArray(snapshot.workspace.notes) && snapshot.workspace.notes.length >= 1, 'demo research notes');
assert.ok(snapshot.workspace.notes.every((n) => n.title && n.thesis && n.risk && n.evidence && n.date), 'notes use thesis/risk/evidence schema');
assert.ok(snapshot.workspace.portfolio?.trades?.length >= 2, 'demo paper portfolio trades');
assert.ok(snapshot.workspace.v3?.ledger?.length >= 3, 'demo V3 practice ledger');
assert.ok(snapshot.workspace.v3?.marks?.length >= 2, 'demo V3 dated marks');
assert.ok(snapshot.workspace.v3?.research?.projects?.length >= 1, 'demo research project');
assert.ok(snapshot.workspace.v3.research.projects[0].items?.length >= 1, 'demo research project has evidence items');
assert.ok(snapshot.workspace.v3Calc?.portfolio?.holdings?.length >= 2, 'precomputed demo holdings');
assert.match(String(snapshot.workspace.v3Calc.notice || snapshot.workspace.v3Calc.portfolio.notice || ''), /demo|synthetic|labelled/i, 'portfolio calc stays labelled');

for (const needle of [
  '/api/v3/heatmap',
  '/api/screener',
  '/api/v3/overview60',
  '/api/v3/crypto-chart',
  '/api/intelligence',
  '/api/v3/forecast61',
  '/api/v3/learning',
  '/api/v3/desk50',
  '/api/v3/overnight51',
  '/api/collector',
]) {
  assert.ok(shim.includes(needle), `shim routes ${needle}`);
}
const indexHtml = fs.readFileSync(path.join(root, 'site/index.html'), 'utf8');
assert.ok(indexHtml.includes('cloud-host.js'));
assert.ok(indexHtml.includes('public-host-mode.js'), 'index loads shared public-host detection first');
assert.ok(
  indexHtml.indexOf('public-host-mode.js') < indexHtml.indexOf('cloud-host.js'),
  'public-host-mode.js must precede cloud-host.js'
);
const cloud = fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8');
assert.ok(!cloud.includes('XMLHttpRequest'), 'demo snapshot must not use sync XHR on the main thread');
assert.ok(cloud.includes('whenSnapshotReady'), 'demo host exposes async snapshot readiness');
assert.ok(cloud.includes('MarketDeskPublicHost'), 'cloud-host uses shared public-host resolver');
assert.ok(indexHtml.includes('release.js'));
assert.ok(indexHtml.includes('view-loader.js'));
assert.ok(indexHtml.includes('demo-wiring.js'));
assert.ok(fs.existsSync(path.join(root, 'site/demo-wiring.js')));
assert.ok(fs.existsSync(path.join(root, 'site/demo-polish.js')));
assert.ok(fs.existsSync(path.join(root, 'site/public-host-mode.js')));
assert.ok(fs.existsSync(path.join(root, 'site/demo-chrome.css')));
assert.ok(indexHtml.includes('demo-chrome.css'));
assert.ok(indexHtml.includes('demo-polish.js'));
assert.ok(cloud.includes("querySelector('.desk-local')"));
const wiring = fs.readFileSync(path.join(root, 'site/demo-wiring.js'), 'utf8');
const polish = fs.readFileSync(path.join(root, 'site/demo-polish.js'), 'utf8');
const hostMode = fs.readFileSync(path.join(root, 'site/public-host-mode.js'), 'utf8');
assert.ok(wiring.includes('SOFT_HIDE'), 'demo wiring soft-hides thin nav');
assert.ok(wiring.includes("'indicators'"), 'demo wiring soft-hides chart indicators');
assert.ok(wiring.includes('demo-nav-soft-hidden'), 'demo wiring marks soft-hidden nav');
assert.ok(wiring.includes('MarketDeskPublicHost'), 'wiring shares public-host detection');
assert.ok(polish.includes('MarketDeskPublicHost'), 'polish shares public-host detection');
assert.ok(wiring.includes('PUBLIC PORTFOLIO'), 'wiring chrome says public portfolio');
assert.ok(polish.includes('PUBLIC PORTFOLIO'), 'polish chrome says public portfolio');
assert.ok(cloud.includes('PUBLIC PORTFOLIO'), 'cloud-host chrome says public portfolio');
assert.ok(cloud.includes('DEMO DATA'), 'status stays honestly labelled DEMO DATA on snapshot fallback');
assert.ok(cloud.includes('tryLiveQuoteApi'), 'public host prefers serverless /api/quotes when available');
assert.ok(cloud.includes('LIVE QUOTES (CACHED)'), 'live proxy upgrades status pill honestly');
assert.ok(fs.existsSync(path.join(root, 'api/quotes.js')), 'Vercel /api/quotes handler present');
assert.ok(fs.existsSync(path.join(root, 'api/quote.js')), 'Vercel /api/quote handler present');
assert.ok(fs.existsSync(path.join(root, 'lib/quotes-api.js')), 'shared quotes helper present');
assert.ok(fs.readFileSync(path.join(root, 'site/desk.js'), 'utf8').includes('window.Desk='), 'desk assigns window.Desk to avoid TDZ race');
assert.ok(fs.readFileSync(path.join(root, 'site/app.js'), 'utf8').includes('BUNDLED DEMO OBSERVATIONS'), 'overview chart source honest on demo');
assert.ok(fs.readFileSync(path.join(root, 'site/app.js'), 'utf8').includes('hydrateDemoForecast'), 'forecast auto-hydrates on demo');
assert.ok(shim.includes('accountsIncomplete'), 'v3 screen marks incomplete dollar accounts on demo');
assert.ok(wiring.includes('assertDemoChrome'), 'demo wiring re-asserts DEMO DATA chrome');
assert.ok(fs.readFileSync(path.join(root, 'site/demo-chrome.css'), 'utf8').includes('demo-nav-soft-hidden'));
assert.ok(fs.readFileSync(path.join(root, 'site/demo-chrome.css'), 'utf8').includes('demo-mac-only'));
assert.ok(cloud.includes("dataset.demoMode = 'true'"));
assert.ok(cloud.includes('md-demo-workflow-seed-v2'), 'demo seeds portfolio/research once (v2)');
assert.ok(hostMode.includes('.tmp.now'), 'anonymous Vercel *.tmp.now hosts auto-enable demo mode');
assert.ok(hostMode.includes('.vercel.app'), 'production *.vercel.app hosts auto-enable without ?demo=1');
assert.ok(hostMode.includes("params.get('demo') === 'local'"), 'loopback ?demo=local stays supported');
assert.ok(cloud.includes('v3Calc'), 'cloud host uses precomputed demo portfolio calc');
assert.ok(cloud.includes('workspace?.v3') || cloud.includes('workspace.v3'), 'cloud host serves seeded V3 workspace');
assert.ok(fs.readFileSync(path.join(root, 'site/signal.js'), 'utf8').includes('SAMPLE DATA · NOT LIVE'));
assert.ok(fs.readFileSync(path.join(root, 'site/pro.js'), 'utf8').includes('DEMO / 01'));
assert.ok(fs.existsSync(path.join(root, 'site/stock-directory.json')));
const release = fs.readFileSync(path.join(root, 'site/release.js'), 'utf8');
assert.ok(release.includes("version = '6.8.0'"), 'release.js version');
assert.ok(!indexHtml.includes('Market Desk<span>4.3</span>'));
const showcase = fs.readFileSync(path.join(root, 'site/showcase61.js'), 'utf8');
assert.ok(showcase.includes('md-guided-demo-seen'));
assert.ok(showcase.includes('MarketDeskShowcase'), 'showcase exposes beginGuidedDemo for soft CTA');
assert.ok(!showcase.includes('openSettingsForDemo'), 'no auto-hijack to Settings on first visit');
assert.ok(showcase.includes('Withheld on bundled sample'), 'pre-seeded tester task sample');
assert.ok(wiring.includes('firstRunCta'), 'demo wiring mounts soft first-run CTA');
assert.ok(wiring.includes('demo-first-run-cta'), 'soft CTA element id');
assert.ok(fs.readFileSync(path.join(root, 'site/demo-chrome.css'), 'utf8').includes('demo-first-run-cta'));
assert.ok(fs.existsSync(path.join(root, 'tools/export-demo-snapshot.py')));
assert.ok(
  fs.readFileSync(path.join(root, 'tools/export-demo-snapshot.py'), 'utf8').includes('v3Calc'),
  'export script builds practice portfolio calc'
);
assert.ok(
  fs.readFileSync(path.join(root, 'site/view-loader.js'), 'utf8').includes('/projects32.js'),
  'research lazy bundle loads projects32'
);
require(path.join(__dirname, 'test_public_host_mode.cjs'));
console.log(
  `Public demo bundle OK · v${snapshot.version} · ${snapshot.heatmap.rows.length} directory rows · ${(fs.statSync(path.join(root, 'site/demo/snapshot.json')).size / 1024).toFixed(0)} KB · ${snapshot.workspace.v3Calc.portfolio.holdings.length} demo holdings`
);