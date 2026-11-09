// Offline Live Tape autocomplete behavior. Fake provider rows test UI logic only;
// no generated prices or stock suggestions enter production.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const dirname=path.resolve(__dirname,'../site'),elements=new Map();
const cls=()=>{let set=new Set();return {add(k){set.add(k)},remove(k){set.delete(k)},toggle(k,force){if(force===true)set.add(k);else if(force===false)set.delete(k);else set.has(k)?set.delete(k):set.add(k);return set.has(k)},contains(k){return set.has(k)}}};
function dom(id){if(!elements.has(id))elements.set(id,{id,value:'',textContent:'',innerHTML:'',style:{},className:'',classList:cls(),events:{},setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]},getAttribute(k){return this[k]},addEventListener(k,fn){this.events[k]=fn},querySelector(){return null},querySelectorAll(){return []},scrollIntoView(){},blur(){},getBoundingClientRect(){return {width:100,height:100}},getContext(){return {setTransform(){},clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},fillText(){},fillRect(){},fill(){},save(){},restore(){},closePath(){},arc(){},setLineDash(){},createLinearGradient(){return {addColorStop(){}}}}}});return elements.get(id)}
let timers=new Map(),nextTimer=0;
const fakeStorage=new Map();
const context={Date,Math,Number,JSON,Object,Array,Set,Map,RegExp,String,Promise,Intl,console,
 window:{devicePixelRatio:1,addEventListener(){}},document:{readyState:'loading',body:dom('body'),getElementById:dom,addEventListener(){},querySelectorAll(){return []}},
 localStorage:{getItem(k){return fakeStorage.get(k)||null},setItem(k,v){fakeStorage.set(k,v)}},
 setTimeout(fn,delay){const key=++nextTimer;timers.set(key,fn);return key},clearTimeout(k){timers.delete(k)},setInterval(){return 2},clearInterval(){},
 requestAnimationFrame(){return 1}, URL,Blob};
vm.createContext(context);
for(const script of ['market-hours.js','app.js','tape.js'])vm.runInContext(fs.readFileSync(path.join(dirname,script),'utf8'),context);
const ev=code=>vm.runInContext(code,context);
ev(`E.watch=['AAPL','TSLA','NVDA'];E.configured=true;E.view='tape';tapeSetup();`);
const input=dom('tape-quick-search'),pane=dom('tape-quick-results');

// Instant local matches before a provider request finishes.
input.value='tes';ev('tapeSearchSchedule()');
assert(pane.innerHTML.includes('Tesla'), 'Shows local Tesla autocomplete from a prefix');
assert(pane.innerHTML.includes('Searching Finnhub'), 'Shows honest loading status');
assert.equal(input['aria-expanded'],'true');
assert.equal(input['aria-autocomplete'],undefined); // The HTML carries the combobox attributes.
assert.equal(ev('T.searchResults.length'),1);

(async()=>{
  // Only accept genuine provider responses; validate symbols and escape descriptions.
  ev(`api=async function(path){return {result:[
    {symbol:'TEST',description:'TestCo Holdings',type:'Common Stock'},
    {symbol:'TESO',description:'Tesoro AG',type:'Common Stock'},
    {symbol:'<bad>',description:'BAD',type:'Common Stock'},
    {symbol:'TSLA',description:'Tesla duplicate',type:'Common Stock'},
    {symbol:'TESQ',description:'Tes <img src=x onerror=alert(1)>',type:'Common Stock'}
  ]}}`);
  const seq=ev('T.searchRequest');
  await ev(`tapeFetchSuggestions('TES',${seq})`);
  assert(pane.innerHTML.includes('TestCo Holdings'),'Remote provider result appears');
  assert(pane.innerHTML.includes('Tesoro AG'),'More than one matching stock appears');
  assert(!pane.innerHTML.includes('data-tape-suggest="<bad>"'), 'Unsafe provider symbols dropped');
  assert(!pane.innerHTML.includes('<img src=x'), 'Provider text is escaped');
  assert(pane.innerHTML.includes('&lt;img'), 'Escaped text appears as text');
  assert(!ev('T.searchLoading'));
  assert(pane.innerHTML.includes('+ ADD & OPEN'),'Results explain one-click add and open');
  assert.equal(ev('T.searchResults.filter(x=>x.sym===\'TSLA\').length'),1,'Remote and watched duplicates merged');

  // Arrow-key navigation and keyboard selection must use highlighted choice.
  ev('T.searchActive=-1;tapeSearchMove(1)');
  assert.equal(ev('T.searchActive'),0);
  assert.equal(input['aria-activedescendant'],'tape-suggestion-0');
  ev('tapeSearchMove(1)');
  assert.equal(ev('T.searchActive'),1);
  const picked=ev('T.searchResults[T.searchActive].sym');
  // Stubs isolate stock-search behavior from quote polling and UI redraw.
  ev(`addStock=function(sym,name){E.watch.push(sym);E.names[sym]=name};tapeSelect=function(sym){T.symbol=sym;tapeCloseSuggestions(true)};`);
  assert(ev('tapeChooseSuggestion(T.searchResults[T.searchActive].sym,T.searchResults[T.searchActive].name)'));
  assert.equal(ev('T.symbol'),picked);
  assert(ev(`E.watch.includes('${picked}')`));
  assert.equal(input.value,'');
  assert(pane.classList.contains('hidden'));

  // Out-of-order provider replies must not overwrite the latest query.
  ev(`api=async function(path){return {result:[{symbol:'OLD',description:'Old result'}]}}`);
  input.value='alph';ev('tapeSearchSchedule()');
  const stale=ev('T.searchRequest');
  input.value='micro';ev('tapeSearchSchedule()');
  await ev(`tapeFetchSuggestions('ALPH',${stale})`);
  assert(!pane.innerHTML.includes('Old result'));
  assert(ev('T.searchLoading'));

  // No token: watchlist still suggests, and explains why remote search is not available.
  ev('E.configured=false');input.value='nvid';ev('tapeSearchSchedule()');
  assert(pane.innerHTML.includes('NVIDIA'));
  assert(pane.innerHTML.includes('Connect a Finnhub token'));

  // Escape/click-away cancels requests so they cannot reopen the panel.
  const id=ev('T.searchRequest');
  ev('tapeCloseSuggestions(true)');
  assert(pane.classList.contains('hidden'));
  await ev(`tapeFetchSuggestions('NVID',${id})`);
  assert(pane.classList.contains('hidden'));
  assert.equal(input.value,'');

  // Watchlist capacity is enforced before adding a provider suggestion.
  ev('E.watch=Array.from({length:60},(_,i)=>"S"+i);');
  assert.equal(ev('tapeChooseSuggestion("NEWC","New Company")'),false);
  assert(!ev('E.watch.includes("NEWC")'));

  // No hidden, fabricated price data is displayed in autocomplete.
  assert(!/\$\d{2,}/.test(pane.innerHTML));
  const html=fs.readFileSync(path.join(dirname,'index.html'),'utf8');
  assert(html.includes('aria-autocomplete="list"'));
  assert(html.includes('role="combobox"'));
  assert(html.includes('role="listbox"'));
  console.log('Live Tape autocomplete: 24 matching, provider, keyboard, race, security and accessibility assertions passed');
})().catch(err=>{console.error(err);process.exitCode=1});
