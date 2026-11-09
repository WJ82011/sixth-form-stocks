/* Synthetic project/chart fixtures only. No provider calls or user storage. */
const assert=require('node:assert/strict'),P=require('../site/projects32.js');
assert.deepEqual(P.splitSymbols('aapl, TTWO\nAAPL   msft'),['AAPL','TTWO','MSFT']);assert.deepEqual(P.splitSymbols(''),[]);assert.ok(P.splitSymbols('bad/symbol').includes('BAD/SYMBOL'),'invalid tokens must reach validation, not silently disappear');
assert.equal(P.escape('<script>"&'), '&lt;script&gt;&quot;&amp;');
const points=Array.from({length:1000},(_,i)=>({t:1735800000000+i*60000,p:10+i/1000,source:'synthetic_test_only'}));const E={selected:'AAA',range:'1D',chartSource:'Synthetic fixture · not market data',chartPoints:points,chartForecast:{rows:[{price:999}]}};
const chart=P.capture(E,'AAA','USD');assert.equal(chart.points.length,600);assert.equal(chart.displayedCount,1000);assert.equal(chart.points[0].t,points[400].t);assert.ok(!JSON.stringify(chart).includes('999}'));points.at(-1).p=1;assert.notEqual(chart.points.at(-1).p,1,'snapshot is a copy, not a live reference');
assert.throws(()=>P.capture(E,'BBB'),/Open this project/);assert.throws(()=>P.capture({...E,chartPoints:[]},'AAA'),/No recorded/);
const gap={range:'1D',points:[{t:1735800000000,p:10},{t:1735800060000,p:11},{t:1735803600000,p:12}]};assert.equal((P.line(gap).match(/M/g)||[]).length,2);assert.equal((P.line({...gap,range:'1Y'}).match(/M/g)||[]).length,1);assert.ok(!P.line({...gap,points:[{t:1,p:10},{t:2,p:10}]}).includes('NaN'));
const project={title:'Synthetic research',symbol:'AAA',stage:'Exploring',updatedAt:'2025-01-01',question:'Check source',thesis:'Author view',risks:'Uncertainty',items:[{id:'c',kind:'chart',title:'Captured test',createdAt:'2025',body:'',chart},{id:'r',kind:'report',title:'Linked report',reportId:'missing',createdAt:'2025'}]};const md=P.markdown(project,[]);assert.match(md,/Linked report unavailable/);assert.match(md,/600 of 1000/);assert.match(md,/Author view/);assert.match(md,/not independently verified/);
const empty={symbol:'AAA',title:'',status:'Draft',checks:{}};assert.equal(P.reportIsDirty(empty),false);assert.equal(P.reportIsDirty({...empty,financial:'Unsaved figures'}),true);assert.equal(P.reportIsDirty({...empty,checks:{primary:true}}),true);const saved={...empty,title:'Saved',checks:{primary:true}};assert.equal(P.reportIsDirty(saved,saved),false);assert.equal(P.reportIsDirty({...saved,checks:{primary:false}},saved),true);
console.log('Projects: source escaping, watchlist parsing, frozen chart bounds/gaps, export and report draft protection PASS');
const fsForm=require('node:fs'),vmForm=require('node:vm'),pathForm=require('node:path');
{
 const text=fsForm.readFileSync(pathForm.join(__dirname,'../site/projects32.js'),'utf8'),start=text.indexOf(' async function submit(e){'),end=text.indexOf(' function bind()',start);let capturedSave=null,prevented=false,resets=0;
 // An input named "id" shadows HTMLFormElement.id in real browsers.
 const form={id:{name:'id',value:''},getAttribute:key=>key==='id'?'p32-list-form':null,reset:()=>resets++};
 const entries=[['id',''],['baseUpdatedAt',''],['name','Synthetic games list'],['symbols','TTWO, EA']];
 const ctxForm=vmForm.createContext({FormData:class{constructor(){}[Symbol.iterator](){return entries[Symbol.iterator]()}},current:()=>null,uid:()=>'test-list',ProjectMath:P,save:async(kind,payload)=>{capturedSave={kind,payload};return true},renderLists(){},listDirty:true,$:()=>({textContent:''}),status(){},Object,Number,Error});
 vmForm.runInContext(text.slice(start,end),ctxForm);ctxForm.testEvent={target:form,preventDefault:()=>prevented=true};
 globalThis.projectFormTestResult=(async()=>{await vmForm.runInContext('submit(testEvent)',ctxForm);assert.ok(prevented);assert.equal(capturedSave.kind,'watchlist.save');assert.equal(capturedSave.payload.watchlist.symbols.join(','),'TTWO,EA');assert.equal(resets,1);console.log('Named watchlist form ID shadowing regression PASS');})();
}
assert.match(P.markdown({...project,items:[{kind:'report',id:'r',title:'Wrong company link',reportId:'r1',createdAt:'2025'}]},[{id:'r1',symbol:'BBB',title:'Another company'}]),/Linked report unavailable/);
