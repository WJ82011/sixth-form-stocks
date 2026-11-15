/* Market Desk 1.3.0 · Professional Edition and personal workspace preferences.
   All figures come from previously received Finnhub quotes or captured trade events.
   No new provider calls, no fabricated prices, no full-exchange-volume claim. */
(function(){
  'use strict';
  const STORAGE_KEY='md-reborn-workstation-v1';
  const DEFAULTS=Object.freeze({edition:'signal',density:'balanced',colour:'blue',chartHeight:'standard',contrast:'normal',ticker:true,motion:true});
  const ALLOWED=Object.freeze({edition:['signal','professional'],density:['balanced','compact','terminal'],colour:['blue','brass','cyan','mint','violet'],chartHeight:['standard','large','xl'],contrast:['normal','high']});
  const el=id=>document.getElementById(id);
  let prefs={...DEFAULTS};
  let renderKey='';
  function normalise(raw){
    const p={...DEFAULTS};
    if(!raw||typeof raw!=='object'||Array.isArray(raw))return p;
    for(const key of Object.keys(ALLOWED))if(ALLOWED[key].includes(raw[key]))p[key]=raw[key];
    for(const key of ['ticker','motion'])if(typeof raw[key]==='boolean')p[key]=raw[key];
    return p;
  }
  function restore(){try{const p=normalise(JSON.parse(localStorage.getItem(STORAGE_KEY)));if(!localStorage.getItem('md-reborn-rounded-v24')){if(p.colour==='brass')p.colour='blue';localStorage.setItem(STORAGE_KEY,JSON.stringify(p));localStorage.setItem('md-reborn-rounded-v24','1');}return p}catch(_){return {...DEFAULTS}}}
  function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(prefs));el('preferences-feedback').textContent='✓ Preferences saved locally';window.dispatchEvent(new Event('marketdesk:preference-saved'));return true}catch(_){el('preferences-feedback').textContent='Changes applied, but browser storage is unavailable';return false}}
  function apply(){
    const body=document.body;
    body.dataset.edition=prefs.edition;
    body.dataset.density=prefs.density;
    body.dataset.colour=prefs.colour;
    body.dataset.chartHeight=prefs.chartHeight;
    body.dataset.contrast=prefs.contrast;
    body.dataset.ticker=prefs.ticker?'on':'off';
    body.dataset.motion=prefs.motion?'on':'off';
    el('desk-edition-label').textContent=prefs.edition==='professional'?'PROFESSIONAL / 02':'STANDARD / 01';
    const editionHeading=el('desk-overview-edition');if(editionHeading)editionHeading.textContent=prefs.edition==='professional'?'THE PROFESSIONAL MODE':'THE STANDARD MODE';
    for(const [id,edition] of [['edition-signal','signal'],['edition-pro','professional']]){
      const node=el(id);const active=prefs.edition===edition;
      node.setAttribute('aria-pressed',String(active));node.querySelector('.edition-check').textContent=active?'●':'○';
    }
    el('pref-density').value=prefs.density;
    el('pref-chart-height').value=prefs.chartHeight;
    el('pref-contrast').value=prefs.contrast;
    el('pref-ticker').checked=prefs.ticker;
    el('pref-motion').checked=prefs.motion;
    for(const node of document.querySelectorAll('.colour-choice'))node.setAttribute('aria-pressed',String(prefs.colour===node.dataset.colour));
    renderKey='';renderPanels();
    // Both chart engines already provide their own resize/draw functions.
    // The DOM updates synchronously, and ResizeObserver/resize event catches layout changes.
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new CustomEvent('marketdesk:edition-change',{detail:{edition:prefs.edition}}));
  }
  function setPref(key,value){prefs=normalise({...prefs,[key]:value});apply();save()}
  function price(sym,value){return Number.isFinite(Number(value))&&Number(value)>0?fmtUnit(sym,Number(value)):'—'}
  function count(value){return Number.isFinite(Number(value))&&Number(value)>=0?Number(value).toLocaleString('en-GB',{maximumFractionDigits:0}):'—'}
  function percentage(value){return Number.isFinite(Number(value))?`${Number(value)>=0?'+':''}${Number(value).toFixed(2)}%`:'—'}
  function readableTime(ms){return Number.isFinite(ms)&&ms>0?new Date(ms).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'—'}
  function validQuoteField(q,field){const v=q?.[field];return (v!==null&&v!==undefined&&Number.isFinite(Number(v))&&Number(v)>0)?Number(v):null}
  function sourceState(sym){
    const observed=quoteFor(sym);
    const record=E.quotes.get(sym);
    const quote=record?.quote||null;
    return {observed,quote};
  }
  function metrics(values){return values.map(([name,value,detail,cls])=>`<div class="pro-stat"><span>${escapeHtml(name)}</span><strong class="${cls||''}">${escapeHtml(value)}</strong><small>${escapeHtml(detail||'')}</small></div>`).join('')}
  function buildOverview(){
    const target=el('pro-overview-metrics');if(!target)return;
    const sym=E.selected||E.watch?.[0]||'AAPL';
    const {observed,quote}=sourceState(sym);
    const last=observed?.p;
    const prev=validQuoteField(quote,'pc');
    const movement=prev&&Number.isFinite(last)?(last-prev)/prev*100:null;
    const session=typeof marketSessionFor==='function'?marketSessionFor(sym):null;
    el('pro-overview-symbol').textContent=sym+' · '+(E.names[sym]||sym);
    const fields=[
      ['Last observation',price(sym,last),observed?.type==='live'?'VERIFIED FINNHUB TRADE':observed?.type==='stale'?'STALE QUOTE / NOT CURRENT':observed?'LATEST FINNHUB QUOTE':'NO USABLE OBSERVATION'],
      ['Move vs prior close',movement===null?'—':percentage(movement),prev?'Calculated from the recorded price and previous closing price':'PRIOR CLOSE UNAVAILABLE',movement>0?'pro-pos':movement<0?'pro-neg':''],
      ['Session open',price(sym,validQuoteField(quote,'o')),'FINNHUB QUOTE FIELD'],
      ['Session high',price(sym,validQuoteField(quote,'h')),'FINNHUB QUOTE FIELD'],
      ['Session low',price(sym,validQuoteField(quote,'l')),'FINNHUB QUOTE FIELD'],
      ['Previous close',price(sym,prev),'FINNHUB QUOTE FIELD'],
      ['Provider quote at',readableTime(Number(quote?.t)*1000),'EXCHANGE / PROVIDER TIME'],
      ['Latest trade at',E.trades.get(sym)?.v>0?readableTime(E.trades.get(sym).t):'—','POSITIVE-VOLUME VERIFIED EVENT'],
      ['Session schedule',String(session?.label||'HOURS UNKNOWN'),session?.state==='unknown'?'NOT VERIFIED FOR THIS VENUE':'SCHEDULE ≠ LIVE MARKET DATA'],
      ['Data transport',E.wsOpen?'SOCKET OPEN':'SOCKET CLOSED',observed?.type==='live'?'RECENT TRADE CONFIRMED':observed?'QUOTE / NOT LIVE TICK':'NO CONFIRMED TRADE']
    ];
    target.innerHTML=metrics(fields);
  }
  function matrixSort(symbols){
    const sort=el('pro-matrix-sort')?.value||'watch';
    if(sort==='symbol')return symbols.sort((a,b)=>a.localeCompare(b));
    if(sort==='change')return symbols.sort((a,b)=>{
      const change=s=>{const {quote,observed}=sourceState(s);const pc=validQuoteField(quote,'pc');return pc&&observed?.p?(observed.p-pc)/pc*100:Number.NEGATIVE_INFINITY};
      return change(b)-change(a)||a.localeCompare(b);
    });
    return symbols;
  }
  function buildMatrix(){
    const target=el('pro-matrix-body');if(!target)return;
    const symbols=matrixSort((E.watch||[]).slice());
    if(!symbols.length){target.innerHTML='<tr><td colspan="8">No stocks in your watchlist yet.</td></tr>';return}
    target.innerHTML=symbols.map(sym=>{
      const {observed,quote}=sourceState(sym);
      const pc=validQuoteField(quote,'pc');
      const delta=pc&&observed?.p?(observed.p-pc)/pc*100:null;
      const label=observed?.type==='live'?'VERIFIED TRADE':observed?.type==='stale'?'STALE QUOTE':observed?'QUOTE SNAPSHOT':'UNAVAILABLE';
      const stamp=observed?.t;
      return `<tr data-select="${escapeHtml(sym)}" role="button" tabindex="0" aria-label="Inspect ${escapeHtml(E.names[sym]||sym)}"><td><div class="pro-symbol-name"><strong>${escapeHtml(sym)}</strong><small>${escapeHtml(E.names[sym]||sym)}</small></div></td><td>${escapeHtml(price(sym,observed?.p))}</td><td class="${delta>0?'pro-pos':delta<0?'pro-neg':''}">${delta===null?'—':escapeHtml(percentage(delta))}</td><td>${escapeHtml(price(sym,validQuoteField(quote,'o')))}</td><td>${escapeHtml(price(sym,validQuoteField(quote,'h')))}</td><td>${escapeHtml(price(sym,validQuoteField(quote,'l')))}</td><td>${escapeHtml(price(sym,pc))}</td><td class="pro-source">${escapeHtml(label)} · ${escapeHtml(readableTime(stamp))}</td></tr>`;
    }).join('');
  }
  function buildTape(){
    const target=el('pro-tape-metrics');if(!target||typeof T==='undefined')return;
    const sym=T.symbol||'AAPL';
    // The tape itself accepts only genuine, positive-volume events. Never include quotes.
    const events=T.events.filter(x=>Number.isFinite(x.p)&&x.p>0&&Number.isFinite(x.v)&&x.v>0);
    let volume=0,notional=0,low=Infinity,high=-Infinity;
    for(const x of events){volume+=x.v;notional+=x.p*x.v;low=Math.min(low,x.p);high=Math.max(high,x.p)}
    const mostRecent=events.length?events.reduce((a,b)=>b.t>a.t?b:a):null;
    const indicator=typeof tapeSymbolIndicators==='function'?tapeSymbolIndicators(sym):null;
    target.innerHTML=metrics([
      ['Selected stock',sym,E.names[sym]||sym],
      ['Captured trades',count(events.length),T.events.length>=4000?'CAPPED LOCAL SAMPLE':'POSITIVE-VOLUME EVENTS ONLY'],
      ['Observed sample volume',count(volume),'UNITS REPORTED BY FINNHUB'],
      ['Observed sample VWAP',volume>0?price(sym,notional/volume):'—','AVERAGE OF RECORDED TRADES, NOT THE WHOLE MARKET'],
      ['Last captured trade',mostRecent?readableTime(mostRecent.t):'—',indicator?.verified?'RECENT LIVE EVENT':'HISTORICAL CAPTURE / NOT CURRENT']
    ]);
  }
  function renderPanels(){
    if(prefs.edition!=='professional'||typeof E==='undefined')return;
    if(E.view==='overview')buildOverview();
    if(E.view==='markets')buildMatrix();
    if(E.view==='tape')buildTape();
  }
  function init(){
    prefs=restore();
    window.addEventListener('marketdesk:workspace-restored',()=>{prefs=restore();apply()});
    el('edition-signal').addEventListener('click',()=>setPref('edition','signal'));
    el('edition-pro').addEventListener('click',()=>setPref('edition','professional'));
    for(const [id,key] of [['pref-density','density'],['pref-chart-height','chartHeight'],['pref-contrast','contrast']])el(id).addEventListener('change',e=>setPref(key,e.target.value));
    for(const key of ['ticker','motion'])el('pref-'+key).addEventListener('change',e=>setPref(key,e.target.checked));
    for(const node of document.querySelectorAll('.colour-choice'))node.addEventListener('click',()=>setPref('colour',node.dataset.colour));
    el('pro-matrix-sort').addEventListener('change',()=>{renderKey='';renderPanels()});
    el('preferences-reset').addEventListener('click',()=>{prefs={...DEFAULTS};apply();save();el('preferences-feedback').textContent='✓ Default appearance restored'});
    apply();
    // Switching workspaces must render institutional widgets immediately,
    // without waiting for the background refresh interval.
    const observer=new MutationObserver(()=>renderPanels());
    for(const view of document.querySelectorAll('.view'))observer.observe(view,{attributes:true,attributeFilter:['class']});
    // Updates are read-only and never initiate extra API calls.
    setInterval(()=>{if(document.visibilityState==='visible')renderPanels()},2500);
  }
  window.MarketDeskPreferences=Object.freeze({normalise,patch:patch=>{prefs=normalise({...prefs,...patch});apply();save()},defaults:()=>({...DEFAULTS}),current:()=>({...prefs})});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
