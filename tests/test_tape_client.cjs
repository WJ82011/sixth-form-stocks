// Isolated live-frame and chart-state assertions — never contacts Finnhub.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const dirname=path.resolve(__dirname,'../site');
const el=()=>({textContent:'',className:'',style:{},classList:{add(){},remove(){},toggle(){},contains(){return false}},setAttribute(){},addEventListener(){},querySelectorAll(){return []},querySelector(){return el()},getClientRects(){return []}});
const dom=new Map();
const context={console,Date,Math,Number,JSON,Object,Array,Set,Map,RegExp,String,Promise,Intl,
  document:{readyState:'loading',getElementById(id){if(!dom.has(id))dom.set(id,el());return dom.get(id)},addEventListener(){},querySelectorAll(){return []}},
  window:{devicePixelRatio:1},
  localStorage:{getItem(){return null},setItem(){}},setTimeout(){return 3},clearTimeout(){},
  setInterval(){return 4},clearInterval(){},URL,Blob};
context.window.window=context.window;
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(dirname,'app.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(dirname,'tape.js'),'utf8'),context);
vm.runInContext("E.watch=['AAPL','NVDA'];E.configured=true;",context);
const t=Date.now();
function deliver(events){
  context.packet={status:{stream:'Connected'},symbols:['AAPL','NVDA'],events};
  vm.runInContext('acceptCollectorPacket(packet)',context);
}
deliver([{s:'AAPL',p:210.25,t,v:0,receivedAt:t}]);
assert.equal(vm.runInContext('E.trades.size',context),0);
deliver([{s:'AAPL',p:210.3,t,v:17,receivedAt:t}]);
assert.equal(vm.runInContext('E.trades.get("AAPL").v',context),17);
assert.equal(vm.runInContext('quoteFor("AAPL").type',context),'live');
deliver([{s:'AAPL',p:999,t:t-700000,v:25,receivedAt:t},{s:'XYZ',p:55,t,v:2,receivedAt:t}]);
assert.equal(vm.runInContext('E.trades.get("AAPL").p',context),210.3);
assert.equal(vm.runInContext('E.trades.size',context),1);
assert.equal(vm.runInContext('tapeClean({t:'+t+',p:100,v:0})',context),null);
assert.equal(vm.runInContext('tapeClean({t:'+t+',p:100,v:3}).v',context),3);
vm.runInContext(`T.events=[{t:${t},p:12,v:1},{t:${t-20},p:11,v:2}];T.range='1h';T.follow=true;`,context);
assert.equal(vm.runInContext('tapeVisible()[0].p',context),11,'trade events sorted chronologically');
console.log('Live Tape client: collector classification and sorting assertions passed');
