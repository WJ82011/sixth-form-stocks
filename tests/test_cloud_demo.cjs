/* Snapshot + shim wiring checks for the public Vercel demo (no network). */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'site/demo/snapshot.json'), 'utf8'));
assert.equal(snapshot.version, 1);
assert.equal(snapshot.heatmap.rows.length, 221, 'directory heatmap rows');
const coloured = snapshot.heatmap.rows.filter((r) => Number.isFinite(r.change));
assert.ok(coloured.length >= 200, 'most tiles should have a period change');
assert.ok(snapshot.dailyBars.AAPL.c.length > 100, 'AAPL daily chart series');
assert.ok(fs.readFileSync(path.join(root, 'site/cloud-host.js'), 'utf8').includes('/api/v3/heatmap'));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('cloud-host.js'));
assert.ok(fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('release.js'));
const release = fs.readFileSync(path.join(root, 'site/release.js'), 'utf8');
assert.ok(release.includes("version = '6.8.0'"), 'release.js version');
assert.ok(!fs.readFileSync(path.join(root, 'site/index.html'), 'utf8').includes('Market Desk<span>4.3</span>'));
assert.ok(fs.readFileSync(path.join(root, 'site/showcase61.js'), 'utf8').includes('md-guided-demo-seen'));
assert.ok(fs.existsSync(path.join(root, 'tools/export-demo-snapshot.py')));
console.log('Public demo bundle: snapshot, shim hook and export script OK');