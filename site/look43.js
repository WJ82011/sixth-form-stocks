/* Dashboard frame matched to the V4.3 layout studies. Prices and events stay real. */
const Look43=window.Look43=(()=>{
  let bars=[],barsSymbol='',heat='1D',series=localStorage.getItem('md-look-series')||'line';
  const money=(sym,value)=>typeof fmtUnit==='function'?fmtUnit(sym,value):Number(value).toFixed(2);
  const pct=value=>Number.isFinite(value)?`${value>=0?'+':''}${value.toFixed(2)}%`:'—';
  function changeFor(symbol){
    const quote=typeof quoteFor==='function'?quoteFor(symbol):null;
    if(quote&&Number.isFinite(quote.change))return quote.change;
    const raw=E.quotes?.get(symbol)?.quote;
    if(raw&&Number(raw.pc)>0&&Number(raw.c)>0)return (Number(raw.c)-Number(raw.pc))/Number(raw.pc)*100;
    return null;
  }
  const spark=points=>{
    const values=(points||[]).map(point=>Number(point.p??point)).filter(Number.isFinite);
    if(values.length<2)return '';
    const min=Math.min(...values),max=Math.max(...values),span=max-min||1;
    const path=values.map((value,index)=>`${index?'L':'M'}${(index/(values.length-1)*72).toFixed(1)} ${(22-(value-min)/span*18).toFixed(1)}`).join(' ');
    return `<svg viewBox="0 0 72 24" aria-hidden="true"><path d="${path}"/></svg>`;
  };
  function ensure(){
    if(!document.body.classList.contains('look43-on'))document.body.classList.add('look43-on');
    const briefing=document.getElementById('v3-home');
    if(briefing&&!briefing.closest('.look43-briefing')){
      const details=document.createElement('details');
      details.className='look43-briefing';
      details.innerHTML='<summary>Saved briefing</summary>';
      briefing.before(details);
      details.append(briefing);
    }
    if(!document.getElementById('look43-rail')){
      const rail=document.createElement('nav');
      rail.id='look43-rail';rail.className='look43-rail';rail.setAttribute('aria-label','Main destinations');
      rail.innerHTML=`<button type="button" data-view="home" aria-label="My Desk">${icon('home')}</button><button type="button" data-view="markets" aria-label="Explore">${icon('markets')}</button><button type="button" data-view="company" aria-label="Investigate">${icon('company')}</button><button type="button" data-view="research" aria-label="My Research">${icon('tools')}</button><button type="button" data-view="settings" aria-label="Settings">${icon('settings')}</button><button type="button" data-look-tools aria-label="All tools" aria-haspopup="dialog">${icon('heat')}</button>`;
      document.body.append(rail);
      rail.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>changeView(button.dataset.view)));
      rail.querySelector('[data-look-tools]')?.addEventListener('click',()=>document.getElementById('focus-tools')?.click());
    }
    if(!document.getElementById('look43-top')){
      const top=document.createElement('header');
      top.id='look43-top';top.className='look43-top';
      top.innerHTML=`<a href="#" id="look43-brand"><strong>Market Desk</strong></a><form id="look43-search" role="search"><input id="look43-query" placeholder="Search symbol" aria-label="Search symbol" autocomplete="off"></form><div class="look43-top-actions"><span id="look43-feed">Checking saved prices</span><div id="look43-mode" role="group" aria-label="Standard or Professional mode"><button type="button" data-v43-edition="standard">Standard</button><button type="button" data-v43-edition="professional">Professional</button></div></div>`;
      document.body.append(top);
      top.querySelector('#look43-search').addEventListener('submit',event=>{
        event.preventDefault();
        const query=event.target.querySelector('input').value.trim();
        const symbol=resolveSymbol(query);
        const note=document.getElementById('look43-feed');
        if(!symbol){if(note)note.textContent='No directory company matches that search.';const box=document.getElementById('directory-search');if(box)box.value=query;changeView('markets');return}
        setSelected(symbol);changeView('home');paint();
      });
      top.querySelector('#look43-mode').addEventListener('click',event=>{
        const button=event.target.closest('[data-v43-edition]');
        if(button&&window.Desk43)Desk43.apply(button.dataset.v43Edition==='professional'?'professional':'signal');
      });
    }
    const home=document.getElementById('home43');
    if(home&&!document.getElementById('look43-board')){
      const panel=document.getElementById('main-chart-panel');
      if(panel)document.body.append(panel);
      home.innerHTML=`<details id="desk50-visit" class="look43-card"><summary>Since your last visit</summary><div id="desk50-visit-body">Checking saved records…</div></details><details id="overnight51-report" class="look43-card"><summary>Overnight research</summary><div id="overnight51-body">Checking the job log…</div></details><div id="look43-board"><section class="look43-chartcard"><div id="look43-head"></div><div class="look43-tools" id="look43-tools"></div><div id="home43-chart"></div><p id="look43-coverage"></p><p id="desk50-status"></p></section><aside class="look43-side"><section class="look43-card"><header><h2>Watchlist</h2><button type="button" data-view="markets" aria-label="Edit watchlist">···</button></header><div id="look43-watch"></div></section><section class="look43-card"><header><h2>Company events</h2><button type="button" data-view="company" aria-label="Open company events">···</button></header><div id="look43-events"></div></section></aside><section class="look43-card look43-heat" id="look43-heat"></section><section class="look43-card look43-tape" id="look43-tape"></section></div>`;
      if(panel)document.getElementById('home43-chart').append(panel);
      window.Workspace60?.mount();
      window.Annotate60?.mount();
      home.addEventListener('click',event=>{
        const view=event.target.closest('[data-view]');
        if(view){
          if(view.getAttribute('aria-label')==='Open company events'){changeView('company');window.Shell43?.companyTab('events');return}
          changeView(view.dataset.view);return
        }
        const stock=event.target.closest('[data-select]');
        if(stock){event.stopPropagation();setSelected(stock.dataset.select);if(stock.dataset.moveStart&&stock.dataset.moveEnd&&window.Move44)Move44.open({symbol:stock.dataset.select,start:stock.dataset.moveStart,end:stock.dataset.moveEnd});paint();return}
        const range=event.target.closest('[data-look-range]');
        if(range){if(window.Chart43?.backToLive)Chart43.backToLive();if(typeof setChartRange==='function')setChartRange(range.dataset.lookRange);paint();return}
        const style=event.target.closest('[data-look-series]');
        if(style){series=style.dataset.lookSeries;try{localStorage.setItem('md-look-series',series)}catch{}paint();if(typeof drawChart==='function')drawChart();return}
        const sector=event.target.closest('[data-look-sector]');
        if(sector){heat=sector.dataset.lookSector;paintHeat();return}
        const next=event.target.closest('[data-desk68]');
        if(next&&window.Desk68){Desk68.go(next.dataset.desk68);return}
        if(event.target.closest('#look43-ask')&&window.Ask48){Ask48.openFrom({symbol:E.selected,range:E.range,area:'chart'});return}
        if(event.target.closest('#look43-reset')&&window.Chart43)Chart43.reset();
      });
    }
  }
  function icon(name){
    const paths={home:'M4 11 12 4l8 7v9H4z',markets:'M4 16V8M10 16V5M16 16v-6M22 16V3',company:'M6 4h12v16H6zM9 8h6M9 12h6',tape:'M4 7h16M4 12h16M4 17h10',heat:'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 3v3M12 18v3M3 12h3M18 12h3',tools:'M4 6h16M4 12h16M4 18h16',pulse:'M3 12h4l2-5 4 10 2-5h6'};
    return `<svg viewBox="0 0 24 24">${name==='pulse'?'<path d="'+paths.pulse+'"/>':'<path d="'+paths[name]+'"/>'}</svg>`;
  }
  function candleBars(from,to){
    const professional=document.body.dataset.edition==='professional';
    if(window.Replay43?.active||barsSymbol!==E.selected||['1H','1D'].includes(E.range))return null;
    if(!professional&&series!=='candles')return null;
    const shown=bars.filter(bar=>bar.t>=from&&bar.t<=to&&Number.isFinite(bar.o)&&Number.isFinite(bar.h)&&Number.isFinite(bar.l)&&Number.isFinite(bar.c));
    return shown.length?shown:null;
  }
  async function loadCandles(){
    if(typeof E==='undefined'||!E.selected||typeof api!=='function')return;
    const symbol=E.selected,end=Math.floor(Date.now()/1000),start=end-86400*420;
    try{
      const data=await api('/api/saved-daily?symbol='+encodeURIComponent(symbol)+'&from='+start+'&to='+end);
      if(symbol!==E.selected)return;
      const candles=data.candles;
      bars=candles?.t?candles.t.map((stamp,index)=>({t:stamp*1000,o:candles.o[index],h:candles.h[index],l:candles.l[index],c:candles.c[index],v:candles.v[index]})).filter(bar=>[bar.o,bar.h,bar.l,bar.c].every(Number.isFinite)):[];
      barsSymbol=symbol;
      if(typeof drawChart==='function')drawChart();
    }catch{if(symbol===E.selected){bars=[];barsSymbol=''}}
  }
  function paint(){
    ensure();
    if(typeof E==='undefined')return;
    const professional=document.body.dataset.edition==='professional';
    document.body.dataset.look=professional?'professional':'standard';
    const quote=typeof quoteFor==='function'?quoteFor(E.selected):null;
    const name=E.names?.[E.selected]||E.selected||'Choose a stock';
    const price=quote?money(E.selected,quote.p):'No saved price';
    const move=pct(changeFor(E.selected));
    const up=Number(changeFor(E.selected))>=0;
    const head=document.getElementById('look43-head');
    if(!head)return;
    head.innerHTML=professional?`<div><strong>${escapeHtml(E.selected||'')}</strong><span>${escapeHtml(name)}</span></div><div><b>${escapeHtml(price)}</b><em class="${up?'up':'down'}">${escapeHtml(move)}</em></div><span class="look43-saved">${E.savedSession?'Saved session':'Recorded prices'}</span>`:`<div><h2>${escapeHtml(name)}</h2><span class="look43-pill">${escapeHtml(E.selected||'')}</span></div><div class="look43-price"><b>${escapeHtml(price)}</b><em class="${up?'up':'down'}">${escapeHtml(move)}</em></div><span class="look43-saved">${E.savedSession?'Saved session':'Recorded prices'}</span>`;
    const ranges=professional?['1H','1D','1W','1M']:['1H','1D','1W','1M','3M','1Y'];
    const toolbar=document.getElementById('look43-tools');
    if(toolbar.dataset.edition!==document.body.dataset.look+'-68'){
      toolbar.dataset.edition=document.body.dataset.look+'-68';
      toolbar.innerHTML=`${professional?'':`<div class="look43-series"><button type="button" data-look-series="line" aria-pressed="${series!=='candles'}">Line</button><button type="button" data-look-series="candles" aria-pressed="${series==='candles'}">Candles</button></div>`}<div class="look43-ranges">${ranges.map(range=>`<button type="button" data-look-range="${range}" aria-pressed="${E.range===range}">${range}</button>`).join('')}</div><button type="button" id="look43-ask">Ask Intelligence</button><button type="button" id="look43-reset">Reset</button><button type="button" data-journal="chart">Save evidence</button><button type="button" data-desk68="move">Investigate this move</button><button type="button" data-desk68="compare">Compare a company</button><button type="button" data-desk68="financials">Supported financials</button>`;
    }
    toolbar.querySelectorAll('[data-look-series]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lookSeries===series)));
    toolbar.querySelectorAll('[data-look-range]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lookRange===E.range)));
    const note=document.getElementById('overview-chart-note')?.textContent||document.getElementById('chart-data-coverage')?.textContent||'';
    const brief=document.getElementById('chart-observed-summary')?.textContent||'';
    const forecast=document.getElementById('chart-forecast-legend')?.textContent||'';
    const coverage=document.getElementById('look43-coverage');
    coverage.replaceChildren();
    const summary=document.createElement('p');
    summary.textContent=(brief.split('·')[0]||note.split('.')[0]||'Checking saved prices').trim();
    const detail=document.createElement('details');
    const label=document.createElement('summary');
    label.textContent='Coverage and forecast detail';
    const more=document.createElement('p');
    more.textContent=[brief,forecast,note].filter(Boolean).join(' ');
    detail.append(label,more);
    coverage.append(summary,detail);
    const observed=E.verifiedAt?new Date(E.verifiedAt).toLocaleTimeString('en-GB',{hour12:false})+' last recorded trade':'No trade recorded this session';
    document.getElementById('look43-feed').textContent=(['1H','1D'].includes(E.range)?observed+' · collector '+(E.backgroundCollector?'on':'off'):'Daily chart uses saved closes · '+observed);
    document.querySelectorAll('#look43-mode [data-v43-edition]').forEach(button=>button.setAttribute('aria-pressed',String((professional?'professional':'standard')===button.dataset.v43Edition)));
    const active=(document.querySelector('.view.active')?.id||'').replace('view-','');
    const area={home:'home',overview:'home',alerts:'home',portfolio:'home',tape:'home',markets:'markets',heatmap:'markets',crypto:'markets',screener:'markets',comparison:'markets',indicators:'markets',news:'markets',macro:'markets',company:'company',calendar:'company',forecast:'company',accuracy:'company',valuation:'company',intelligence:'company',research:'research',reports:'research',learning:'research',settings:'settings'};
    document.querySelectorAll('#look43-rail [data-view]').forEach(button=>{if(button.dataset.view===(area[active]||active))button.setAttribute('aria-current','page');else button.removeAttribute('aria-current')});
    const symbols=(E.watch||[]).slice(0,professional?6:4);
    document.getElementById('look43-watch').innerHTML=professional?`<table><thead><tr><th>Symbol</th><th>Price</th><th>Change</th></tr></thead><tbody>${symbols.map(symbol=>{const row=quoteFor(symbol);const change=changeFor(symbol);return `<tr data-select="${escapeHtml(symbol)}"><td>${escapeHtml(symbol)}</td><td>${row?escapeHtml(money(symbol,row.p)):'—'}</td><td class="${Number(change)>=0?'up':'down'}">${escapeHtml(pct(change))}</td></tr>`}).join('')}</tbody></table>`:symbols.map(symbol=>{const row=quoteFor(symbol);const change=changeFor(symbol);return `<button type="button" data-select="${escapeHtml(symbol)}" aria-pressed="${symbol===E.selected}"><span><strong>${escapeHtml(symbol)}</strong><small>${escapeHtml(E.names?.[symbol]||symbol)}</small></span><i data-spark="${escapeHtml(symbol)}"></i><b>${row?escapeHtml(money(symbol,row.p)):'—'}</b><em class="${Number(change)>=0?'up':'down'}">${escapeHtml(pct(change))}</em></button>`}).join('')||'<p>Your watchlist is empty.</p>';
    document.getElementById('look43-heat').hidden=professional;
    document.getElementById('look43-tape').hidden=!professional;
  }
  async function paintEvents(){
    const box=document.getElementById('look43-events');
    if(!box||typeof E==='undefined'||!E.selected)return;
    const symbol=E.selected;
    try{
      const data=await api('/api/v3/events42?symbol='+encodeURIComponent(symbol));
      if(symbol!==E.selected)return;
      const events=(data.events||[]).slice(0,document.body.dataset.edition==='professional'?2:3);
      box.innerHTML=events.length?events.map(event=>`<article><span>${escapeHtml(event.symbol||symbol)}</span><strong>${escapeHtml(event.title)}</strong><small>${escapeHtml(event.timeLabel||'Timing unknown')}${event.kindLabel?' · '+escapeHtml(event.kindLabel):''}</small>${event.reason?`<small>${escapeHtml(event.reason)}</small>`:''}</article>`).join(''):'<p>No saved events for this company.</p>';
    }catch(error){if(symbol===E.selected)box.innerHTML='<p>'+escapeHtml(error.message)+'</p>'}
  }
  async function paintHeat(){
    const box=document.getElementById('look43-heat');
    if(!box||box.hidden||typeof E==='undefined')return;
    const sectors=['All sectors','Technology','Consumer','Health Care','Financials','Communication'];
    try{
      const data=await api('/api/v3/heatmap?period=1D&symbols='+encodeURIComponent((E.watch||[]).join(',')));
      const rows=(data.rows||[]).filter(row=>(E.watch||[]).includes(row.symbol)&&Number.isFinite(row.change));
      const groups=new Map();
      for(const row of rows){const name=row.category||'Other';if(!groups.has(name))groups.set(name,[]);groups.get(name).push(row)}
      const chosen=heat==='1D'||heat==='All sectors'?null:heat;
      const tiles=chosen&&groups.has(chosen)?groups.get(chosen).slice(0,7).map(row=>({name:row.symbol,change:row.change,points:row.points,start:row.start,end:row.end})):[...groups].map(([name,list])=>({name,change:list.reduce((sum,row)=>sum+row.change,0)/list.length,points:list[0]?.points})).slice(0,7);
      box.innerHTML=`<header><h2>Market heatmap</h2><div>${['All sectors',...[...groups.keys()].slice(0,5)].map(name=>`<button type="button" data-look-sector="${escapeHtml(name)}" aria-pressed="${(chosen||'All sectors')===name}">${escapeHtml(name)}</button>`).join('')}</div></header><div class="look43-tiles">${tiles.map(tile=>`<button type="button" class="${tile.change>=0?'up':'down'}" ${tile.name.length<=5?'data-select="'+escapeHtml(tile.name)+'"':''} ${tile.start&&tile.end?'data-move-start="'+escapeHtml(tile.start)+'" data-move-end="'+escapeHtml(tile.end)+'"':''}><strong>${escapeHtml(tile.name)}</strong><b>${escapeHtml(pct(tile.change))}</b></button>`).join('')||'<p>No saved daily moves for the watchlist yet.</p>'}</div>`;
      for(const row of rows){const slot=document.querySelector(`[data-spark="${row.symbol}"]`);if(slot&&row.points)slot.innerHTML=spark(row.points)}
    }catch(error){box.innerHTML='<header><h2>Market heatmap</h2></header><p>'+escapeHtml(error.message)+'</p>'}
  }
  async function paintTape(){
    const box=document.getElementById('look43-tape');
    if(!box||box.hidden||typeof E==='undefined'||!E.selected)return;
    const symbol=E.selected;
    try{
      const data=await api('/api/tape?symbol='+encodeURIComponent(symbol)+'&last=1&limit=8');
      if(symbol!==E.selected)return;
      const cursor=window.Replay43?.active?Replay43.cursor:Infinity;
      const events=(data.events||[]).filter(event=>Number(event.t)<=cursor).slice(-4).reverse();
      box.innerHTML=`<header><h2>Live Tape</h2><span>${escapeHtml(symbol)}</span></header><table><thead><tr><th>Time</th><th>Price</th><th>Size</th></tr></thead><tbody>${events.map(event=>{const price=Number(event.p);return `<tr><td>${escapeHtml(new Date(event.t).toLocaleTimeString('en-GB',{hour12:false}))}</td><td>${escapeHtml(money(symbol,price))}</td><td>${escapeHtml(String(event.v??'—'))}</td></tr>`}).join('')||'<tr><td colspan="3">No saved trades for this company yet.</td></tr>'}</tbody></table><p>Saved trades already on this Mac. Replay hides anything after the replay clock.</p>`;
    }catch(error){if(symbol===E.selected)box.innerHTML='<header><h2>Live Tape</h2></header><p>'+escapeHtml(error.message)+'</p>'}
  }
  function resolveSymbol(query){
    const text=String(query||'').trim();
    if(!text||typeof STOCK_DIRECTORY==='undefined')return '';
    const upper=text.toUpperCase();
    if(DIRECTORY_BY_SYMBOL[upper]||(E.watch||[]).includes(upper))return upper;
    const exact=STOCK_DIRECTORY.find(row=>row.name.toUpperCase()===upper);
    if(exact)return exact.symbol;
    const matches=STOCK_DIRECTORY.filter(row=>row.name.toUpperCase().includes(upper)||row.listingName.toUpperCase().includes(upper));
    return matches.length===1?matches[0].symbol:'';
  }
  let paintKey='',eventsKey='',heatKey='',tapeKey='';
  function refresh(){
    if(typeof E==='undefined')return;
    const price=typeof quoteFor==='function'?quoteFor(E.selected)?.p:'';
    const key=[E.selected,E.range,document.body.dataset.edition,E.savedSession,(E.watch||[]).join(','),price,E.chartPoints?.length,E.chartPoints?.at?.(-1)?.t,document.getElementById('chart-forecast-legend')?.textContent?.slice(0,48)].join('|');
    if(key!==paintKey){paintKey=key;paint()}
    if(E.selected!==eventsKey){eventsKey=E.selected||'';paintEvents();loadCandles()}
    if((document.body.dataset.edition||'')+'|'+(E?.watch||[]).join(',')!==heatKey){heatKey=(document.body.dataset.edition||'')+'|'+(E?.watch||[]).join(',');paintHeat()}
    if((document.body.dataset.edition||'')+'|'+E?.selected!==tapeKey){tapeKey=(document.body.dataset.edition||'')+'|'+E?.selected;paintTape()}
  }
  document.addEventListener('DOMContentLoaded',()=>{ensure();refresh();setInterval(()=>{if(document.visibilityState==='visible')refresh()},4000)});
  window.addEventListener('marketdesk:edition-change',()=>setTimeout(refresh,0));
  return {candleBars,refresh};
})();
