const assert=require('node:assert/strict');const A=require('../site/analyst34.js');
assert.equal(A.number(''),null,'Blank inputs must not become assumed zero');
assert.equal(A.number('0'),0);assert.equal(A.esc('<script>"x"&'), '&lt;script&gt;&quot;x&quot;&amp;');
const a=A.reference(),b=A.reference();assert.deepEqual(a.map(x=>x.name),['Downside','Base','Upside']);
a[0].product.enabled=true;assert.equal(b[0].product.enabled,false,'Independent cases and calls');
assert(a.every(x=>x.rationale.includes('no claim')));assert(b.every(x=>x.valuation.method==='none'));

const source=require('node:fs').readFileSync(require('node:path').join(__dirname,'../site/analyst34.js'),'utf8');assert(!source.includes('data-action='),'Analyst record buttons must not trigger the retained app navigation delegate');
