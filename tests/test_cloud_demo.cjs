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
assert.ok(snapshot.tape.AAPL.events.length > 20, 'tape events');
assert.ok(snapshot.intelligence.TTWO.hour.count > 0, 'intelligence hour points');
assert.equal(snapshot.forecasts.TTWO.status, 'learned', 'TTWO shown forecast');
assert.equal(snapshot.forecasts.AMD.status, 'withheld', 'AMD withheld forecast');
assert.ok(Object.keys(snapshot.workspace.names).length >= 200, 'workspace name index');

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
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('cloud-host.js'));
const cloud = fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8');
assert.ok(!cloud.includes('XMLHttpRequest'), 'demo snapshot must not use sync XHR on the main thread');
assert.ok(cloud.includes('whenSnapshotReady'), 'demo host exposes async snapshot readiness');
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('release.js'));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('view-loader.js'));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('demo-wiring.js'));
assert.ok(fs.existsSync(path.join(root, 'site/demo-wiring.js')));
assert.ok(fs.existsSync(path.join(root, 'site/demo-polish.js')));
assert.ok(fs.existsSync(path.join(root, 'site/demo-chrome.css')));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('demo-chrome.css'));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('demo-polish.js'));
assert.ok(fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8').includes("querySelector('.desk-local')"));
assert.ok(fs.existsSync(path.join(root, 'site/stock-directory.json')));
const release = fs.readFileSync(path.join(root, 'site/release.js'), 'utf8');
assert.ok(release.includes("version = '6.8.0'"), 'release.js version');
assert.ok(!fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('Market Desk<span>4.3</span>'));
assert.ok(fs.readFileSync(path.join(root, 'site/showcase61.js'), 'utf8').includes('md-guided-demo-seen'));
assert.ok(fs.existsSync(path.join(root, 'tools/export-demo-snapshot.py')));
console.log(
  `Public demo bundle OK · v${snapshot.version} · ${snapshot.heatmap.rows.length} directory rows · ${(fs.statSync(path.join(root, 'site/demo/snapshot.json')).size / 1024).toFixed(0)} KB`
);