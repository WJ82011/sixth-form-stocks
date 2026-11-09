/* Synthetic browser/storage/transport fixtures; no actual browser data. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',value:'',classList:{toggle(){},add(){},remove(){}}});return nodes.get(id)};
const storage=new Map([['md-reborn-notes','["original"]'],['unrelated','keep']]);let failAt=0,writes=0;
const localStorage={getItem:k=>storage.get(k)??null,setItem(k,v){writes++;if(writes===failAt)throw Error('Synthetic quota');storage.set(k,v)},removeItem:k=>storage.delete(k)};
const ctx=vm.createContext({document:{readyState:'loading',getElementById:node,addEventListener(){},querySelectorAll(){return []}},localStorage,URL,console,ChartResearch:require('../site/chart-research.js')});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/app.js'),'utf8'),ctx);ctx.renderOverview=()=>{};ctx.drawChart=()=>{};
const run=s=>vm.runInContext(s,ctx);ctx.originalApi=run('api');
globalThis.failureUiTestResult=(async()=>{
 for(let i=1;i<=4;i++){
  storage.clear();storage.set('md-reborn-notes','["original"]');storage.set('unrelated','keep');failAt=i;writes=0;
  assert.throws(()=>run("commitBrowserRecords({'md-reborn-notes':['new'],'md-reborn-watch':['AAPL'],'md-reborn-v3':{},'md-reborn-reports':[]})"),/previous records were restored/);
  assert.equal(storage.get('md-reborn-notes'),'["original"]');assert.equal(storage.get('unrelated'),'keep');assert.equal(storage.size,2);
 }
 failAt=0;writes=0;run("commitBrowserRecords({'md-reborn-notes':['new'],'md-reborn-watch':['AAPL']})");assert.equal(storage.get('md-reborn-notes'),'["new"]');
 // An older chart response arrives after a new company was selected.
 let release;ctx.api=async url=>{if(url.includes('symbol=AAPL'))return new Promise(r=>{release=r});return {points:[{t:Date.now()-1000,p:200,source:'finnhub_quote'}]}};
 run("E.selected='AAPL';E.range='1D';E.forecastEnabled=false");const old=run('loadChart()');run("E.selected='MSFT'");await run('loadChart()');release({points:[{t:Date.now()-1000,p:10,source:'finnhub_quote'}]});await old;
 assert.equal(run('E.chartPoints.at(-1).p'),200);assert.equal(run('E.selected'),'MSFT');
 // Invalid JSON and HTTP failure must not be treated as successful source data.
 ctx.fetch=async()=>({ok:true,json:async()=>{throw Error('Synthetic truncated body')}});await assert.rejects(run("originalApi('/api/history')"),/Invalid response/);
 ctx.fetch=async()=>({ok:false,status:503,json:async()=>({error:'Synthetic unavailable'})});await assert.rejects(run("originalApi('/api/history')"),/Synthetic unavailable/);
 console.log('Quota rollback, unrelated storage, stale chart response and failed transport PASS');
})();
