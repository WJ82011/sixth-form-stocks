/* Live Tape 1.1.2 · verified Finnhub events, sourced stock-autocomplete, quick switching. */
'use strict';
const TAPE_RANGES = Object.freeze({'1m':60000,'5m':300000,'15m':900000,'1h':3600000,'1d':86400000});
const T = {
  symbol:'AAPL', range:'1h', follow:true, pause:false, anchor:0,
  events:[], chartStyle:'trades', review:null, reviewId:0, frozen:null, minSize:0, hoverX:null, hoverY:null, loadId:0, setup:false,
  refreshTimer:0, redrawTimer:0, hoverFrame:0, lastMarqueeSymbols:'', viewport:null,
  chartLayout:null, recentReceived:0, lastError:'', lastSeenTrade:null,
  dragStart:null, pendingDuringLoad:[], loading:false, lastSwitcherRender:0, lastShortcutKey:'', lastRadarRender:0, lastRadarFilter:'',
  searchTimer:0, searchRequest:0, searchActive:-1, searchResults:[], searchCache:new Map(), searchLoading:false, searchError:''
};
const tapeTime = t => new Date(t).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
const tapeTimeMs = t => new Date(t).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit',fractionalSecondDigits:3});
const tapeNum = n => Number(n).toLocaleString('en-GB',{maximumFractionDigits:2});
const tapePrice = (sym,p) => fmtUnit(sym,p);
// Scheduled exchange hours and actual streaming evidence are independent.
function tapeSymbolIndicators(sym,at=new Date()){
  const market=typeof marketSessionFor==='function'?marketSessionFor(sym,at):{state:'unknown',label:'HOURS UNKNOWN',detail:'Exchange schedule not loaded',isOpen:false};
  const trade=E.trades.get(sym),ms=at.getTime();
  const verified=Boolean(E.wsOpen&&trade&&trade.v>0&&E.subscribed.has(sym)&&trade.receivedAt<=ms+60000&&ms-trade.receivedAt<180000&&ms-trade.t<300000&&trade.t<=ms+60000);
  const q=quoteFor(sym);
  const feed=verified?'LIVE TRADE':q?.type==='stale'?'STALE QUOTE':q?'QUOTE ONLY':E.wsOpen&&E.subscribed.has(sym)?'AWAITING TRADE':'NO LIVE TICK';
  return {market,verified,feed,quote:q};
}
function tapeSessionPill(s){
  return `<span class="tape-session-badge ${escapeHtml(s.market.state)}" title="${escapeHtml(s.market.detail)}">${escapeHtml(s.market.label)}</span>`;
}
function tapeFeedPill(s){
  return `<span class="tape-feed-badge ${s.verified?'verified':'idle'}" title="${escapeHtml(s.verified?'Recent Finnhub trade with a reported size above zero':'No recent confirmed trade with a size above zero for this stock')}">${s.verified?'● LIVE':'○ '+escapeHtml(s.feed)}</span>`;
}
// Suggestions appear immediately from the local watchlist, then Finnhub's actual
// /search endpoint supplies broader instrument choices. No guessed symbols.
function tapeNormalizeSuggestion(raw){
  if(!raw||typeof raw!=='object')return null;
  const sym=String(raw.symbol||'').trim().toUpperCase();
  if(!safeSymbol(sym))return null;
  const name=String(raw.description||raw.name||E.names[sym]||sym).trim().slice(0,140)||sym;
  const type=String(raw.type||'').slice(0,60);
  const display=String(raw.displaySymbol||sym).slice(0,60);
  return {sym,name,type,display,watched:E.watch.includes(sym)};
}
function tapeSuggestionRank(entry,query){
  const symbol=entry.sym.toUpperCase(),name=entry.name.toUpperCase();
  if(symbol===query)return 0;
  if(symbol.startsWith(query))return 1;
  if(name===query)return 2;
  if(name.startsWith(query))return 3;
  if(symbol.includes(query))return 4;
  if(name.includes(query))return 5;
  return 6;
}
function tapeSuggestionMatches(query,remote=[]){
  const q=String(query||'').trim().toUpperCase();
  if(!q)return [...new Set([...E.watch,...STOCK_DIRECTORY.map(x=>x.symbol)])].slice(0,24).map(sym=>tapeNormalizeSuggestion({symbol:sym,description:safeName(sym)})).filter(Boolean);
  const localRows=typeof localStockMatches==='function'?localStockMatches(q):E.watch.map(sym=>({symbol:sym,description:safeName(sym)}));
  const local=localRows.map(tapeNormalizeSuggestion).filter(Boolean);
  const seen=new Set(local.map(item=>item.sym));
  const provider=[];
  for(const raw of Array.isArray(remote)?remote:[]){
    const item=tapeNormalizeSuggestion(raw);
    if(!item||seen.has(item.sym))continue;
    // Finnhub may include partial matches and other instrument categories;
    // match visible descriptions/symbols before showing a suggestion.
    if(!item.sym.includes(q)&&!item.name.toUpperCase().includes(q)&&!item.display.toUpperCase().includes(q))continue;
    seen.add(item.sym);provider.push(item);
  }
  const order=(a,b)=>tapeSuggestionRank(a,q)-tapeSuggestionRank(b,q)||a.sym.localeCompare(b.sym);
  // Watched instruments remain immediately accessible even when Finnhub is slow.
  return [...local.sort(order).slice(0,5),...provider.sort(order).slice(0,9)].slice(0,12);
}
function tapeSearchOpen(){return !$('tape-quick-results').classList.contains('hidden')}
function tapeCloseSuggestions(clear=false){
  clearTimeout(T.searchTimer);T.searchRequest++;T.searchLoading=false;
  $('tape-quick-results').classList.add('hidden');
  $('tape-quick-search').setAttribute('aria-expanded','false');
  $('tape-quick-search').removeAttribute('aria-activedescendant');
  T.searchActive=-1;
  if(clear)$('tape-quick-search').value='';
}
function tapeRenderSuggestions(){
  const input=$('tape-quick-search'),pane=$('tape-quick-results');
  const q=input.value.trim().toUpperCase();
  const remote=T.searchCache.get(q)?.rows||[];
  const suggestions=tapeSuggestionMatches(q,remote);
  T.searchResults=suggestions;
  if(T.searchActive>=suggestions.length)T.searchActive=suggestions.length-1;
  const sections=[];
  if(suggestions.length){
    sections.push(`<div class="tape-suggestions-caption">${q?'MATCHING STOCKS':'QUICK PICKS'} <span>${suggestions.length} ${q?(suggestions.length===1?'SUGGESTION':'SUGGESTIONS'):'SHORTCUTS'}</span></div>`);
    sections.push(suggestions.map((entry,i)=>{
      const market=entry.watched?tapeSessionPill(tapeSymbolIndicators(entry.sym)):'';
      const tag=entry.watched?'<span class="tape-autocomplete-watch">ON WATCHLIST</span>':'<span class="tape-autocomplete-add">'+(tapeCanOpen(entry.sym)?'OPEN TAPE':'+ FOLLOW & OPEN')+'</span>';
      return `<button type="button" class="tape-search-result tape-autocomplete-result ${i===T.searchActive?'is-active':''}" id="tape-suggestion-${i}" role="option" aria-selected="${i===T.searchActive}" data-tape-suggest="${escapeHtml(entry.sym)}" data-tape-name="${escapeHtml(entry.name)}" title="Open ${escapeHtml(entry.name)} (${escapeHtml(entry.sym)})"><span class="tape-autocomplete-symbol">${escapeHtml(entry.sym)}</span><span class="tape-autocomplete-name"><strong>${escapeHtml(entry.name)}</strong><small>${escapeHtml(entry.type||(entry.watched?'Saved company':'Finnhub result'))}${entry.display!==entry.sym?' · '+escapeHtml(entry.display):''}</small></span><span class="tape-autocomplete-meta">${market}${tag}</span></button>`;
    }).join(''));
  }else if(q&&!T.searchLoading&&!T.searchError){sections.push('<div class="tape-suggestion-message">No matching stocks found. Try a company name or stock symbol.</div>');}
  if(T.searchLoading)sections.push('<div class="tape-suggestion-message" role="status"><span class="tape-search-spinner"></span> Searching Finnhub for more companies…</div>');
  else if(T.searchError)sections.push(`<div class="tape-suggestion-message tape-search-warning" role="status">Finnhub suggestions unavailable: ${escapeHtml(T.searchError)}. Saved stocks remain searchable.</div>`);
  else if(q.length===1)sections.push('<div class="tape-suggestion-message">Keep typing to search Finnhub’s full symbol directory.</div>');
  else if(q.length>=2)sections.push('<div class="tape-suggestion-credit">Search matches sourced from Finnhub · Symbols do not imply live data access</div>');
  else sections.push('<div class="tape-suggestion-credit">Start typing a name or ticker to search Finnhub</div>');
  pane.innerHTML=sections.join('');
  pane.classList.remove('hidden');input.setAttribute('aria-expanded','true');
  if(T.searchActive>=0)input.setAttribute('aria-activedescendant','tape-suggestion-'+T.searchActive);
  else input.removeAttribute('aria-activedescendant');
}
function tapeSearchSchedule(){
  clearTimeout(T.searchTimer);
  T.searchRequest++;
  T.searchActive=-1;T.searchError='';T.searchLoading=false;
  const q=$('tape-quick-search').value.trim().toUpperCase();
  if(!q){tapeRenderSuggestions();return}
  if(q.length<2){tapeRenderSuggestions();return}
  const cached=T.searchCache.get(q);
  if(cached&&nowMs()-cached.at<300000){tapeRenderSuggestions();return}
  if(!E.configured){T.searchError='Add a Finnhub API key in Settings';tapeRenderSuggestions();return}
  T.searchLoading=true;tapeRenderSuggestions();
  const seq=T.searchRequest;
  T.searchTimer=setTimeout(()=>tapeFetchSuggestions(q,seq),330);
}
async function tapeFetchSuggestions(query,seq){
  try{
    const data=await api('/api/search?q='+encodeURIComponent(query));
    // Ignore outdated responses, including ones that arrive after the user
    // switches stocks, closes the dropdown or changes the query.
    if(seq!==T.searchRequest||$('tape-quick-search').value.trim().toUpperCase()!==query)return;
    const rows=Array.isArray(data.result)?data.result:[];
    T.searchCache.set(query,{rows,at:nowMs()});
    if(T.searchCache.size>35)T.searchCache.delete(T.searchCache.keys().next().value);
    T.searchError='';
  }catch(err){
    if(seq!==T.searchRequest||$('tape-quick-search').value.trim().toUpperCase()!==query)return;
    T.searchError=String(err.message||'Request failed').slice(0,180);
  }
  if(seq!==T.searchRequest)return;
  T.searchLoading=false;tapeRenderSuggestions();
}
function tapeSearchMove(delta){
  if(!tapeSearchOpen()){tapeRenderSuggestions();return}
  if(!T.searchResults.length)return;
  T.searchActive=(T.searchActive+delta+T.searchResults.length)%T.searchResults.length;
  tapeRenderSuggestions();
  const option=$('tape-quick-results').querySelector('#tape-suggestion-'+T.searchActive);
  if(option&&option.scrollIntoView)option.scrollIntoView({block:'nearest'});
}
function tapeCanOpen(sym){
  return safeSymbol(sym)&&(E.watch.includes(sym)||(typeof DIRECTORY_BY_SYMBOL!=='undefined'&&Boolean(DIRECTORY_BY_SYMBOL[sym])));
}
function tapeChooseSuggestion(sym,name=''){
  sym=String(sym||'').trim().toUpperCase();
  if(!safeSymbol(sym))return false;
  if(!tapeCanOpen(sym)){
    if(E.watch.length>=60){toast('Watchlist full (60 stocks). Remove a stock in Stock Browser first.');return false}
    addStock(sym,name);
  }else if(name&&(!E.names[sym]||E.names[sym]===sym)){
    E.names[sym]=name;saveJSON('md-reborn-names',E.names);
  }
  if(!tapeCanOpen(sym))return false;
  tapeSelect(sym);
  tapeCloseSuggestions(true);
  return true;
}
// Backwards compatible helper for overview/status refresh calls.
function tapeQuickResults(){if(tapeSearchOpen())tapeRenderSuggestions()}
function tapeQuickStep(direction){
  if(!E.watch.length)return;
  const i=E.watch.indexOf(T.symbol),next=(i+direction+E.watch.length)%E.watch.length;
  tapeSelect(E.watch[next]);
}
function tapeRenderSwitcher(force=false){
  if(!T.setup)return;
  const ms=nowMs();if(!force&&ms-T.lastSwitcherRender<4000)return;T.lastSwitcherRender=ms;
  const chosen=tapeSymbolIndicators(T.symbol),market=chosen.market;
  const badge=$('tape-market-status');badge.textContent=market.label;badge.className='tape-session-badge '+market.state;badge.title=market.detail;
  $('tape-session-summary').textContent=market.detail+' · '+(chosen.verified?'A confirmed Finnhub trade arrived recently':chosen.feed.toLowerCase());
  const fav=['AAPL','NVDA','MSFT','TSLA','GOOGL','AMZN','META','NFLX','AMD','PLTR'];
  const symbols=[...new Set([...fav.filter(sym=>E.watch.includes(sym)),T.symbol])].slice(0,11);
  if(symbols.length<6)for(const sym of E.watch){if(!symbols.includes(sym))symbols.push(sym);if(symbols.length>=10)break}
  const signature=symbols.map(sym=>{const x=tapeSymbolIndicators(sym);return sym+':'+x.market.state+':'+x.verified}).join('|')+'|'+T.symbol;
  if(signature!==T.lastShortcutKey){
    T.lastShortcutKey=signature;
    const oldScroll=$('tape-shortcuts').scrollLeft;
    $('tape-shortcuts').innerHTML=symbols.map(sym=>{
    const s=tapeSymbolIndicators(sym);const selected=sym===T.symbol;
    return `<button type="button" class="tape-chip ${selected?'selected':''}" aria-pressed="${selected}" data-tape-symbol="${escapeHtml(sym)}" title="${escapeHtml(safeName(sym))} — ${escapeHtml(s.market.detail)}; ${s.verified?'verified live trade':'no recent verified trade'}"><span class="tape-chip-name"><strong>${escapeHtml(sym)}</strong><small>${escapeHtml(safeName(sym))}</small></span><span class="tape-chip-badges">${tapeSessionPill(s)}<i class="tape-chip-feed ${s.verified?'verified':''}" title="${escapeHtml(s.feed)}"></i></span></button>`;
  }).join('');
    $('tape-shortcuts').scrollLeft=oldScroll;
  }
  // Do not rebuild autocomplete results on every price tick: preserve keyboard selection.
}
function tapeSelectedSymbol(){return T.symbol}
function tapeSort(events){return events.slice().sort((a,b)=>a.t-b.t||(a.id||0)-(b.id||0))}
function tapeClean(e){
  if(!e||typeof e!=='object')return null;
  const t=Number(e.t),p=Number(e.p),v=Number(e.v),recv=Number(e.receivedAt);
  if(!Number.isInteger(t)||t<946684800000||t>nowMs()+60000||!(p>0&&p<=1e9)||!(v>0&&v<=1e12))return null;
  return {t,p,v,receivedAt:Number.isFinite(recv)?recv:0,id:Number.isInteger(e.id)?e.id:null};
}
function tapeCandles(events,width){
  const bars=new Map();
  for(const trade of tapeSort(events)){
    const bucket=Math.floor(trade.t/width)*width;
    const bar=bars.get(bucket);
    if(bar){
      bar.high=Math.max(bar.high,trade.p);bar.low=Math.min(bar.low,trade.p);
      bar.close=trade.p;bar.last=trade.t;bar.size+=trade.v;bar.count++;
    }else{
      bars.set(bucket,{bucket,first:trade.t,last:trade.t,open:trade.p,high:trade.p,low:trade.p,close:trade.p,size:trade.v,count:1});
    }
  }
  return [...bars.values()];
}
function tapeSegments(points,maximumGap){
  const result=[];
  for(const point of points){
    const last=result.at(-1);
    if(!last||point.t-last.at(-1).t>maximumGap)result.push([point]);
    else last.push(point);
  }
  return result;
}
function tapeReviewControls(){
  const showing=Boolean(T.review);
  $('tape-return-live').classList.toggle('hidden',!showing);
  $('tape-seek-wrap').classList.toggle('hidden',!showing);
  $('tape-date-wrap').classList.toggle('hidden',!showing);
  $('tape-review').disabled=showing;
  $('tape-review-status').textContent=showing
    ?'Saved review · '+tapeFullTime(T.anchor)+' · '+tapeNum(T.review.events.length)+' loaded trades'+(T.review.events.length>=4000?' · newest 4,000 retained in this view':'')
    :'';
}
function tapeSeek(value){
  if(!T.review||!Number.isFinite(value))return;
  if(T.pause)tapeTogglePause();
  const fraction=Math.max(0,Math.min(1,value/1000));
  T.anchor=Math.round(T.review.first+(T.review.last-T.review.first)*fraction);
  tapeReviewControls();tapeRender();
}
async function tapeLoadReview(day=''){
  const symbol=T.symbol,id=++T.reviewId,button=$('tape-review');
  button.disabled=true;
  $('tape-date').disabled=true;
  $('tape-review-status').textContent='Reading saved trade records…';
  try{
    const data=await api('/api/tape?symbol='+encodeURIComponent(symbol)+'&last=1&limit=4000'+(day?'&day='+encodeURIComponent(day):''));
    if(id!==T.reviewId||symbol!==T.symbol)return;
    const events=tapeSort((data.events||[]).map(tapeClean).filter(Boolean));
    if(!events.length)throw Error('This company has no saved trades yet.');
    if(T.pause)tapeTogglePause();
    const selector=$('tape-date');
    selector.innerHTML='<option value="">Latest recording</option>'+ (data.recordingDays||[]).map(row=>
      '<option value="'+escapeHtml(row.date)+'">'+escapeHtml(row.date)+' · '+tapeNum(row.count)+' trades</option>').join('');
    selector.value=day;
    T.review={events,first:events[0].t,last:events.at(-1).t};
    T.anchor=T.review.last;$('tape-seek').value='1000';
    tapeToggleFollow(false);tapeReviewControls();
  }catch(error){
    if(id===T.reviewId)$('tape-review-status').textContent=error.message;
  }finally{
    if(id===T.reviewId){button.disabled=Boolean(T.review);$('tape-date').disabled=false;}
  }
}
function tapeWindow(){
  const width=TAPE_RANGES[T.range],end=T.frozen?.end||(T.follow?nowMs():T.anchor||nowMs());
  return {start:end-width,end,width};
}
function tapeVisible(){const {start,end}=tapeWindow();return tapeSort((T.frozen?.events||T.review?.events||T.events).filter(x=>x.t>=start&&x.t<=end))}
function tapeFullTime(t){return new Date(t).toLocaleString('en-GB',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',fractionalSecondDigits:3})}
function tapeOnView(){
  if(!T.setup)return;
  if(!tapeCanOpen(T.symbol))T.symbol=E.watch[0]||'AAPL';
  tapeReload();
  tapeOnMarketData();
  tapeRenderSwitcher(true);
  window.setTimeout(tapeDraw,80);
}
function tapeOnConnection(){if(T.setup)tapeScheduleRefresh(true)}
function tapeOnTrades(trades){
  if(!T.setup)return;
  for(const item of trades){
    if(item.s!==T.symbol)continue;
    const e=tapeClean(item);if(!e)continue;
    T.lastSeenTrade=e;
    if(T.loading)T.pendingDuringLoad.push(e);
    else T.events.push(e);
  }
  if(T.pendingDuringLoad.length>4600)T.pendingDuringLoad=T.pendingDuringLoad.slice(-4200);
  if(!T.loading&&T.events.length>4600){T.events=tapeSort(T.events).slice(-4200)}
  // Stream recording never stops; pause affects only what the user sees.
  if(!T.pause)tapeScheduleRefresh(false);
}
function tapeScheduleRefresh(full){
  if(E.view!=='tape'||T.pause)return;
  if(full){
    if(!T.refreshTimer)T.refreshTimer=setTimeout(()=>{T.refreshTimer=0;tapeRender()},280);
  }else if(!T.redrawTimer){
    T.redrawTimer=setTimeout(()=>{T.redrawTimer=0;tapeRender()},240);
  }
}
function tapeOnMarketData(){
  if(!T.setup)return;
  if(E.view==='tape'&&!T.pause){
    tapeRenderRadar();tapeRenderMarquee();tapeRenderHealth();tapeRenderSwitcher();
  }
}
async function tapeReload(){
  if(!T.setup)return;
  const symbol=T.symbol;
  if(T.loading&&T.loadingSymbol===symbol)return;
  const req=++T.loadId;
  T.loading=true;T.loadingSymbol=symbol;T.pendingDuringLoad=[];T.lastError='';
  $('tape-symbol-title').textContent=symbol;
  $('tape-symbol-name').textContent=safeName(symbol);
  try{
    const data=await api('/api/tape?symbol='+encodeURIComponent(symbol)+'&since='+Math.max(0,nowMs()-86400000)+'&limit=4000');
    if(req!==T.loadId)return;
    const old=T.pendingDuringLoad;
    const received=(data.events||[]).map(tapeClean).filter(Boolean);
    // A frame may be stored while history is loading. Exclude exact duplicates only;
    // distinct same-timestamp trades are otherwise kept as separate reported events.
    const counts=new Map();
    const key=e=>e.t+'|'+e.p+'|'+e.v;
    for(const e of received)counts.set(key(e),(counts.get(key(e))||0)+1);
    const pending=old.filter(e=>{const k=key(e),remaining=counts.get(k)||0;if(remaining>0){counts.set(k,remaining-1);return false}return true});
    T.events=tapeSort([...received,...pending]).slice(-4500);
    T.lastSeenTrade=T.events[T.events.length-1]||null;
  }catch(err){
    if(req!==T.loadId)return;
    T.lastError='Saved trades could not be loaded: '+err.message;
    T.events=tapeSort([...T.events,...T.pendingDuringLoad]).slice(-4500);
  }finally{
    if(req===T.loadId){T.loading=false;T.pendingDuringLoad=[];tapeRender()}
  }
}
function tapeSelect(sym){
  if(!tapeCanOpen(sym))return;
  if(sym===T.symbol){tapeCloseSuggestions(true);tapeRenderSwitcher(true);return}
  const was=T.symbol;T.symbol=sym;T.anchor=0;T.follow=true;T.pause=false;
  T.reviewId++;T.review=null;T.frozen=null;tapeReviewControls();
  T.events=[];T.lastSeenTrade=null;T.hoverX=null;
  saveJSON('md-tape-symbol',sym);
  tapeCloseSuggestions(true);
  $('tape-symbol-filter').blur();
  $('tape-follow').setAttribute('aria-pressed','true');
  $('tape-pause').setAttribute('aria-pressed','false');
  $('tape-pause').textContent='Ⅱ Pause display';
  $('tape-follow').textContent='◉ Follow latest';
  // Keep one socket. Reconnect only when the desired symbol is not subscribed.
  if(was!==sym&&E.view==='tape')resubscribe();
  tapeRender();tapeReload();tapeRenderRadar();tapeRenderHealth();tapeRenderSwitcher(true);
}
function tapeSetRange(range){
  if(!(range in TAPE_RANGES))return;
  T.range=range;
  document.querySelectorAll('[data-tape-range]').forEach(b=>b.classList.toggle('active',b.dataset.tapeRange===range));
  tapeRender();
}
function tapeZoom(factor){
  const keys=Object.keys(TAPE_RANGES),i=keys.indexOf(T.range),target=Math.max(0,Math.min(keys.length-1,i+factor));
  tapeSetRange(keys[target]);
}
function tapeTogglePause(){
  if(!T.pause){
    const {end}=tapeWindow();
    T.frozen={end,events:(T.review?.events||T.events).slice()};
  }else T.frozen=null;
  T.pause=!T.pause;
  const btn=$('tape-pause');
  btn.setAttribute('aria-pressed',String(T.pause));
  btn.textContent=T.pause?'▶ Resume display':'Ⅱ Pause display';
  if(!T.pause){tapeRender();tapeOnMarketData()}
  else $('tape-point-count').textContent+=' · display paused';
}
function tapeToggleFollow(force){
  T.follow=typeof force==='boolean'?force:!T.follow;
  if(T.follow){
    T.reviewId++;T.review=null;T.anchor=0;
    if(T.pause)tapeTogglePause();
    tapeReviewControls();
  }
  if(!T.follow&&!T.anchor)T.anchor=nowMs();
  $('tape-follow').setAttribute('aria-pressed',String(T.follow));
  $('tape-follow').textContent=T.follow?'◉ Follow latest':'○ Follow paused';
  tapeRender();
}
function tapeExpand(force){
  const panel=$('tape-chart-panel');
  const expanded=typeof force==='boolean'?force:!panel.classList.contains('tape-expanded');
  panel.classList.toggle('tape-expanded',expanded);
  document.body.classList.toggle('tape-expanded-body',expanded);
  $('tape-chart-expand').textContent=expanded?'✕ Close':'⤢ Expand';
  $('tape-chart-expand').setAttribute('aria-expanded',String(expanded));
  setTimeout(tapeDraw,60);
}
function tapeEscape(){if($('tape-chart-panel')?.classList.contains('tape-expanded'))tapeExpand(false)}
function tapeExport(){
  const events=tapeVisible();
  if(!events.length){toast('No confirmed trade events in the selected period to export.');return}
  const csv=['symbol,provider_timestamp_utc,unix_ms,price,volume,locally_received_utc,source',...events.map(x=>[
    T.symbol,new Date(x.t).toISOString(),x.t,x.p,x.v,x.receivedAt?new Date(x.receivedAt).toISOString():'',
    'Finnhub WebSocket observed trade'].join(','))].join('\r\n')+'\r\n';
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='MarketDesk-LiveTape-'+T.symbol+'-'+new Date().toISOString().slice(0,10)+'.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function tapeRenderMetrics(events){
  const n=events.length,first=events[0],last=events[n-1];
  const isCurrent=!T.review&&!T.pause&&last&&E.wsOpen&&E.subscribed.has(T.symbol)&&nowMs()-last.receivedAt<180000&&nowMs()-last.t<300000;
  $('tape-metric-price').textContent=last?tapePrice(T.symbol,last.p):'—';
  $('tape-metric-price-note').textContent=last?(isCurrent?'VERIFIED STREAM TRADE · ':'RECORDED, NOT CURRENT · ')+elapsed(last.t):'No captured trade in window';
  const pct=n>=2&&first.p>0?(last.p/first.p-1)*100:null;
  $('tape-metric-move').textContent=pct===null?'—':fmtPct(pct);
  $('tape-metric-move').className='tape-metric-value '+(pct===null?'':signClass(pct));
  $('tape-metric-move-note').textContent=n>=2?'Change between the first and last recorded trade, not the whole trading day':'Needs at least two recorded trades';
  $('tape-metric-count').textContent=n?tapeNum(n):'0';
  let size=0,notional=0;
  for(const e of events){size+=e.v;notional+=e.v*e.p}
  $('tape-metric-volume').textContent=n?tapeNum(size):'0';
  $('tape-metric-vwap').textContent=size>0?'Captured-trade VWAP: '+tapePrice(T.symbol,notional/size):'Captured-trade VWAP: —';
  $('tape-symbol-title').textContent=T.symbol;
  $('tape-symbol-name').textContent=safeName(T.symbol);
  $('tape-last-source').textContent=!last?'NO OBSERVED TRADE':isCurrent?'VERIFIED LIVE TRADE':'RECORDED · NOT LIVE';
  $('tape-last-source').className='tape-source '+(isCurrent?'good':'');
  $('tape-last-time').textContent=last?'Latest in view: '+tapeFullTime(last.t):'No confirmed trade in selected period';
  $('tape-point-count').textContent=n+' captured trade'+(n===1?'':'s')+(T.events.length>=4000?' · sample may be capped':'');
}
function tapeRenderTrades(events){
  const body=$('tape-trades-body');
  if(!events.length){body.innerHTML=`<tr><td colspan="5" class="tape-empty-row">No recorded Finnhub trades within ${escapeHtml(T.range.toUpperCase())}. Keep Market Desk open during the trading session to collect real observations.</td></tr>`;$('tape-record-count').textContent='0';return}
  const matching=[];
  for(let index=events.length-1;index>=0&&matching.length<75;index--){
    if(events[index].v>=T.minSize)matching.push(index);
  }
  $('tape-record-count').textContent=tapeNum(events.filter(e=>e.v>=T.minSize).length);
  if(!matching.length){body.innerHTML='<tr><td colspan="5" class="tape-empty-row">No trades meet this size filter.</td></tr>';return;}
  body.innerHTML=matching.map(index=>{
    const e=events[index],prior=events[index-1];
    const delta=prior?e.p-prior.p:null;
    return `<tr><td class="tape-mono"><span>${tapeTimeMs(e.t)}</span><small>${new Date(e.t).toLocaleDateString('en-GB',{day:'2-digit',month:'short'})}</small></td><td class="tape-mono tape-table-price">${escapeHtml(tapePrice(T.symbol,e.p))}</td><td class="tape-mono">${tapeNum(e.v)}</td><td class="tape-mono ${delta===null?'':signClass(delta)}">${delta===null?'—':(delta>0?'+':'')+delta.toFixed(3)}</td><td><span class="tape-executed">● TRADE</span></td></tr>`
  }).join('');
}
function tapeRenderRadar(force=false){
  const filter=String($('tape-symbol-filter').value||'').trim().toUpperCase();
  const ms=nowMs();
  if(!force&&ms-T.lastRadarRender<3000&&filter===T.lastRadarFilter)return;
  T.lastRadarRender=ms;T.lastRadarFilter=filter;
  const scroll=$('tape-symbol-list').scrollTop;
  const items=E.watch.filter(s=>!filter||s.includes(filter)||safeName(s).toUpperCase().includes(filter));
  $('tape-symbol-count').textContent=E.watch.length+' TRACKED';
  $('tape-symbol-list').innerHTML=items.length?items.map(sym=>{
    const s=tapeSymbolIndicators(sym),q=s.quote;
    return `<button class="tape-symbol-row ${sym===T.symbol?'selected':''}" data-tape-symbol="${escapeHtml(sym)}" aria-pressed="${sym===T.symbol}" title="${escapeHtml(s.market.detail)}"><span class="tape-symbol-identity"><strong>${escapeHtml(sym)}</strong><small>${escapeHtml(safeName(sym))}</small>${tapeSessionPill(s)}</span><span class="tape-symbol-value"><b>${q?escapeHtml(tapePrice(sym,q.p)):'—'}</b><small class="${q?signClass(q.change):''}">${q?fmtPct(q.change):'NO PRICE'}</small>${tapeFeedPill(s)}</span></button>`;
  }).join(''):'<p class="tape-muted">No matching symbols on your watchlist.</p>';
  $('tape-symbol-list').scrollTop=scroll;
}
function tapeRenderMarquee(){
  const selected=E.watch.slice(0,12),symbols=selected.join('|');
  const shell=$('tape-marquee');
  if(symbols!==T.lastMarqueeSymbols){
    T.lastMarqueeSymbols=symbols;
    const content=selected.map(sym=>`<div class="tape-mq-item" data-mq="${escapeHtml(sym)}"><strong>${escapeHtml(sym)}</strong><span class="mq-price">—</span><b class="mq-pct">—</b><i class="mq-type">NO DATA</i></div>`).join('');
    shell.innerHTML=`<div class="tape-mq-set">${content}</div><div class="tape-mq-set" aria-hidden="true">${content}</div>`;
  }
  shell.querySelectorAll('[data-mq]').forEach(item=>{
    const sym=item.dataset.mq,q=quoteFor(sym);
    const p=item.querySelector('.mq-price'),pct=item.querySelector('.mq-pct'),typ=item.querySelector('.mq-type');
    p.textContent=q?tapePrice(sym,q.p):'—';pct.textContent=q?fmtPct(q.change):'—';pct.className='mq-pct '+(q?signClass(q.change):'');
    typ.textContent=q?(q.type==='live'?'LIVE TRADE':q.type==='stale'?'STALE QUOTE':'QUOTE'):'NO DATA';typ.className='mq-type '+(q?.type==='live'?'mq-live':'');
  });
}
function tapeRenderHealth(){
  const latest=E.trades.get(T.symbol),quote=E.quotes.get(T.symbol);
  const live=E.wsOpen&&E.subscribed.has(T.symbol)&&latest&&nowMs()-latest.receivedAt<180000&&nowMs()-latest.t<300000;
  $('tape-feed-pill').textContent=live?'● VERIFIED TRADE STREAM':E.wsOpen?'● CONNECTED / AWAITING TRADE':'● STREAM NOT CONNECTED';
  $('tape-feed-pill').className='tape-feed-pill '+(live?'tape-pill-live':E.wsOpen?'tape-pill-idle':'tape-pill-offline');
  $('tape-health-dot').className='tape-health-dot '+(live?'healthy':E.wsOpen?'idle':'offline');
  $('tape-ws-status').textContent=E.wsOpen?'CONNECTED · TRANSPORT ONLY':E.wsError||'DISCONNECTED';
  $('tape-health-trade').textContent=latest?(live?'LIVE TRADE · ':'LAST OBSERVED · ')+tapeTime(latest.t):'NONE CONFIRMED';
  $('tape-quote-status').textContent=quote?.quote?((nowMs()-quote.quote.t*1000>900000?'STALE REST QUOTE':'REST QUOTE')+' · '+elapsed(quote.quote.t*1000)):'NO QUOTE';
  $('tape-event-age').textContent=latest?elapsed(latest.t):'—';
  const latency=latest?latest.receivedAt-latest.t:null;
  $('tape-latency').textContent=latency!==null&&latency>=0?Math.round(latency)+' ms · approximate':'—';
  $('tape-connection-help').textContent=T.lastError||(live?'A Finnhub trade with a size above zero has arrived. Your feed may cover only markets included in your plan.':E.wsOpen?'Transport open. No qualifying recent trade for this symbol; a quote or zero-volume update is not proof of an execution.':'The live feed is not connected. Price quotes and saved trades keep their labels.');
}
function tapeRender(){
  if(!T.setup||E.view!=='tape'||T.pause)return;
  const events=tapeVisible();
  tapeRenderMetrics(events);tapeRenderTrades(events);tapeRenderRadar();tapeRenderMarquee();tapeRenderHealth();tapeDraw(events);
}
function tapeDraw(events=null){
  if(!T.setup||E.view!=='tape')return;
  const canvas=$('tape-canvas'),box=canvas.getBoundingClientRect();
  if(box.width<40||box.height<80)return;
  const {start,end,width:duration}=tapeWindow();
  const all=events||tapeVisible();
  const points=tapeSort(all).slice(-4000);
  const candleWidth=T.chartStyle==='1m'?60000:T.chartStyle==='5m'?300000:0;
  const note=$('tape-chart-no-data');
  note.classList.toggle('hidden',points.length>0);
  const alternate=quoteFor(T.symbol);
  note.textContent=points.length===1?'One trade recorded. A second trade is needed before drawing a line.':
    'No confirmed trades were recorded during this period. No price trend is made up.'+
    (alternate?.type!=='live'&&alternate?.p?' Latest Finnhub '+(alternate.stale?'stale quote':'quote snapshot')+': '+tapePrice(T.symbol,alternate.p)+' at '+fmtDateTime(alternate.t)+'.':'');
  const dpr=Math.min(window.devicePixelRatio||1,2);
  const w=box.width,h=box.height;
  const pxW=Math.max(1,Math.round(w*dpr)),pxH=Math.max(1,Math.round(h*dpr));
  if(canvas.width!==pxW)canvas.width=pxW;
  if(canvas.height!==pxH)canvas.height=pxH;
  const ctx=canvas.getContext('2d');if(!ctx)return;
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const left=18,right=w-73,top=21,bottom=h-33,volumeTop=h-105,priceBottom=h-122;
  const x=t=>left+((t-start)/duration)*(right-left);
  const allPrices=points.map(p=>p.p);
  let min=points.length?Math.min(...allPrices):0,max=points.length?Math.max(...allPrices):1;
  const margin=Math.max((max-min)*.18,max*.0005,.005);
  min-=margin;max+=margin;
  const y=p=>top+(max-p)/(max-min)*(priceBottom-top);
  ctx.font='11px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif';
  ctx.lineWidth=1;
  for(let i=0;i<=4;i++){
    const yy=top+(priceBottom-top)*i/4;
    ctx.strokeStyle='rgba(115,139,160,.15)';ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();
    if(points.length){ctx.fillStyle='#7f94a5';ctx.textAlign='right';ctx.fillText((max-i*(max-min)/4).toFixed(2),w-8,yy+4)}
  }
  for(let i=0;i<=4;i++){
    const xx=left+(right-left)*i/4;
    ctx.strokeStyle='rgba(115,139,160,.10)';ctx.beginPath();ctx.moveTo(xx,top);ctx.lineTo(xx,bottom);ctx.stroke();
    ctx.fillStyle='#74889a';ctx.textAlign='center';ctx.fillText(tapeTime(start+i*duration/4).slice(0,5),xx,h-10)
  }
  ctx.strokeStyle='#253443';ctx.beginPath();ctx.moveTo(left,volumeTop-10);ctx.lineTo(right,volumeTop-10);ctx.stroke();
  if(!points.length){
    // An actual quote can provide context, but a single observation is NOT a chart.
    // No synthetic trend, fabricated trading volume or arbitrary price scale.
    const last=quoteFor(T.symbol);
    if(last&&last.type!=='live'){
      ctx.textAlign='center';ctx.fillStyle='#d5b97b';ctx.font='700 23px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif';
      ctx.fillText(tapePrice(T.symbol,last.p),w/2,(top+priceBottom)/2-3);
      ctx.fillStyle='#9da9b2';ctx.font='11px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif';
      ctx.fillText(last.stale?'OLD FINNHUB PRICE QUOTE · NOT A LIVE TRADE':'FINNHUB PRICE QUOTE · NO RECORDED TRADES',w/2,(top+priceBottom)/2+23);
    }
  }
  if(points.length){
    const bins=Math.max(10,Math.min(72,Math.floor((right-left)/12)));
    const buckets=Array(bins).fill(0);
    for(const e of points){const i=Math.min(bins-1,Math.max(0,Math.floor((e.t-start)/duration*bins)));buckets[i]+=e.v}
    const maxV=Math.max(...buckets,1);
    const bw=(right-left)/bins;
    ctx.fillStyle='rgba(114,229,181,.28)';
    for(let i=0;i<bins;i++){
      const bh=buckets[i]/maxV*(bottom-volumeTop-7);
      if(bh>0)ctx.fillRect(left+i*bw+.6,bottom-bh,Math.max(1,bw-1.3),bh)
    }
    if(points.length>=2){
      const rising=points[points.length-1].p>=points[0].p;
      const color=rising?'#7aafff':'#ff8b9d';
      const grad=ctx.createLinearGradient(0,top,0,priceBottom);
      grad.addColorStop(0,rising?'rgba(97,235,164,.22)':'rgba(255,130,150,.18)');grad.addColorStop(1,'rgba(12,21,29,0)');
      if(candleWidth){
        const bodyWidth=Math.max(1,Math.min(12,(right-left)*candleWidth/duration*.62));
        for(const candle of tapeCandles(points,candleWidth)){
          const xx=x((candle.first+candle.last)/2);
          ctx.strokeStyle=ctx.fillStyle=candle.close>=candle.open?'#72e5b5':'#ff8b9d';
          ctx.lineWidth=1.3;ctx.beginPath();ctx.moveTo(xx,y(candle.high));ctx.lineTo(xx,y(candle.low));ctx.stroke();
          const openY=y(candle.open),closeY=y(candle.close);
          ctx.fillRect(xx-bodyWidth/2,Math.min(openY,closeY),bodyWidth,Math.max(1,Math.abs(openY-closeY)));
        }
      }else{
        const segments=tapeSegments(points,Math.max(10000,Math.min(300000,duration/20)));
        for(const segment of segments){
          if(segment.length===1){
            const p=segment[0];ctx.fillStyle=color;ctx.beginPath();ctx.arc(x(p.t),y(p.p),2,0,2*Math.PI);ctx.fill();continue;
          }
          ctx.beginPath();ctx.moveTo(x(segment[0].t),priceBottom);
          for(const p of segment)ctx.lineTo(x(p.t),y(p.p));
          ctx.lineTo(x(segment.at(-1).t),priceBottom);ctx.closePath();ctx.fillStyle=grad;ctx.fill();
          ctx.beginPath();segment.forEach((p,i)=>i?ctx.lineTo(x(p.t),y(p.p)):ctx.moveTo(x(p.t),y(p.p)));
          ctx.strokeStyle=color;ctx.lineWidth=2;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
        }
      }
      const last=points[points.length-1];
      ctx.fillStyle=color;ctx.beginPath();ctx.arc(x(last.t),y(last.p),3.3,0,2*Math.PI);ctx.fill();
    }
    if(points.length===1){const p=points[0];ctx.fillStyle='#7aafff';ctx.beginPath();ctx.arc(x(p.t),y(p.p),3,0,2*Math.PI);ctx.fill();}
    if(T.hoverX!==null){
      const xx=Math.max(left,Math.min(right,T.hoverX)),tGuess=start+(xx-left)/(right-left)*duration;
      let low=0,high=points.length-1;
      while(low<high){const mid=(low+high)>>1;if(points[mid].t<tGuess)low=mid+1;else high=mid}
      const i=low&&Math.abs(points[low-1].t-tGuess)<Math.abs(points[low].t-tGuess)?low-1:low;
      const pt=points[i],px=x(pt.t),py=y(pt.p);
      ctx.setLineDash([4,4]);ctx.strokeStyle='rgba(202,220,233,.55)';ctx.beginPath();ctx.moveTo(px,top);ctx.lineTo(px,bottom);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#d1fa79';ctx.beginPath();ctx.arc(px,py,4.4,0,Math.PI*2);ctx.fill();
      const tooltip=$('tape-canvas-tooltip');tooltip.textContent=tapePrice(T.symbol,pt.p)+' · '+tapeTimeMs(pt.t)+' · size '+tapeNum(pt.v);
      tooltip.classList.remove('hidden');tooltip.style.left=Math.max(2,Math.min(w-220,px+10))+'px';tooltip.style.top=Math.max(5,py-49)+'px';
    }else $('tape-canvas-tooltip').classList.add('hidden');
  }else $('tape-canvas-tooltip').classList.add('hidden');
  T.chartLayout={left,right,start,end,width:w};
}
function tapeSetup(){
  if(T.setup)return;
  T.setup=true;
  const selected=savedJSON('md-tape-symbol','AAPL');
  T.symbol=typeof selected==='string'&&tapeCanOpen(selected)?selected:(E.watch.includes('AAPL')?'AAPL':E.watch[0]||'AAPL');
  $('tape-timezone').textContent='CHART TIME · '+(Intl.DateTimeFormat().resolvedOptions().timeZone||'LOCAL');
  $('tape-reconnect').addEventListener('click',()=>{if(!E.configured){changeView('settings');return}connectWS();toast('Finnhub WebSocket reconnect requested. Wait for a verified trade before calling it live.')});
  $('tape-export').addEventListener('click',tapeExport);
  $('tape-review').addEventListener('click',()=>tapeLoadReview());
  $('tape-date').addEventListener('change',event=>tapeLoadReview(event.target.value));
  $('tape-return-live').addEventListener('click',()=>tapeToggleFollow(true));
  $('tape-seek').addEventListener('input',event=>tapeSeek(Number(event.target.value)));
  $('tape-chart-style').addEventListener('change',event=>{
    T.chartStyle=event.target.value;tapeDraw();
  });
  $('tape-min-size').addEventListener('input',event=>{
    const value=Number(event.target.value);
    T.minSize=Number.isFinite(value)?Math.max(0,value):0;tapeRenderTrades(tapeVisible());
  });
  $('tape-follow').addEventListener('click',()=>tapeToggleFollow());
  $('tape-pause').addEventListener('click',tapeTogglePause);
  $('tape-chart-expand').addEventListener('click',()=>tapeExpand());
  $('tape-chart-reset').addEventListener('click',()=>{tapeToggleFollow(true);tapeSetRange('1h')});
  $('tape-zoom-in').addEventListener('click',()=>tapeZoom(-1));
  $('tape-zoom-out').addEventListener('click',()=>tapeZoom(1));
  $('tape-refresh').addEventListener('click',tapeReload);
  $('tape-symbol-filter').addEventListener('input',()=>tapeRenderRadar(true));
  $('tape-prev').addEventListener('click',()=>tapeQuickStep(-1));
  $('tape-next').addEventListener('click',()=>tapeQuickStep(1));
  $('tape-add-stock').addEventListener('click',()=>{changeView('markets');$('symbol-search').focus()});
  $('tape-shortcuts').addEventListener('click',e=>{const el=e.target.closest('[data-tape-symbol]');if(el)tapeSelect(el.dataset.tapeSymbol)});
  $('tape-quick-search').addEventListener('input',tapeSearchSchedule);
  $('tape-quick-search').addEventListener('focus',()=>tapeSearchSchedule());
  $('tape-quick-search').addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();tapeCloseSuggestions(true);return}
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();tapeSearchMove(e.key==='ArrowDown'?1:-1);return;
    }
    if(e.key==='Enter'){
      if(!tapeSearchOpen())return;
      e.preventDefault();
      const match=T.searchResults[T.searchActive>=0?T.searchActive:0];
      if(match)tapeChooseSuggestion(match.sym,match.name);
    }
    if(e.key==='Tab')tapeCloseSuggestions();
  });
  $('tape-quick-results').addEventListener('click',e=>{
    const el=e.target.closest('[data-tape-suggest]');
    if(el)tapeChooseSuggestion(el.dataset.tapeSuggest,el.dataset.tapeName);
  });
  document.addEventListener('click',e=>{
    if(!e.target.closest('.tape-search-wrap'))tapeCloseSuggestions();
  });
  document.addEventListener('keydown',e=>{
    if(E.view!=='tape'||e.altKey||e.ctrlKey||e.metaKey)return;
    const tag=e.target?.tagName||'',typing=['INPUT','TEXTAREA','SELECT'].includes(tag)||e.target?.isContentEditable;
    if(!typing&&e.key==='/'){e.preventDefault();$('tape-quick-search').focus()}
    if(!typing&&e.key==='ArrowLeft'){e.preventDefault();tapeQuickStep(-1)}
    if(!typing&&e.key==='ArrowRight'){e.preventDefault();tapeQuickStep(1)}
  });
  $('tape-symbol-list').addEventListener('click',e=>{
    const el=e.target.closest('[data-tape-symbol]');if(!el)return;
    tapeSelect(el.dataset.tapeSymbol);saveJSON('md-tape-symbol',T.symbol);
  });
  document.querySelectorAll('[data-tape-range]').forEach(b=>b.addEventListener('click',()=>tapeSetRange(b.dataset.tapeRange)));
  const canvas=$('tape-canvas');
  canvas.addEventListener('pointermove',e=>{T.hoverX=e.clientX-canvas.getBoundingClientRect().left;if(!T.hoverFrame)T.hoverFrame=requestAnimationFrame(()=>{T.hoverFrame=0;tapeDraw()})});
  canvas.addEventListener('pointerleave',()=>{T.hoverX=null;if(!T.hoverFrame)T.hoverFrame=requestAnimationFrame(()=>{T.hoverFrame=0;tapeDraw()})});
  canvas.addEventListener('pointerdown',e=>{if(T.pause||(e.pointerType==='mouse'&&e.button!==0))return;T.dragStart={x:e.clientX,anchor:tapeWindow().end};canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointerup',e=>{if(!T.dragStart||!T.chartLayout)return;
    const dx=e.clientX-T.dragStart.x;
    if(Math.abs(dx)>8){
      const duration=TAPE_RANGES[T.range],pixels=Math.max(1,T.chartLayout.right-T.chartLayout.left);
      const want=T.dragStart.anchor-dx/pixels*duration;
      if(T.review){
        const ratio=Math.max(0,Math.min(1,(want-T.review.first)/Math.max(1,T.review.last-T.review.first)));
        $('tape-seek').value=String(Math.round(ratio*1000));
        tapeSeek(ratio*1000);
      }else{
        T.anchor=Math.min(nowMs(),Math.max(nowMs()-86400000+duration,want));
        tapeToggleFollow(false);
      }
    }T.dragStart=null;
  });
  canvas.addEventListener('wheel',e=>{
    // Wheel zoom is available only with the control/command modifier to protect page scrolling.
    if(!(e.ctrlKey||e.metaKey))return;
    e.preventDefault();tapeZoom(e.deltaY<0?-1:1);
  },{passive:false});
  if(typeof ResizeObserver!=='undefined')new ResizeObserver(()=>{if(E.view==='tape')tapeDraw()}).observe($('tape-chart-panel'));
  window.addEventListener('resize',()=>{if(E.view==='tape')tapeDraw()});
  setInterval(()=>{if(E.view==='tape'&&!T.pause){tapeRenderHealth();tapeRenderSwitcher();if(T.follow)tapeRender();}},3000);
  tapeRenderMarquee();tapeRenderRadar();tapeRenderHealth();tapeRenderSwitcher(true);
}
