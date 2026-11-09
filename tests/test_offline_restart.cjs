/* Synthetic fixtures exercise recovery after sleep; never used as market data. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const nodes=new Map(),el=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',classList:{toggle(){},add(){},remove(){}}});return nodes.get(id)};
const C=require('../site/chart-research.js'),now=Date.now(),DAY=86400000;
const ctx=vm.createContext({document:{getElementById:el,readyState:'loading',addEventListener(){},querySelectorAll(){return []}},console,URL,ChartResearch:C});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/app.js'),'utf8'),ctx);ctx.$=el;ctx.drawChart=()=>{};ctx.renderOverview=()=>{};
const run=s=>vm.runInContext(s,ctx);
globalThis.offlineRestartTestResult=(async()=>{
 const old=[{t:now-4*DAY-3600000,p:100,source:'finnhub_quote'},{t:now-4*DAY,p:101,source:'finnhub_quote'}];const calls=[];
 ctx.api=async p=>{calls.push(p);if(p.startsWith('/api/history'))return {points:p.endsWith('since=0')?old:[]};throw Error('No internet')};
 run("E.selected='AAPL';E.range='1D';E.forecastEnabled=false");await run('loadChart()');
 assert.equal(run('E.chartPoints.length'),2);assert.equal(run('E.chartPoints.at(-1).t'),old[1].t);assert.equal(run('E.chartDomain.to'),old[1].t);assert.match(el('overview-chart-note').textContent,/LAST SAVED SESSION/);assert.match(el('chart-data-coverage').textContent,/Last saved session/);assert.match(run('E.chartSource'),/NOT CURRENT/);
 ctx.api=async p=>p.startsWith('/api/history')?{points:[{t:now-1000,p:102,source:'finnhub_quote'}]}:Promise.reject(Error('Unexpected'));
 await run('loadChart()');assert.equal(run('E.chartPoints.at(-1).p'),102);assert.ok(run('E.chartDomain.to')>old[1].t);assert.ok(!run('E.chartSource').includes('LAST SAVED'));
 calls.length=0;run("E.configured=true;E.massiveConfigured=true;E.candles.clear()");
 ctx.api=async p=>{calls.push(p);if(p.startsWith('/api/imported-history'))return {status:'no_data'};if(p.startsWith('/api/saved-daily'))return {status:'ok',provider:'massive',cached:true,candles:{t:[Math.floor((now-3*DAY)/1000),Math.floor((now-2*DAY)/1000)],c:[100,101]}};throw Error('Internet unavailable')};
 const cached=await run("historicalFor('AAPL','1Y')");assert.equal(cached.points.length,2);assert.ok(!calls.some(p=>p.startsWith('/api/candles')),'opening a saved chart must not wait for internet');
 calls.length=0;const refreshed=await run("historicalFor('AAPL','1Y',true,true)");assert.equal(refreshed.points.length,2);assert.ok(calls.some(p=>p.startsWith('/api/candles')));assert.match(refreshed.refreshError,/Internet unavailable/);
 ctx.api=async p=>p.startsWith('/api/history')?{points:[]}:Promise.reject(Error('No internet'));
 run("E.range='1H';E.candles.clear()");await run('loadChart()');assert.equal(run('E.chartPoints.length'),0);assert.match(el('overview-chart-note').textContent,/No recorded prices/);
 console.log('Offline restart, genuine dates, current-session recovery, cached daily load and refresh fallback PASS');
})();
