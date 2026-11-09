const assert=require('assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const els=new Map();const document={readyState:'loading',addEventListener(){},getElementById(id){if(!els.has(id))els.set(id,{textContent:'',innerHTML:'',classList:{add(){},remove(){}}});return els.get(id)}};
const ctx={document,console,URL,Date,Map,Set,JSON,Math,Number,String,Object,Array,Promise,setTimeout,clearTimeout};vm.createContext(ctx);
for(const name of ['app.js','tape.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/'+name),'utf8'),ctx);
const run=code=>vm.runInContext(code,ctx);
assert(run("DEFAULT_STOCKS.includes('TTWO')"));
for(const q of ['TTWO','Take Two','Take-Two Interactive','Rockstar','Rockstar Games','GTA VI','GTA 6','Grand Theft Auto VI']){
 assert.equal(run(`localStockMatches(${JSON.stringify(q)})[0].symbol`),'TTWO');
 assert.equal(run(`tapeSuggestionMatches(${JSON.stringify(q)})[0].sym`),'TTWO');
}
assert.equal(run("localStockMatches('No Such Brand ABCDEF').length"),0);
run("E.watch=['AAPL'];E.configured=false");
assert.equal(run("localStockMatches('Rockstar')[0].type"),'Listed parent of Rockstar Games · Nasdaq · USD');
assert.equal(run("JSON.stringify(E.watch)"),'["AAPL"]');
assert(!run("JSON.stringify(localStockMatches('GTA VI'))").includes('"price"'));
(async()=>{await run("searchStocks('Rockstar')");const s=els.get('search-results').innerHTML;assert(s.includes('TTWO'));assert(s.includes('Take-Two Interactive'));assert(s.includes('Listed parent of Rockstar'));assert(s.includes('data-add="TTWO"'));assert(!s.includes('data-add="ROCKSTAR"'));assert.equal(run('JSON.stringify(E.watch)'),'["AAPL"]');console.log('Stock catalogue: Take-Two aliases, offline search, parent label and saved-watchlist preservation PASS');})();
