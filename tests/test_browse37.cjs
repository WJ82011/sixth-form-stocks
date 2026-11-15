const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',classList:{add(){},remove(){},toggle(){}}});return nodes.get(id)};
const context={window:{},document:{readyState:'loading',addEventListener(){},getElementById:id=>id==='home43-chart'?null:node(id)},console,URL,Date,Math,Map,Set,JSON,Object,Number,String,Array,Promise};vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/app.js'),'utf8'),context);const run=s=>vm.runInContext(s,context);
const directory=JSON.parse(fs.readFileSync(path.join(__dirname,'../site/stock-directory.json'),'utf8'));
run(`applyStockDirectory(${JSON.stringify(directory)})`);
run("E.watch=STOCK_DIRECTORY.slice(0,60).map(x=>x.symbol);E.selected=E.watch[0];globalThis.originalWatch=JSON.stringify(E.watch);globalThis.visits=[];renderPickers=()=>{};refreshWatchFreshness=()=>{};changeView=v=>visits.push(v);setTimeout=()=>{};drawChart=()=>{};renderOverview=()=>{};loadChart=()=>{};openStock('WING')");
assert.equal(run('E.selected'),'WING');assert.equal(run('E.watch.length'),60);assert(!run("E.watch.includes('WING')"));assert.equal(run('JSON.stringify(E.watch)'),run('originalWatch'));assert.equal(run('visits[0]'),'overview');assert(run("companyChoices().includes('WING')"));assert.equal(run('companyChoices().length'),316);assert.equal(run('browseSymbols().length'),60);assert.equal(run('browseSymbols()[0]'),'WING');
run("openStock('<script>')");assert.equal(run('E.selected'),'WING');

run("E.view='overview';globalThis.tapeSelectedSymbol=()=>E.watch.at(-1)");
assert(run("desiredSubscriptions().has('WING')"),'The chart temporarily receives live trades for the open company');
assert(run('desiredSubscriptions().has(E.watch.at(-1))'),'The selected tape symbol retains priority');
assert.equal(run('desiredSubscriptions().size'),30);
run("E.view='home'");assert(!run("desiredSubscriptions().has('WING')"),'Leaving the chart releases the temporary stream slot');
assert.equal(run('JSON.stringify(E.watch)'),run('originalWatch'));
