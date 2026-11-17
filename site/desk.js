/* Market Desk v2.7. Original overview: saved evidence, simple wording and visible limits. */
const DeskMath=(()=>{
 'use strict';const DAY=86400000,finite=x=>typeof x==='number'&&Number.isFinite(x),positive=x=>finite(x)&&x>0&&x<=1e9;
 function quote(row,now=Date.now()){
  const t=row?.quoteTime;
  if(!positive(row?.price)||!positive(row?.previousClose)||!finite(t)||t<946684800000||t>now)return {usable:false,reason:'Needs a valid price, previous close and source date'};
  if(now-t>3*DAY)return {usable:false,reason:'Quote is more than 3 days old'};
  return {usable:true,t,price:row.price,change:(row.price/row.previousClose-1)*100,old:now-t>15*60000};
 }
 function briefing(rows,now=Date.now()){
  const available=rows.map(row=>({row,...quote(row,now)})).filter(x=>x.usable),up=available.filter(x=>x.change>0),down=available.filter(x=>x.change<0);
  return {total:rows.length,available:available.length,up:up.length,down:down.length,flat:available.length-up.length-down.length,missing:rows.length-available.length,
   older:available.filter(x=>x.old).length,rise:up.sort((a,b)=>b.change-a.change)[0]||null,fall:down.sort((a,b)=>a.change-b.change)[0]||null};
 }
 function rangeState(range,info={},massive=false,finnhub=false,now=Date.now()){
  const days={'1W':7,'1M':30,'3M':90,'6M':183,'1Y':365,'2Y':730,'5Y':1826,'10Y':3653}[range];
  if(range==='1H'||range==='1D')return {label:info.intraday?.count>1?'Local records':'Recordings needed',detail:'Only timestamped observations recorded while this Mac was running. Gaps stay visible.'};
  const source=info.imported||info.daily,imported=Boolean(info.imported),start=now-days*DAY;
  const intersects=source?.count>1&&finite(source.first)&&finite(source.last)&&source.first<=now&&source.last>=start;
  if(intersects){
   if(source.last<now-10*DAY)return {label:imported?'Old file':'Old saved data',detail:'The last saved daily price is more than 10 days old. Check the actual dates before comparing.'};
   if(source.first>start+14*DAY)return {label:imported?'Partial file':'Partial saved data',detail:'The saved series starts after this range begins. Earlier prices are missing; source-date coverage does not guarantee every trading day.'+(!imported&&days>730?' Import a longer daily-price file for a full '+range+' series.':'')};
   return {label:imported?'Saved file':'Saved daily data',detail:'Saved prices reach this range’s start and recent end. Internal gaps may remain; check the plotted dates.'};
  }
  if(imported)return {label:'File outside range',detail:'The imported file has no usable pair of dates in this period. Replace it or choose another range.'};
  if(days>730)return {label:massive||!finnhub?'Import needed':'Check access / import',detail:'Free Massive history reaches about 2 years. A full '+range+' series needs a longer imported file or historical access on your Finnhub plan.'};
  return {label:massive?'Can load daily data':finnhub?'Check plan access':'Connect or import',detail:massive?'Request daily history within the existing free-plan window. Opening a chart or selecting a period may request daily history through the provider cache.':finnhub?'Daily history depends on your Finnhub plan. If access is unavailable, import a suitable daily-price file.':'Add a historical data connection in Settings, or import a suitable daily-price file.'};
 }
 function headlines(items,now=Date.now(),limit=6){
  const seen=new Set();return (Array.isArray(items)?items:[]).filter(x=>{
   const ts=x?.datetime*1000;let u;try{u=new URL(x?.url)}catch{return false}
   if(!['http:','https:'].includes(u.protocol)||u.username||u.password||!x.headline||!x.source||!finite(ts)||ts>now||ts<now-7*DAY||seen.has(u.href))return false;
   seen.add(u.href);return true;
  }).sort((a,b)=>b.datetime-a.datetime).slice(0,limit);
 }
 function companyHeadlines(items,symbol,name,now=Date.now()){
  const terms=[name,...(symbol==='TTWO'?['Take-Two','Take Two','Rockstar','GTA VI','GTA 6']:[])].filter(x=>typeof x==='string'&&x.length>=3).map(x=>x.toLowerCase());
  return headlines(items,now,36).filter(x=>{const title=x.headline.toLowerCase();const token=String(symbol).toUpperCase();const ticker=x.headline.split(/[^A-Za-z0-9.:-]+/).includes(token);return ticker||terms.some(term=>title.includes(term));}).slice(0,6);
 }
 return {quote,briefing,rangeState,headlines,companyHeadlines};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=DeskMath;
/* Assign to window.Desk (not a bare const) so terminal/app can resolve during boot
   without hitting a temporal-dead-zone ReferenceError while setup() runs. */
window.Desk=(()=>{
 'use strict';if(typeof document==='undefined')return {};
 const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),DAY=86400000;
 const NOTES={
  AAPL:'Apple makes devices such as iPhone and Mac, develops their software and sells digital services.',
  NVDA:'NVIDIA designs graphics processors and computing platforms used in gaming, data centres and artificial intelligence.',
  MSFT:'Microsoft develops software and provides cloud computing, business tools and gaming products.',
  GOOGL:'Alphabet is the parent company of Google, whose businesses include search, advertising, YouTube and cloud services.',
  AMZN:'Amazon operates online retail and marketplace services, alongside cloud computing through Amazon Web Services.',
  META:'Meta operates social and messaging services including Facebook, Instagram and WhatsApp.',
  TSLA:'Tesla makes electric vehicles and develops energy storage and related products.',
  AMD:'AMD designs processors and graphics chips used in computers, gaming systems and data centres.',
  PLTR:'Palantir develops software that helps organisations work with and analyse data.',
  JPM:'JPMorgan Chase provides banking, investment and other financial services.',
  KO:'The Coca-Cola Company owns and markets beverage brands, with products distributed through its bottling system.',
  DIS:'Disney operates entertainment businesses including films, television, streaming services and theme parks.',
  NFLX:'Netflix provides a streaming service and produces and licenses entertainment.',
  BA:'Boeing designs and makes commercial aircraft, defence products and space systems.',
  TSM:'Taiwan Semiconductor Manufacturing Company makes semiconductor chips for other companies.',
  TTWO:'Take-Two Interactive publishes video games through businesses including Rockstar Games and 2K. Rockstar is part of Take-Two; it does not have its own separately listed stock.'
 };
 let mode='briefing',data=null,ready=false,sequence=0,busy=false,lastLoad=0,request=null,pickerKey='',watchKey='',watchLoadedKey='',lastRenderKey='',refreshAttempts=new Map();
 const date=t=>typeof t==='number'&&Number.isFinite(t)&&t>0?new Date(t).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}):'Not available';
 const time=t=>typeof t==='number'&&Number.isFinite(t)&&t>0?new Date(t).toLocaleString('en-GB',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}):'Not available';
 const signed=n=>(n>0?'+':'')+n.toFixed(2)+'%',tone=n=>n>0?'desk-up':n<0?'desk-down':'desk-flat';
 const currency=r=>r.listingCurrency||'',money=(r,n)=>Number.isFinite(n)?n.toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})+(currency(r)?' '+currency(r):' · currency unreported'):'Not available';
 function safeScroll(node){if(!node)return;const reduced=document.body.dataset.motion==='off'||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;node.scrollIntoView({block:'start',behavior:reduced?'instant':'smooth'});}
 function rows(){
  const saved=new Map((data?.rows||[]).map(r=>[r.symbol,r]));
  return (E.watch||[]).map(sym=>{
   let row={symbol:sym,name:typeof safeName==='function'?safeName(sym):sym,listingCurrency:typeof DIRECTORY_BY_SYMBOL!=='undefined'?DIRECTORY_BY_SYMBOL[sym]?.currency:'',...saved.get(sym)};
   const q=E.quotes.get(sym)?.quote;
   if(q&&q.t*1000>=(row.quoteTime||0))row={...row,price:q.c,previousClose:q.pc,quoteTime:q.t*1000};
   return row;
  });
 }
 function imported(sym){return data?.imports?.items?.find(x=>x.symbol===sym)||null;}
 function historyInfo(sym){
  const result={...(data?.history?.[sym]||{}),imported:imported(sym)};if(result.daily)result.daily={...result.daily,provider:'massive'};
  const hist=E.candles.get(sym),pts=hist?.points;
  if(hist?.status==='ok'&&pts?.length>1){const ext={first:pts[0].t,last:pts.at(-1).t,count:pts.length};if(hist.provider==='imported')result.imported={...hist,...result.imported,...ext,splitAdjusted:hist.split_adjusted,importedAt:hist.imported_at};else if(hist.provider==='massive'&&result.daily?.count)result.daily={first:Math.min(result.daily.first,ext.first),last:Math.max(result.daily.last,ext.last),count:Math.max(result.daily.count,ext.count),provider:'massive'};else result.daily={...ext,provider:hist.provider};}
  return result;
 }
 function renderRanges(){
  if(!ready)return;const info=historyInfo(E.selected),now=Date.now();
  document.querySelectorAll('#overview-ranges button').forEach(button=>{
   let caption=button.querySelector('.desk-range-caption');if(!caption){caption=document.createElement('span');caption.className='desk-range-caption';button.appendChild(caption)}
   const state=DeskMath.rangeState(button.dataset.range,info,E.massiveConfigured,E.configured,now);caption.textContent=state.label;button.title=state.detail;button.setAttribute('aria-describedby','desk-range-hint');
  });
  const current=DeskMath.rangeState(E.range,info,E.massiveConfigured,E.configured,now);
  $('desk-range-hint').textContent=E.savedSession?E.range+' · Last saved session ending '+time(E.chartDomain.to)+'. Older recorded prices, not the current hour or day.':E.range+' · '+current.label+'. '+current.detail;
  if(E.heatmapWindow)$('desk-range-hint').textContent='Heatmap · '+E.heatmapWindow.label+' · '+E.heatmapWindow.start+' → '+E.heatmapWindow.end+'. Completed-session closing prices. Choose a chart range above to leave this comparison.';
  if(E.sessionReplay)$('desk-range-hint').textContent='Massive minute history · '+E.sessionReplay.day+' New York date. Choose a range to return to the recorded chart.';
  const quote=typeof quoteFor==='function'?quoteFor(E.selected):null;
  $('desk-quote-date').textContent=quote?'Price above: latest recorded '+(quote.type==='live'?'stream trade':'quote')+' · '+time(quote.t)+'. This is separate from the past-price line.':'The large price above needs a valid quote. Historical prices, when available, remain separate below.';
  $('desk-import-target').textContent='Importing for '+(E.selected||'no selected stock')+' · '+(typeof safeName==='function'?safeName(E.selected):'')+'. This replaces only this stock’s imported file.';
 }
 function renderPicker(){
  const choices=companyChoices(),key=JSON.stringify(choices.map(s=>[s,safeName(s)]));if(key!==pickerKey){pickerKey=key;$('desk-stock-select').replaceChildren();for(const sym of choices){const option=document.createElement('option');option.value=sym;option.textContent=sym+' · '+safeName(sym);$('desk-stock-select').appendChild(option)}}
  $('desk-stock-select').value=E.selected;$('desk-stock-select').disabled=!choices.length;
 }
 function renderBrief(all,now){
  const b=DeskMath.briefing(all,now);
  $('desk-brief-title').textContent=b.available?`${b.up} rising. ${b.down} falling. ${b.flat} unchanged.`:b.total?'Your briefing is waiting for prices.':'Your next idea starts with a company.';
  $('desk-brief-sub').textContent=b.total?`${b.available} of ${b.total} watched stocks have a usable comparison. ${b.missing} ${b.missing===1?'needs':'need'} newer or more complete data. ${b.older} usable quotes are over 15 minutes old.`:'Add companies in Stock Browser to create your own briefing.';
  $('desk-brief-story').innerHTML=`<div><span class="desk-eyebrow">YOUR WATCHLIST / AVAILABLE QUOTES</span><strong>${b.available}<small> / ${b.total}</small></strong><p>Prices with a valid previous close and quote date.</p></div><div class="desk-story-note"><span class="desk-mini-dot" aria-hidden="true"></span><p>${b.older?'Some quotes are older. Read the time on each card before comparing.':'Each card shows its provider quote time.'} Counts describe this watchlist only.</p></div>`;
  $('desk-movers').innerHTML=[['Largest available rise',b.rise,'↑'],['Largest available fall',b.fall,'↓']].map(([label,item,arrow])=>item?`<button type="button" class="desk-mover ${tone(item.change)}" data-desk-stock="${esc(item.row.symbol)}"><span>${label}</span><strong>${esc(item.row.name)} <i>${arrow}</i></strong><b>${signed(item.change)}</b><small>${esc(item.row.symbol)} · quote ${esc(time(item.t))}${item.old?' · older quote':''}</small></button>`:`<div class="desk-mover"><span>${label}</span><strong>No ${arrow==='↑'?'rise':'fall'} to show</strong><p>No matching usable quote in this watchlist.</p></div>`).join('');
  // Avoid replacing a keyboard-focused watch card when nothing relevant changed.
  const key=JSON.stringify(all.map(r=>[r.symbol,r.name,r.price,r.previousClose,r.quoteTime,DeskMath.quote(r,now).old]));
  if(key!==watchKey){watchKey=key;const active=$('desk-watch').contains(document.activeElement)?document.activeElement?.dataset?.deskStock:null;
   $('desk-watch').innerHTML=all.map(r=>{const q=DeskMath.quote(r,now);return `<button type="button" class="desk-watch-card" data-desk-stock="${esc(r.symbol)}"><span class="desk-watch-symbol">${esc(r.symbol)} <i aria-hidden="true">↗</i></span><strong>${esc(r.name)}</strong><b class="${q.usable?tone(q.change):''}">${q.usable?signed(q.change):'Needs data'}</b><small>${q.usable?esc(money(r,q.price))+' · vs previous close':esc(q.reason)}</small><small>${r.quoteTime?'Quote '+esc(time(r.quoteTime)): 'No quote saved'}${q.old?' · older quote':''}</small></button>`}).join('')||'<div class="desk-empty"><h3>Your watchlist is empty.</h3><p>Choose Manage watchlist to add your first company.</p></div>';
   if(active){const button=[...$('desk-watch').querySelectorAll('[data-desk-stock]')].find(x=>x.dataset.deskStock===active);button?.focus({preventScroll:true})}
  }
 }
 function renderHeadlines(target,scope,label){
  const source=data?.news?.[scope],items=scope==='general'?DeskMath.headlines(source?.items||[]):DeskMath.companyHeadlines(source?.items||[],scope,safeName(scope)),node=$(target);
  node.innerHTML=items.length?items.map(item=>`<article class="desk-headline"><p>${esc(item.source)} <span>· published ${esc(time(item.datetime*1000))}</span></p><h3><a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.headline)} <span aria-hidden="true">↗</span></a></h3><small>Publisher’s report · read the original article for context.</small></article>`).join(''):`<div class="desk-empty"><h3>${scope==='general'?'No recent linked headlines saved.':'No recent company-title matches saved.'}</h3><p>${scope==='general'?'Refresh the briefing':'Choose Update this company & news'} to request headlines. Provider access and availability can vary.</p></div>`;
  $(label).textContent=source?.fetchedAt?'Finnhub headline list retrieved '+time(source.fetchedAt)+'. '+(scope==='general'?'Showing linked reports published within the past seven days.':'Showing company-name or ticker title matches from the past seven days; relevant reports may be missed.'):'No saved headline retrieval date. Nothing has been inferred from the chart.';
 }
 function renderCompany(all){
  const sym=E.selected,row=all.find(x=>x.symbol===sym)||data?.rows?.find(x=>x.symbol===sym)||DIRECTORY_BY_SYMBOL[sym],profile=data?.profiles?.[sym],p=profile?.data||{},name=row?.name||safeName(sym)||'Choose a company';
  $('desk-company-symbol').textContent=sym?sym+' / COMPANY OVERVIEW':'YOUR SELECTED COMPANY';$('desk-company-name').textContent=name;$('desk-company-mark').textContent=sym?sym.slice(0,2):'↗';
  $('desk-company-about').textContent=!sym?'Add a company to your watchlist to start exploring.':NOTES[sym]||(p.finnhubIndustry?name+' is listed by Finnhub in the '+p.finnhubIndustry+' industry. A detailed business description is not saved.':name+' is available to explore. A business description is not saved yet. Open full company research or update its details.');
  $('desk-company-description-source').textContent=NOTES[sym]?'Directory description · written for Market Desk. General background, not an explanation of a price move.':p.finnhubIndustry?'Based on Finnhub’s saved industry field · retrieved '+time(profile.fetchedAt)+'.':'Missing company descriptions are left open rather than generated.';
  $('desk-company-details').innerHTML=`<dl class="desk-company-fields">${[['Stock symbol',sym],['Listing currency',row?.listingCurrency],['Exchange',p.exchange||row?.exchange],['Provider industry',p.finnhubIndustry],['Profile retrieved',profile?.fetchedAt?time(profile.fetchedAt):null]].map(([label,value])=>`<div><dt>${label}</dt><dd>${esc(value||'Not saved')}</dd></div>`).join('')}</dl><p class="desk-source">Profile retrieval is not a financial reporting date. Full company research retains the original financial figures and source notes.</p>`;
  $('desk-refresh-company').disabled=busy||!sym;renderHeadlines('desk-company-headlines',sym,'desk-company-news-date');renderHistory();
 }
 function renderHistory(){
  const sym=E.selected,info=historyInfo(sym),file=info.imported,items=data?.imports?.items||[],d=info.daily;
  $('desk-history-selected').textContent=(sym||'No stock selected')+' · '+(file?'Daily chart source: your imported file. Provider bars remain separate.':'Daily chart source: provider history, when available.');
  $('desk-history-sources').innerHTML=`<div class="desk-saved-source"><strong>${file?'Imported daily prices':'Saved provider daily prices'}</strong><p>${file?`${esc(file.source||'User-provided file')} · ${file.count} prices · ${date(file.first)} – ${date(file.last)} · ${file.splitAdjusted?'marked split-adjusted':'not split-adjusted; splits can cause jumps'}`:d?.count?`${d.count} saved ${d.provider==='finnhub'?'Finnhub':'Massive'} daily bars · ${date(d.first)} – ${date(d.last)}. Other Finnhub daily bars may be held temporarily in the browser.`:'No Massive daily bars saved for this stock. You can request provider history by selecting a range, or add a daily-price file.'}</p>${file?`<small>Imported ${time(file.importedAt)} · not independently verified.</small>`:''}</div>`;
  $('desk-download-import').disabled=!file;$('desk-open-import').disabled=!sym;
  $('desk-import-library').innerHTML=items.length?items.map(x=>`<article class="desk-import-row"><div><strong>${esc(x.symbol)}</strong><p>${esc(x.source)} · ${x.count} prices · ${date(x.first)} – ${date(x.last)}</p><small>${x.splitAdjusted?'Marked split-adjusted':'Unadjusted; splits may cause jumps'} · imported ${time(x.importedAt)}</small></div><button type="button" class="ghost-btn" data-desk-import="${esc(x.symbol)}">${x.symbol===sym?'Review selected file':'Review file ↗'}</button></article>`).join('')+(data.imports.total>items.length?'<p>Showing the 200 most recently stored files. Select a stock to access its source.</p>':''):'<p class="desk-source">No imported files are saved. Your original provider records are available separately.</p>';
 }
 function memory(){
  if(!ready||typeof E==='undefined')return;
  const symbols=browseSymbols().join(',');if(symbols!==watchLoadedKey){watchLoadedKey=symbols;Promise.resolve().then(()=>reload(true));}
  renderPicker();renderRanges();if($('desk-follow')){$('desk-follow').textContent=E.watch.includes(E.selected)?'Following this company':'Follow this company';$('desk-follow').disabled=!E.selected||E.watch.includes(E.selected);}
  const all=rows(),key=JSON.stringify([all,E.selected,E.configured,Math.floor(Date.now()/60000),data?.asOf]);
  if(key===lastRenderKey)return;lastRenderKey=key;renderBrief(all,Date.now());renderCompany(all);renderHeadlines('desk-headlines','general','desk-news-date');
 }
 async function reload(force=false){
  if(!ready)return;if(request&&!force)return request;
  const symbols=browseSymbols().join(','),id=++sequence;lastLoad=Date.now();
  let task;task=(async()=>{try{if(typeof api!=='function'){if(id===sequence)$('desk-status').textContent='Waiting for Market Desk API…';return}const r=await api('/api/desk?symbols='+encodeURIComponent(symbols));if(id!==sequence||symbols!==browseSymbols().join(','))return;data=r;
    for(const row of r.rows||[]){if(!browseSymbols().includes(row.symbol)||!Number.isFinite(row.price)||row.price<=0||row.price>1e9||!Number.isInteger(row.quoteTime)||row.quoteTime<946684800000||row.quoteTime>Date.now())continue;const t=row.quoteTime/1000;if(!Number.isInteger(t)||(E.quotes.get(row.symbol)?.quote?.t||0)>=t)continue;E.quotes.set(row.symbol,{symbol:row.symbol,quote:{c:row.price,pc:row.previousClose,t},cached:true,source:'Finnhub saved quote snapshot',receivedAt:row.quoteFetchedAt});}
    lastRenderKey='';memory();renderAll();if(!busy)$('desk-status').textContent='Saved data checked '+time(r.asOf)+'. Source dates stay visible on each card.';}catch(error){if(id===sequence)$('desk-status').textContent='Saved briefing data could not be read: '+error.message;}finally{if(request===task)request=null}})();request=task;return task;
 }
 function setMode(next){
  if(!['briefing','stock','advanced'].includes(next))return;
  if($('main-chart-panel')?.classList.contains('is-expanded'))toggleExpandedChart(false);
  mode=next;document.body.dataset.deskMode=next;$('desk-page-title').innerHTML=next==='briefing'?'A little context.<br><span>A clearer picture.</span>':next==='stock'?'Your company.<span> In focus.</span>':'Your detailed workspace.';$('desk-briefing').hidden=next!=='briefing';$('desk-stock').hidden=next!=='stock';$('desk-legacy').hidden=next!=='advanced';
  document.querySelectorAll('[data-desk-mode]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.deskMode===next)));
  window.dispatchEvent(new CustomEvent('marketdesk:edition-change',{detail:{edition:document.body.dataset.edition}}));
  memory();requestAnimationFrame(()=>{if(next!=='briefing')drawChart()});
 }
 function selected(){if(!ready)return;if(mode!=='advanced')setMode('stock');reload();if(E.configured&&Date.now()-(refreshAttempts.get(E.selected)||0)>600000)Promise.resolve().then(()=>refresh('company'));}
 function open(){if(!ready)return;memory();reload();}
 function historyChanged(){if(!ready)return;renderRanges();renderHistory();}
 function chartMount(){return mode==='advanced'?null:$('desk-chart-mount');}
 function adoptQuotes(items){
  for(const item of items||[]){const sym=item.symbol,q=item.quote;if(!browseSymbols().includes(sym)||!q||!Number.isFinite(q.c)||q.c<=0||q.c>1e9||!Number.isInteger(q.t)||q.t<946684800||q.t*1000>Date.now()+60000)continue;
   if((E.quotes.get(sym)?.quote?.t||0)>q.t)continue;E.quotes.set(sym,{...item,receivedAt:Date.now()});E.quoteFailures.delete(sym);E.quoteChecks.set(sym,{busy:false,checkedAt:Date.now(),cached:Boolean(item.cached)});E.lastGoodQuoteAt=Date.now();
  }
 }
 async function refresh(modeName){
  if(busy)return;if(!E.configured){$('desk-status').textContent='Add your Finnhub connection in Settings to request prices and news. Saved history can still be viewed.';return}
  const all=rows(),chosen=modeName==='company'?[E.selected]:all.slice().sort((a,b)=>Math.max(a.quoteFetchedAt||0,refreshAttempts.get(a.symbol)||0)-Math.max(b.quoteFetchedAt||0,refreshAttempts.get(b.symbol)||0)).slice(0,8).map(r=>r.symbol);
  if(!chosen.length){$('desk-status').textContent='Add a company to your watchlist first.';return}
  busy=true;$('desk-refresh-brief').disabled=true;$('desk-refresh-company').disabled=true;chosen.forEach(sym=>refreshAttempts.set(sym,Date.now()));$('desk-status').textContent='Requesting '+chosen.join(', ')+(modeName==='company'?' details and company news…':' prices and market headlines…');
  try{const result=await post('/api/desk/refresh',{mode:modeName,symbols:chosen});adoptQuotes(result.quotes);await reload(true);$('desk-status').textContent=result.warnings?.length?'Some data could not be updated: '+[...new Set(result.warnings)].slice(0,2).join(' · '):'Requested '+chosen.length+' stock'+(chosen.length===1?'':'s')+'. Check source dates; cached or older data may be returned.';renderAll();if(modeName==='company'&&E.selected===chosen[0])loadChart(false);}catch(error){$('desk-status').textContent='Update unavailable: '+error.message;}finally{busy=false;$('desk-refresh-brief').disabled=false;$('desk-refresh-company').disabled=!E.selected;}
 }
 async function downloadImport(){
  const sym=E.selected;try{const result=await api('/api/imported-history?symbol='+encodeURIComponent(sym));if(result.status!=='ok')throw Error('No imported prices saved for '+sym);
   const heading=result.price_column?.toLowerCase().includes('adj')?'Adj Close':'Close';const csv=['Date,'+heading+',Symbol',...result.points.map(x=>`${new Date(x.t).toISOString().slice(0,10)},${x.p},${sym}`)].join('\r\n');
   const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='MarketDesk-'+sym+'-imported-daily-prices.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('desk-status').textContent='Downloaded the imported daily prices for '+sym+'. Keep your original source and adjustment notes too.';
  }catch(error){$('desk-status').textContent=error.message;}
 }
 function showImport(){setMode('stock');$('history-import-panel').open=true;safeScroll($('history-import-panel'));$('history-import-file').focus({preventScroll:true});}
 function setup(){
  if(!$('desk-start'))return;ready=true;document.body.classList.add('desk-v27');$('desk-today').textContent=new Date().toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  document.querySelectorAll('[data-desk-mode]').forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.deskMode)));
  const follow=document.createElement('button');follow.id='desk-follow';follow.className='ghost-btn';follow.type='button';follow.textContent='Follow this company';follow.addEventListener('click',()=>{addStock(E.selected,safeName(E.selected));memory()});$('desk-refresh-company').after(follow);
  $('desk-stock-select').addEventListener('change',event=>openStock(event.target.value));
  $('desk-refresh-brief').addEventListener('click',()=>refresh('briefing'));$('desk-refresh-company').addEventListener('click',()=>refresh('company'));
  $('desk-open-heat').addEventListener('click',()=>changeView('heatmap'));$('desk-manage-watch').addEventListener('click',()=>{changeView('markets');switchMarketsTab('watch')});$('desk-all-news').addEventListener('click',()=>changeView('news'));
  $('desk-history-link').addEventListener('click',()=>{$('desk-history-manager').open=true;safeScroll($('desk-history-manager'))});$('desk-open-import').addEventListener('click',showImport);$('desk-download-import').addEventListener('click',downloadImport);
  $('view-overview').addEventListener('click',event=>{
   const stock=event.target.closest('[data-desk-stock]');if(stock){openStock(stock.dataset.deskStock);return}
   const file=event.target.closest('[data-desk-import]');if(file){const sym=file.dataset.deskImport;openStock(sym);$('desk-history-manager').open=true;safeScroll($('desk-history-manager'));}
  });
  setMode('stock');reload();setInterval(()=>{if(document.visibilityState==='visible'&&E.view==='overview'){if(Date.now()-lastLoad>25000)reload();else memory()}},10000);
 }
 // Defer setup until after window.Desk is assigned — setMode dispatches edition-change,
 // and terminal.js moveChart must see a finished Desk (not a TDZ / missing binding).
 const api={open,memory,selected,reload,historyChanged,chartMount,revealSelected:()=>safeScroll(mode==='advanced'?$('main-chart-panel'):$('desk-company-name'))};
 const boot=()=>{if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();};
 queueMicrotask(boot);
 return api;
})();
