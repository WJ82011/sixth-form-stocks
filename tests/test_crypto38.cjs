const assert=require('node:assert/strict');
const {acceptTick}=require('../site/crypto38.js');
const now=Date.parse('2026-11-08T16:00:00Z');
const tick={type:'ticker',product_id:'BTC-USD',price:'101.5',time:'2026-11-08T15:59:59Z'};
assert.deepEqual(acceptTick(tick,'BTC-USD',now),{price:101.5,time:now-1000,kind:'stream'});
assert.equal(acceptTick(tick,'ETH-USD',now),null);
for(const invalid of [{price:true},{price:'NaN'},{price:'0'},{time:'2026-11-08T16:01:00Z'},{time:'2026-11-08T15:58:59Z'}]){
  assert.equal(acceptTick({...tick,...invalid},'BTC-USD',now),null);
}
