/* Unit tests: public portfolio mode without requiring ?demo=1 on Vercel hosts. */
const assert = require('node:assert/strict');
const path = require('node:path');

const mode = require(path.join(__dirname, '..', 'site', 'public-host-mode.js'));

function check(loc, expectDemo, label) {
  const got = mode.resolve(loc);
  assert.equal(got.demoMode, expectDemo, `${label} → demoMode=${got.demoMode} (expected ${expectDemo})`);
}

// Production / preview hosts — bare path, no query.
check({ hostname: 'sixth-form-stocks.vercel.app', port: '', search: '' }, true, 'production vercel.app');
check({ hostname: 'sixth-form-stocks-git-main-team.vercel.app', port: '', search: '' }, true, 'preview vercel.app');
check({ hostname: 'agile-aspen-kpbkd82.tmp.now', port: '', search: '' }, true, 'anonymous tmp.now');
check({ hostname: 'legacy-demo.now.sh', port: '', search: '' }, true, 'legacy now.sh');
check({ hostname: 'www.sixth-form-stocks.example', port: '', search: '' }, true, 'custom host with project name');

// ?demo=local must NOT disable public hosts (admissions URL stays snapshot-backed).
check(
  { hostname: 'sixth-form-stocks.vercel.app', port: '', search: '?demo=local' },
  true,
  'production ignores ?demo=local'
);
check({ hostname: 'foo.tmp.now', port: '', search: '?demo=local' }, true, 'tmp.now ignores ?demo=local');

// Force-on still works for local static servers.
check({ hostname: '127.0.0.1', port: '8777', search: '?demo=1' }, true, 'static local ?demo=1');
check({ hostname: 'localhost', port: '8777', search: '?demo=cloud' }, true, 'static local ?demo=cloud');

// Mac server.py path stays live (no snapshot intercept).
check({ hostname: '127.0.0.1', port: '8765', search: '' }, false, 'Mac server.py default');
check({ hostname: 'localhost', port: '8765', search: '?demo=1' }, false, 'Mac server.py ignores ?demo=1');

// Local static without force-on stays Mac-shaped shell.
check({ hostname: '127.0.0.1', port: '8777', search: '' }, false, 'local static bare /');
check({ hostname: 'localhost', port: '8777', search: '?demo=local' }, false, 'local ?demo=local forces off');

assert.equal(mode.isPublicPortfolioHost('sixth-form-stocks.vercel.app'), true);
assert.equal(mode.isPublicPortfolioHost('localhost'), false);
assert.equal(mode.isLoopbackHost('127.0.0.1'), true);

console.log('PASS public host mode · auto-enable without ?demo=1 on vercel.app/tmp.now');
