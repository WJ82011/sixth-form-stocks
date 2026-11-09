/* UI fixtures are synthetic, never provider data. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const nodes=new Map(),events={},calls=[],pending=[];
function node(id){if(!nodes.has(id))nodes.set(id,{id,value:id==='fh-period'?'annual':id==='company-select'||id==='compare-a'?'AAPL':id==='compare-b'?'MSFT':'',innerHTML:'',textContent:'',disabled:false,addEventListener(k,f){(events[id]??={})[k]=f}});return nodes.get(id)}
const document={getElementById:node,addEventListener(k,f){if(k==='DOMContentLoaded')f()}};
const context={document,E:{selected:'AAPL'},module:{exports:{}},fetch(url,options){calls.push({url,options});return new Promise(resolve=>pending.push(data=>resolve({ok:true,json:async()=>data})))},URL,Intl,console,Blob,setTimeout};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/financial-health.js'),'utf8'),context);const ui=context.module.exports;
function report(symbol,name='Synthetic <script>bad</script>'){
 const f={value:0,url:'https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/0000320193-26-000001-index.html',form:'10-K',filed:'2026-02-01',tag:'NetIncomeLoss',start:'2025-01-01',end:'2025-12-31'};
 return {status:'ok',symbol,name,fetchedAt:1,annual:[{start:'2025-01-01',end:'2025-12-31',durationDays:365,type:'annual',metrics:{profit:f,revenue:{...f,value:1000}},longTermDebt:null,netMarginPct:0,revenueGrowthPct:0,warnings:[]}],quarterly:[],notice:'Synthetic fixture'};
}
globalThis.financialHealthTestResult=(async()=>{
 assert.equal(calls.length,0,'Mounting the UI must not contact providers');
 const first=ui.load('AAPL'),second=ui.load('MSFT');pending[1](report('MSFT'));await second;pending[0](report('AAPL'));await first;
 assert(node('fh-output').innerHTML.includes('MSFT'));assert(!node('fh-output').innerHTML.includes('AAPL /'),'Late company response cannot overwrite current selection');
 assert(node('fh-output').innerHTML.includes('&lt;script&gt;'));assert(!node('fh-output').innerHTML.includes('<script>'));assert(node('fh-output').innerHTML.includes('0.0%'),'Real zero margin must remain zero');assert(node('fh-output').innerHTML.includes('Not available'),'Missing debt must not be shown as zero');
 assert.equal(ui.source({url:'javascript:alert(1)'}),'');assert.equal(ui.source({url:'https://www.sec.gov.evil.test/Archives/edgar/data/test'}),'');assert.equal(ui.source({url:'https://user:secret@www.sec.gov/Archives/edgar/data/test'}),'','Credential URLs must not become source links');
 const before=calls.length;node('fh-period').value='quarterly';events['fh-period'].change();assert.equal(calls.length,before);assert(node('fh-output').innerHTML.includes('No supported directly reported quarterly figures'));
 const c=ui.compare(false);assert(calls.at(-1).url.includes('/api/financials/compare'));node('compare-b').value='TTWO';events['compare-b'].change();pending.at(-1)({aligned:true,rows:[],basis:'STALE',notice:'old'});await c;assert(!node('fh-compare-output').innerHTML.includes('STALE'),'Changed company choices invalidate comparison response');
 assert(calls.every(x=>!x.url.includes('sec.gov')),'Browser only talks to the local server');
 console.log('Financial health UI: escaped values, real zero/missing, source allowlist, local-only reads and company/comparison races PASS');return true;
})();
