const assert=require('node:assert/strict');
const C=require('../site/chart-research.js');
const day=86400000, now=Date.UTC(2026,10,2,15);
const gen=(n,step=day)=>Array.from({length:n},(_,i)=>({t:now-2*day-(n-i-1)*step,p:100+i*.15+Math.sin(i/4)}));
const sample=gen(150);
const base=C.model(sample,[],now,20);
assert.equal(base.rows.length,21);
assert.equal(base.anchor.p,sample.at(-1).p);
assert.equal(base.rows[0].price,sample.at(-1).p);
assert.equal(base.rows[0].low,base.rows[0].price);
assert.equal(base.rows[0].high,base.rows[0].price);
assert.equal(base.method,'damped-multi-horizon');
assert.equal(C.model(sample.slice(-44),[],now,20),null);
assert.equal(C.model(gen(90,60000),[],now,20),null,'Intraday ticks must not impersonate daily closes');
assert.equal(C.model(sample.map(x=>({...x,t:x.t-50*day})),[],now,20),null,'Outdated observations cannot generate current forecast');
assert.equal(C.coverage(gen(20),now-7*day,now).count,6);
const dedup=C.normaliseDaily([...sample,{...sample[0],p:101},{t:now-4*day,p:-20},{t:now+30*day,p:50}],now);
assert.equal(dedup.length,150);
const headlines=[{datetime:Math.floor((now-day)/1000),headline:'Company raises guidance after strong demand'},
 {datetime:Math.floor((now-day)/1000),headline:'Company raises guidance after strong demand'},
 {datetime:Math.floor((now-2*day)/1000),headline:'Company faces recall and cuts guidance'},
 {datetime:Math.floor((now-20*day)/1000),headline:'Company beats estimates'}];
const sentiment=C.headlineSignal(headlines,now);
assert.equal(sentiment.used,2,'Duplicate and stale headlines excluded');
const positive=C.model(sample,[headlines[0]],now,20),negative=C.model(sample,[headlines[2]],now,20);
assert.ok(positive.sentiment.score>negative.sentiment.score);
assert.equal(positive.newsContribution,0);
assert.equal(negative.newsContribution,0);
assert.deepEqual(positive.rows,negative.rows,'Unvalidated headline keywords must NEVER change the price projection');
assert.equal(C.headlineSignal([],now).used,0);

// The central path bends due to decaying multi-timescale trends, NOT a
// manufactured oscillation. When history has no trend, it remains flat.
const regime=Array.from({length:220},(_,i)=>({
 t:now-2*day-(219-i)*day,
 p:100*Math.exp(.0002*i+.003*Math.max(0,i-210))
}));
const curved=C.model(regime,[],now,60);
const firstSlope=Math.log(curved.rows[1].price/curved.rows[0].price);
const lastSlope=Math.log(curved.rows[60].price/curved.rows[59].price);
assert.ok(firstSlope>lastSlope+.00025,`Recent momentum should fade instead of tracing a straight line: ${firstSlope}, ${lastSlope}`);
assert.ok(curved.rows[1].price>curved.rows[0].price);
assert.ok(curved.rows[60].price>curved.rows[1].price);
assert.ok(curved.rows.every(r=>r.low<=r.price&&r.high>=r.price),'Expected volatility fan must enclose forecast');
assert.equal(curved.rows[0].price,regime.at(-1).p,'Forecast must start at authentic last close');
const flat=C.model(Array.from({length:120},(_,i)=>({t:now-2*day-(119-i)*day,p:100})),[],now,60);
assert.ok(flat.rows.every(r=>r.price===100),'Truly flat history should NOT cause decorative future waves');
assert.ok(flat.rows[60].high>flat.rows[10].high,'Volatility band must widen with horizon');
const laterShock=regime.map((r,i)=>i>200?{...r,p:r.p*Math.exp((i%2?1:-1)*.05)}:r);
const shocked=C.model(laterShock,[],now,60);
assert.ok(shocked.sigma>curved.sigma,'Higher realised volatility must widen the fan');
assert.ok(shocked.rows[30].high/shocked.rows[30].low>curved.rows[30].high/curved.rows[30].low);
const down=C.model(regime.map((r,i)=>({...r,p:10000/r.p})),[],now,60);
assert.ok(down.rows[60].price<down.rows[0].price,'Falling observed trends should yield negative (not forced positive) scenarios');

const back=C.walkForward(sample);
assert.ok(back&&back.samples>=5&&Number.isFinite(back.modelMAPE)&&Number.isFinite(back.baselineMAPE));
assert.equal(back.newsTested,false);
const back20=C.walkForward(gen(330),20);
assert.ok(back20&&back20.samples>=5&&back20.horizon===20,'20-session historical test must be available with enough observations');
assert.ok(back20.modelMAPE>=0&&back20.baselineMAPE>=0);
assert.equal(C.walkForward(sample.slice(-40)),null);

// Offline Mac chart gaps: never draw an invented price line/area across a
// period without observations. Long-range real daily closes stay independent.
const night=[{t:now-6*3600000,p:110},{t:now-5.8*3600000,p:111},
 {t:now-1*3600000,p:109},{t:now-.8*3600000,p:112}];
assert.deepEqual(C.chartSegments(night,'1D').map(x=>x.length),[1,1,1,1]);
assert.deepEqual(C.chartGaps(night,'1D'),night.slice(1).map((p,i)=>({from:night[i].t,to:p.t})));
assert.equal(C.chartSegments(night,'1M').length,1);
assert.deepEqual(C.chartSegments([], '1D'),[]);
console.log('Chart research v1.6.4: source gates, contextual news, curved trend, changing regimes, wide bands, 5/20-session historical backtests and sleep gaps: PASS');

assert.equal(C.chartSegments(night,'1H').length,4);

// A recurring observed regime yields chronological comparisons and a deterministic centre.
const recurring=Array.from({length:620},(_,i)=>({
 t:now-2*day-(619-i)*day,p:100*Math.exp(.0001*i+.035*Math.sin(i*2*Math.PI/40)+.012*Math.cos(i*2*Math.PI/10))
}));
const matched=C.model(recurring,[],now,20);
assert.equal(matched.method,'matched-path-blend');
assert.ok(matched.matches>=8);
assert.deepEqual(C.model(recurring,[],now,20).rows,matched.rows);
assert.deepEqual(C.model([...recurring,{t:now+3600000,p:999}],[],now,20).rows,matched.rows);
assert.equal(matched.rows[0].price,recurring.at(-1).p);
