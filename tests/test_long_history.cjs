/* Synthetic test fixtures only; never shipped as market data. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../site/app.js'),'utf8'),C=require('../site/chart-research.js'),now=Date.now(),DAY=86400000;
const nodes=new Map(),el=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',classList:{toggle(){},add(){},remove(){}}});return nodes.get(id)};
const ctx=vm.createContext({document:{getElementById:el,readyState:'loading',addEventListener(){},querySelectorAll(){return []}},console,URL,ChartResearch:C});
vm.runInContext(src,ctx);ctx.$=el;ctx.drawChart=()=>{};ctx.renderOverview=()=>{};
const run=s=>vm.runInContext(s,ctx);
globalThis.longHistoryTestResult=(async()=>{
 assert.equal(run("timeWindow('5Y')"),1826*DAY);assert.equal(run("timeWindow('10Y')"),3653*DAY);
 const series=Array.from({length:2000},(_,i)=>({t:now-(2000-i)*DAY,p:100+i*.02}));
 assert.equal(C.normaliseDaily(series,now).length,2000,'longer data survives normalisation');
 assert.equal(C.chartSegments(series,'5Y').length,1,'daily sessions remain connected');
 assert.equal(C.chartSegments([{t:now-20*DAY,p:1},{t:now,p:2}],'5Y').length,2,'large gaps are not bridged');
 run("E.configured=false;E.massiveConfigured=false;E.forecastEnabled=true");
 const calls=[];ctx.api=async p=>{calls.push(p);if(p.startsWith('/api/imported-history'))return {status:'ok',provider:'imported',source:'Test fixture',split_adjusted:true,points:series};if(p.startsWith('/api/history'))return {points:[{t:now-1000,p:999}]};throw Error('Unwanted network call')};
 const hist=await run("historicalFor('AAPL','5Y')");assert.equal(hist.provider,'imported');assert.equal(hist.points.length,2000);assert.equal(calls.length,1);
 await run("historicalFor('AAPL','5Y')");assert.equal(calls.length,1,'repeat range uses local cache');
 run("E.selected='AAPL';E.range='5Y'");await run('loadChart()');assert.equal(run('E.chartPoints.at(-1).p'),series.at(-1).p,'intraday price is not spliced into imported line');assert.equal(run('E.chartForecast'),null);assert.match(el('chart-forecast-legend').textContent,/not been independently verified/);assert.match(el('chart-data-coverage').textContent,/Imported/);
 run("E.range='10Y'");await run('loadChart()');assert.match(el('chart-data-coverage').textContent,/Partial 10Y/,'coverage warning visible outside disclosure');
 run('E.candles.clear();E.configured=true');calls.length=0;
 ctx.api=async p=>{calls.push(p);if(p.startsWith('/api/imported-history'))return {status:'no_data'};return {status:'no_data',provider:'massive'}};
 await run("historicalFor('AAPL','5Y')");const req=new URL('http://local'+calls.find(p=>p.startsWith('/api/candles')));assert.ok(Number(req.searchParams.get('to'))-Number(req.searchParams.get('from'))>5*365*86400);
 const chartBefore=run("E.candles.get('AAPL')");calls.length=0;await run("historicalFor('AAPL','1Y',false)");assert.equal(run("E.candles.get('AAPL')"),chartBefore,'provider research does not replace the selected chart source');assert.ok(!calls.some(p=>p.startsWith('/api/imported-history')),'forecast provider path never consumes imported files');
 console.log('Long-range chart, source isolation, coverage and cache checks PASS');
})();
