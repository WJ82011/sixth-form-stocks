// Offline UI state tests with a minimal DOM fixture. No mock prices are included in app release.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const dirname=path.resolve(__dirname,'../site'),elements=new Map();
const canvasContext=()=>({setTransform(){},clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},fillText(){},fillRect(){},fill(){},save(){},restore(){},closePath(){},arc(){},setLineDash(){},createLinearGradient(){return {addColorStop(){}}}});
const cls=()=>{let set=new Set();return {add(k){set.add(k)},remove(k){set.delete(k)},toggle(k,force){if(force===true)set.add(k);else if(force===false)set.delete(k);else set.has(k)?set.delete(k):set.add(k);return set.has(k)},contains(k){return set.has(k)}}};
function dom(id){if(!elements.has(id))elements.set(id,{id,value:'',textContent:'',innerHTML:'',style:{},className:'',width:0,height:0,classList:cls(),events:{},setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]},getAttribute(k){return this[k]},addEventListener(k,cb){this.events[k]=cb},querySelectorAll(){return []},querySelector(){return dom(id+'-nested')},getBoundingClientRect(){return id==='tape-canvas'?{width:1024,height:380,left:0}:{width:100,height:100}},getContext(){return canvasContext()},blur(){},setPointerCapture(){}});return elements.get(id)}
const context={Date,Math,Number,JSON,Object,Array,Set,Map,RegExp,String,Promise,Intl,console,
 window:{devicePixelRatio:2,addEventListener(){},WebSocket:{OPEN:1}},
 document:{readyState:'loading',body:dom('body'),getElementById:dom,addEventListener(){},querySelectorAll(){return []}},
 localStorage:{getItem(){return null},setItem(){}},
 requestAnimationFrame(fn){fn();return 1},setTimeout(){return 1},clearTimeout(){},setInterval(){return 2},clearInterval(){},URL,Blob};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(dirname,'market-hours.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(dirname,'app.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(dirname,'tape.js'),'utf8'),context);
vm.runInContext(`E.watch=['AAPL','NVDA'];E.configured=false;E.view='tape';`,context);
vm.runInContext('tapeSetup();tapeRender();',context);
assert.equal(dom('tape-metric-count').textContent,'0');
assert.equal(dom('tape-symbol-title').textContent,'AAPL');
assert(dom('tape-shortcuts').innerHTML.includes('data-tape-symbol="AAPL"'));
assert(dom('tape-shortcuts').innerHTML.includes('data-tape-symbol="NVDA"'));
assert(dom('tape-shortcuts').innerHTML.includes('tape-chip-badges')); // Labels vary by exchange session
assert(dom('tape-symbol-list').innerHTML.includes('tape-session-badge'));
vm.runInContext(`tapeQuickStep(1)`,context);
assert.equal(vm.runInContext('T.symbol',context),'NVDA');
vm.runInContext(`tapeQuickStep(-1)`,context);
assert.equal(vm.runInContext('T.symbol',context),'AAPL');
assert(dom('tape-market-status').textContent.includes('MARKET')||dom('tape-market-status').textContent.includes('HOURS')||dom('tape-market-status').textContent.includes('PRE-')||dom('tape-market-status').textContent.includes('AFTER')); 
assert(dom('tape-chart-no-data').textContent.includes('No confirmed trades'));
const t=Date.now();
vm.runInContext(`T.events=[{t:${t-20000},p:110,v:100,receivedAt:${t-19000}},{t:${t-10000},p:111,v:200,receivedAt:${t-9900}}];tapeRender();`,context);
assert.equal(dom('tape-metric-count').textContent,'2');
assert.equal(dom('tape-metric-volume').textContent,'300');
assert(dom('tape-metric-vwap').textContent.includes('110.67'));
assert(dom('tape-metric-move').textContent.includes('0.91%'));
assert(dom('tape-trades-body').innerHTML.includes('TRADE'));
vm.runInContext('tapeTogglePause()',context);assert.equal(dom('tape-pause')['aria-pressed'],'true');
vm.runInContext('tapeTogglePause()',context);assert.equal(dom('tape-pause')['aria-pressed'],'false');
vm.runInContext('tapeExpand(true)',context);assert(dom('tape-chart-panel').classList.contains('tape-expanded'));
vm.runInContext('tapeEscape()',context);assert(!dom('tape-chart-panel').classList.contains('tape-expanded'));
vm.runInContext(`tapeSetRange('5m')`,context);assert.equal(vm.runInContext('T.range',context),'5m');
console.log('Live Tape DOM fixture: 17 interactive, chart, market status and switching assertions passed');

vm.runInContext(`T.range='1h';T.follow=true;T.events=[{t:${t-20000},p:110,v:100,id:1},{t:${t-10000},p:112,v:200,id:2},{t:${t-10000},p:109,v:30,id:3}];`,context);
const candle=vm.runInContext('JSON.stringify(tapeCandles(T.events,300000))',context);
const bars=JSON.parse(candle);
assert.equal(bars.reduce((sum,b)=>sum+b.size,0),330);
assert.equal(bars.at(-1).close,109);
assert.equal(bars.at(-1).low,109);
vm.runInContext('tapeTogglePause();const frozenCount=tapeVisible().length;T.events.push({t:nowMs()-1,p:120,v:80});',context);
assert.equal(vm.runInContext('tapeVisible().length===frozenCount',context),true);
vm.runInContext('tapeTogglePause();T.minSize=150;tapeRenderTrades(tapeVisible());',context);
assert.equal(dom('tape-record-count').textContent,'1');
assert.equal(vm.runInContext("tapeCanOpen('TTWO') && !E.watch.includes('TTWO')",context),true);
