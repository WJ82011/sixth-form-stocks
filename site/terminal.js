/* Market Desk Professional Terminal v1.4.0.
 * UI-only adapter: reads the existing Finnhub feed and chart in memory.
 * Never starts a second WebSocket, changes quote sources, or invents prices.
 */
(function(){
  'use strict';
  const byId=id=>document.getElementById(id);
  const safe=s=>escapeHtml(String(s??''));
  const price=(sym,p)=>p!==null&&p!==undefined&&Number.isFinite(Number(p))&&Number(p)>0?fmtUnit(sym,Number(p)):'—';
  const number=(n,precision=2)=>Number.isFinite(n)?n.toLocaleString('en-GB',{maximumFractionDigits:precision}):'—';
  const signed=p=>Number.isFinite(p)?`${p>=0?'+':''}${p.toFixed(2)}%`:'—';
  const deltaClass=p=>p>0?'pro-pos':p<0?'pro-neg':'';
  const quoteField=(quote,key)=>quote&&quote[key]!==null&&quote[key]!==undefined&&Number.isFinite(Number(quote[key]))&&Number(quote[key])>0?Number(quote[key]):null;
  const timestamp=t=>Number.isFinite(Number(t))&&Number(t)>0?new Date(Number(t)).toLocaleTimeString('en-GB',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';
  const sourceFor=(sym)=>{
    const q=quoteFor(sym);
    // Only the original price feed may determine quote vs recent, verified trade.
    const trade=E.trades.get(sym);
    return {ob:q,record:E.quotes.get(sym)?.quote||null,trade,executed:Boolean(q?.type==='live'&&Number(trade?.v)>0)};
  };
  const current=()=>document.body.dataset.edition==='professional';
  let anchor=null,renderStamp='';
  function moveChart(){
    const panel=byId('main-chart-panel');
    if(!panel)return;
    if(!anchor){anchor=document.createComment('overview-chart-original-position');panel.parentNode.insertBefore(anchor,panel)}
    const slotted=window.Shell43?.chartSlot();
    const goal=slotted||(current()?byId('pro-chart-mount'):((typeof Desk!=='undefined'&&Desk.chartMount())||anchor.parentNode));
    if(slotted&&panel.parentNode===slotted)return;
    if(!goal)return;
    if(!current() && panel.classList.contains('is-expanded') && typeof toggleExpandedChart==='function')toggleExpandedChart(false);
    if(panel.parentNode!==goal){
      if(goal===anchor.parentNode)anchor.parentNode.insertBefore(panel,anchor.nextSibling);else goal.appendChild(panel);
      window.dispatchEvent(new Event('resize'));
      // Chart is an existing canvas using actual locally recorded/provider observations.
      if(typeof drawChart==='function')requestAnimationFrame(drawChart);
    }
  }
  function feedLabel(){
    if(!E.configured)return 'FINNHUB / NOT CONFIGURED';
    if(E.wsOpen && E.verifiedAt && Date.now()-E.verifiedAt<180000)return 'FINNHUB / VERIFIED RECENT STREAM';
    if(E.wsOpen)return 'WEBSOCKET OPEN / AWAITING TRADE';
    if(E.lastGoodQuoteAt && Date.now()-E.lastGoodQuoteAt<180000)return 'FINNHUB / QUOTE SNAPSHOTS';
    return 'FEED / NOT VERIFIED LIVE';
  }
  function getLabel(ob,executed){return executed?'VERIFIED TRADE':ob?.type==='live'?'STREAM PRICE':ob?.type==='stale'?'STALE QUOTE':ob?'QUOTE SNAPSHOT':'NO DATA'}
  function sessionLabel(sym){
    try{const session=typeof marketSessionFor==='function'?marketSessionFor(sym):null;return session?.label||'HOURS UNKNOWN'}catch(_){return 'HOURS UNKNOWN'}
  }
  function focus(sym){setSelected(sym);renderStamp='';render();requestAnimationFrame(()=>{if(typeof drawChart==='function')drawChart()})}
  function topStrip(){
    const target=byId('pro-quote-strip');
    const watch=E.watch.slice(0,6);
    target.innerHTML=watch.length?watch.map(sym=>{
      const {ob,executed}=sourceFor(sym);
      const label=getLabel(ob,executed);
      return `<button type="button" class="pro-quote-cell" data-pro-select="${safe(sym)}" aria-current="${sym===E.selected}"><span class="pro-quote-id">${safe(sym)} <small>${safe(label)}</small></span><span class="pro-quote-value">${safe(price(sym,ob?.p))}</span><span class="pro-quote-foot"><em class="${deltaClass(ob?.change)}">${safe(signed(ob?.change))}</em><em>${safe(timestamp(ob?.t))}</em></span></button>`;
    }).join(''):'<div class="pro-empty">Add stocks in Stock Browser to see them here.</div>';
  }
  function watchList(){
    byId('pro-watch-count').textContent=E.watch.length+' MONITORED';
    const symbols=E.watch.slice(0,60);
    const monitor=byId('pro-ops-watch');
    const previousScroll=monitor.scrollTop;
    monitor.innerHTML=symbols.map(sym=>{
      const {ob}=sourceFor(sym);
      return `<button type="button" class="pro-watch-row ${sym===E.selected?'selected':''}" data-pro-select="${safe(sym)}" aria-current="${sym===E.selected}" title="${safe(E.names[sym]||sym)}"><span><strong>${safe(sym)}</strong><small class="pro-watch-name">${safe(E.names[sym]||sym)}</small></span><span class="pro-watch-number">${safe(price(sym,ob?.p))}</span><span class="pro-watch-delta ${deltaClass(ob?.change)}">${safe(signed(ob?.change))}</span></button>`;
    }).join('')||'<div class="pro-empty">No stocks saved yet.</div>';
    monitor.scrollTop=previousScroll;
  }
  function inspector(){
    const sym=E.selected||E.watch[0]||'AAPL';
    const {ob,record,trade,executed}=sourceFor(sym);
    const prior=quoteField(record,'pc');
    const pct=prior&&ob?.p?(ob.p-prior)/prior*100:null;
    const sess=sessionLabel(sym);
    byId('pro-focus-name').innerHTML=safe(sym)+' <small>'+safe(E.names[sym]||sym)+'</small>';
    const replayPrice=window.Replay43?.active?Replay43.prices().at(-1)?.p:null;
    byId('pro-focus-last').textContent=price(sym,replayPrice??ob?.p);
    byId('pro-focus-move').textContent=window.Replay43?.active?'Revealed prices only':pct===null?'CHANGE UNAVAILABLE':signed(pct)+' VS PREVIOUS CLOSE';
    byId('pro-focus-move').className=deltaClass(pct);
    byId('pro-focus-source').textContent=getLabel(ob,executed);
    byId('pro-focus-session').textContent=sess.toUpperCase();
    byId('pro-feed-state').textContent=feedLabel();
    byId('pro-session-state').textContent='US EQUITIES / '+sessionLabel('AAPL').toUpperCase();
    const replay=window.Replay43?.active?Replay43.frame():null;
    const items=[
      ['OPEN',price(sym,replay?replay.prices[0]?.p:quoteField(record,'o'))],['SESSION HIGH',price(sym,replay?replay.high:quoteField(record,'h'))],
      ['SESSION LOW',price(sym,replay?replay.low:quoteField(record,'l'))],['PREVIOUS CLOSE',replay?'Hidden until replay ends':price(sym,prior)],
      ['FINNHUB QUOTE AT',timestamp(quoteField(record,'t')?Number(record.t)*1000:null)],
      ['OBSERVED AT',timestamp(ob?.t)],['OBSERVATION TYPE',getLabel(ob,executed)]
    ];
    byId('pro-focus-fields').innerHTML=items.map(([name,value])=>`<div class="pro-field-row"><span>${safe(name)}</span><strong>${safe(value)}</strong></div>`).join('');
    const count=Number(trade?.v)>0?number(trade.v,4):'—';
    byId('pro-trade-inspect').innerHTML=`<div class="pro-activity-line"><span>SOCKET TRANSPORT</span><b>${E.wsOpen?'OPEN':'CLOSED'}</b></div><div class="pro-activity-line"><span>TRADE CONFIRMED</span><b>${executed?'RECENT + POSITIVE SIZE':'NO RECENT VERIFIED TRADE'}</b></div><div class="pro-activity-line"><span>LAST REPORTED SIZE</span><b>${safe(count)}</b></div><div class="pro-activity-line"><span>LAST STREAM EVENT</span><b>${Number(trade?.v)>0?safe(timestamp(trade.t)):'—'}</b></div><p class="pro-activity-warning">Quotes are not executed trades. This screen has no order book or bid/ask spread. Local events are incomplete exchange coverage.</p>`;
  }
  function crossTable(){
    byId('pro-cross-body').innerHTML=E.watch.slice(0,60).map(sym=>{
      const {ob,record,executed}=sourceFor(sym);
      const prev=quoteField(record,'pc');
      const ch=prev&&ob?.p?(ob.p-prev)/prev*100:null;
      return `<tr class="${sym===E.selected?'selected':''}" data-pro-select="${safe(sym)}" tabindex="0" aria-label="Inspect ${safe(sym)}"><td><strong>${safe(sym)}</strong></td><td>${safe(price(sym,ob?.p))}</td><td class="${deltaClass(ch)}">${safe(signed(ch))}</td><td>${safe(price(sym,quoteField(record,'o')))}</td><td>${safe(price(sym,quoteField(record,'h')))}</td><td>${safe(price(sym,quoteField(record,'l')))}</td><td>${safe(price(sym,prev))}</td><td>${safe(getLabel(ob,executed))} · ${safe(timestamp(ob?.t))}</td></tr>`;
    }).join('')||'<tr><td colspan="8">No prices yet. Add stocks in Stock Browser.</td></tr>';
  }
  function researchWire(){
    const cursor=window.Replay43?.active?Replay43.cursor:Infinity;
    const news=(Array.isArray(E.news)?E.news:[]).filter(item=>!Number.isFinite(cursor)||!Number(item.datetime)||Number(item.datetime)*1000<=cursor).slice(0,5);
    byId('pro-research-wire').innerHTML=news.map(item=>{
      const href=validHttpLink(item.url);
      const time=Number(item.datetime)>0?timestamp(item.datetime*1000):'—';
      // Only Finnhub-provided headline text and validated HTTP(S) source links are used.
      const inner=`<small>${safe(item.source||'FINNHUB')} / ${safe(time)}</small>${safe(item.headline||'Untitled item')}`;
      return href?`<a class="pro-wire-item" href="${safe(href)}" target="_blank" rel="noopener noreferrer">${inner}</a>`:`<div class="pro-wire-item">${inner}</div>`;
    }).join('')||'<div class="pro-empty">No sourced headlines loaded. Visit Market News to refresh the feed.</div>';
  }
  function render(){
    if(!current()||typeof E==='undefined'||!['overview','home','company'].includes(E.view))return;
    const quoteState=E.watch.map(s=>{
      const q=E.quotes.get(s),t=E.trades.get(s);return `${s}:${q?.quote?.t||0}:${q?.receivedAt||0}:${t?.t||0}:${t?.receivedAt||0}`;
    }).join('|');
    const wire=Array.isArray(E.news)?E.news.map(n=>`${n.datetime||0} ${n.headline||''}`).join('|'):'';
    const key=[E.selected,E.wsOpen,E.verifiedAt,Math.floor(Date.now()/60000),wire,quoteState].join(':');
    if(key===renderStamp)return;
    renderStamp=key;
    topStrip();watchList();inspector();crossTable();researchWire();
  }
  function updateEdition(){renderStamp='';moveChart();if(current()){
    render();
    // The old chart remains the same interactive canvas. Only its position changes.
    requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')));
  }}
  function init(){
    if(!byId('pro-console')||!byId('main-chart-panel'))return;
    byId('pro-console').addEventListener('click',event=>{
      const nav=event.target.closest('[data-pro-nav]');
      if(nav){const target=nav.dataset.proNav;const button=document.querySelector('.nav-btn[data-view="'+target+'"]');if(button)button.click();return}
      const stock=event.target.closest('[data-pro-select]');
      if(stock){focus(stock.dataset.proSelect);return}
    });
    byId('pro-console').addEventListener('keydown',event=>{
      const row=event.target.closest('tr[data-pro-select]');
      if(row&&(event.key==='Enter'||event.key===' ')){event.preventDefault();focus(row.dataset.proSelect)}
    });
    window.addEventListener('marketdesk:edition-change',updateEdition);
    window.addEventListener('marketdesk:layout',()=>{moveChart();if(current()){renderStamp='';render()}if(typeof drawChart==='function')requestAnimationFrame(drawChart)});
    const observer=new MutationObserver(()=>{if(current()&&E.view==='overview'){renderStamp='';render()}});
    observer.observe(byId('view-overview'),{attributes:true,attributeFilter:['class']});
    updateEdition();
    // Read-only refresh from the existing provider state. No network calls.
    setInterval(()=>{if(document.visibilityState==='visible')render()},1100);
  }
  window.MarketDeskTerminal=Object.freeze({active:current,refresh:()=>{renderStamp='';render()}});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
