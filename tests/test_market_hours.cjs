// Independent UTC exchange calendar / daylight-saving tests; no network, no fake prices.
const assert=require('node:assert/strict');
const {marketSessionFor,usTicker}=require('../site/market-hours.js');
const test=(s,iso,state)=>assert.equal(marketSessionFor(s,new Date(iso)).state,state,`${s} ${iso} expected ${state}`);
test('AAPL','2026-11-02T14:29:00Z','premarket'); // UK GMT / New York EST
test('AAPL','2026-11-02T14:30:00Z','open');
test('NVDA','2026-11-02T20:59:00Z','open');
test('NVDA','2026-11-02T21:00:00Z','afterhours');
test('AAPL','2026-06-01T13:30:00Z','open'); // NY daylight savings
// Day after UK DST switches but US DST has not yet ended: NY remains EDT.
test('AAPL','2026-10-30T13:30:00Z','open');
test('MSFT','2026-07-03T14:00:00Z','closed'); // Independence holiday observed
test('AAPL','2026-11-26T15:30:00Z','closed'); // Thanksgiving
test('AAPL','2026-11-27T17:59:00Z','open'); // NYSE 1pm early close
test('AAPL','2026-11-27T18:00:00Z','afterhours');
test('AAPL','2026-12-24T17:30:00Z','open');
test('AAPL','2026-12-24T18:00:00Z','afterhours');
test('AAPL','2027-12-24T15:00:00Z','closed');
test('AAPL','2028-07-03T16:59:00Z','open');
test('AAPL','2028-07-03T17:00:00Z','afterhours');
test('AAPL','2026-11-07T15:00:00Z','closed'); // Saturday
test('TSLA','2029-03-02T16:00:00Z','unknown'); // stale calendar: don't guess
test('VOD.L','2026-11-02T15:00:00Z','unknown');
test('7203.T','2026-11-02T15:00:00Z','unknown');
test('BINANCE:BTCUSDT','2026-11-02T15:00:00Z','unknown');
assert.equal(usTicker('BRK.B'),true);
assert.equal(usTicker('AAPL'),true);
assert.equal(usTicker('SHOP.TO'),false);
assert.match(marketSessionFor('NVDA',new Date('2026-11-02T14:30:00Z')).detail,/Scheduled regular US equity session/);
console.log('Market hours: 24 calendar, DST, holiday, venue and early-close checks passed');
