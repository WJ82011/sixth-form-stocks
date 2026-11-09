const assert=require('node:assert/strict'),T=require('../site/truth36.js');const now=Date.parse('2026-11-06T16:00:00Z');const old={time:now-10000,price:96,previous:100,changePct:-4},r={time:now,price:94.87,previous:100,changePct:-5.13};assert(T.event(old,r,now));assert(!T.event(null,r,now));assert(!T.event(old,{...r,time:now-300000},now));assert(!T.event(old,{...r,time:old.time},now));assert(!T.event(old,{...r,previous:101},now));assert(!T.event(r,{...r,time:now+1000},now+1000));

assert(!T.event(old,{...r,changePct:-8},now),'inconsistent return rejected');
assert(!T.event(old,{...r,time:now+1},now),'future quote rejected');
assert(!T.event({...old,time:now-300000},r,now),'stale baseline rejected');
assert(!T.event({...old,currency:'GBP'},{...r,currency:'USD'},now),'currency changes rejected');
const n={key:'a',datetime:(now-10000)/1000,fetchedAt:now-5000};
assert(T.headline(n,now-20000,now,new Set()));
assert(!T.headline(n,now-20000,now,new Set(['a'])),'no replay');
assert(!T.headline(n,now-1000,now,new Set()),'published before enabling');
assert(!T.headline({...n,fetchedAt:now-30000},now-20000,now,new Set()),'old retrieval');
assert(!T.headline({...n,datetime:(now+1000)/1000},now-20000,now,new Set()),'future headline');
assert(!T.headline({...n,datetime:(now-700000)/1000},now-800000,now,new Set()),'expired headline');
