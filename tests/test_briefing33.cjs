const assert=require('node:assert/strict'),B=require('../site/briefing33.js');
assert.equal(B.same(['TTWO','AAPL'],['AAPL','TTWO']),true);assert.equal(B.same(['AAPL'],['TTWO']),false);
assert.equal(B.count([{newToBriefing:true},{newToBriefing:false}],true),1);assert.equal(B.count([{newToBriefing:false}],false),1);assert.equal(B.esc('<script>'), '&lt;script&gt;');
const review=Date.parse('2026-11-06T12:00:00Z');assert.match(B.timing({date:'2026-11-06'},'filings',review),/filing time not supplied/);assert.match(B.timing({date:'2026-11-05'},'filings',review),/Earlier filing/);assert.match(B.timing({datetime:review/1000-100},'news',review),/Earlier article/);assert.match(B.timing({datetime:review/1000+100},'news',review),/Published after/);assert.equal(B.timing({},'news',null),'');assert.match(B.notes.revised,/withheld/);assert.match(B.notes.currency,/withheld/);
console.log('Briefing: scope matching, first-review counts, source escaping and date-only filing ordering PASS');
