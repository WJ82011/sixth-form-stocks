/* Dashboard frame matched to the V4.3 layout studies. Prices and events stay real. */
const Look43=window.Look43=(()=>{
  let bars=[],barsSymbol='',barsSource='',heat='1D',series=localStorage.getItem('md-look-series')||'line',controlsBound=false,loadingSymbol='';
  const money=(sym,value)=>typeof fmtUnit==='function'?fmtUnit(sym,value):Number(value).toFixed(2);
  const pct=value=>Number.isFinite(value)?`${value>=0?'+':''}${value.toFixed(2)}%`:'—';
  const notice=(text)=>{const feed=document.getElementById('look43-feed');if(feed&&text)feed.textContent=text;if(typeof toast==='function'&&text)toast(text)};
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
  function wantsCandles(){
    return series==='candles'||document.body.dataset.edition==='professional';
  }
  function dailyRangeForCandles(){
    if(!['1H','1D'].includes(E.range))return false;
    if(typeof setChartRange==='function')setChartRange('1M');
    else{
      E.range='1M';
      document.querySelectorAll('#overview-ranges button').forEach(button=>button.classList.toggle('active',button.dataset.range==='1M'));
      if(typeof loadChart==='function')loadChart();
    }
    return true;
  }
  function parseBars(candles){
    if(!candles?.t?.length)return [];
    return candles.t.map((stamp,index)=>({
      t:Number(stamp)<1e12?Number(stamp)*1000:Number(stamp),
      o:Number(candles.o?.[index]),
      h:Number(candles.h?.[index]),
      l:Number(candles.l?.[index]),
      c:Number(candles.c?.[index]),
      v:Number(candles.v?.[index]),
    })).filter(bar=>[bar.o,bar.h,bar.l,bar.c].every(Number.isFinite));
  }
  async function loadCandles(force=false){
    if(typeof E==='undefined'||!E.selected||typeof api!=='function')return;
    const symbol=E.selected;
    if(!force&&barsSymbol===symbol&&bars.length)return;
    if(loadingSymbol===symbol&&!force)return;
    loadingSymbol=symbol;
    try{
      if(window.MarketDeskHost?.whenSnapshotReady)await window.MarketDeskHost.whenSnapshotReady();
      if(symbol!==E.selected)return;
      const end=Math.floor(Date.now()/1000),start=end-86400*420;
      const query='?symbol='+encodeURIComponent(symbol)+'&resolution=D&from='+start+'&to='+end;
      let data=null;
      try{data=await api('/api/saved-daily'+query)}catch{/* Prefer saved/snapshot bars; fall through to /api/candles. */}
      if(data?.status!=='ok'||!data?.candles?.t?.length){
        try{data=await api('/api/candles'+query)}catch(error){
          if(symbol===E.selected&&!bars.length){
            bars=[];barsSymbol='';barsSource='';
            if(wantsCandles())notice('OHLC bars unavailable · '+error.message);
          }
          return;
        }
      }
      if(symbol!==E.selected)return;
      const next=parseBars(data?.candles);
      bars=next;
      barsSymbol=next.length?symbol:'';
      barsSource=data?.source||data?.notice||(next.length?'Daily OHLC bars':'');
      if(typeof drawChart==='function')drawChart();
      if(wantsCandles()&&!next.length)notice('No OHLC bars for '+symbol+' in the snapshot or API.');
      else if(wantsCandles()&&next.length&&(E.demoMode||window.MarketDeskHost?.demoMode)&&barsSource){
        const feed=document.getElementById('look43-feed');
        if(feed)feed.textContent='Candles · '+(barsSource.includes('DEMO')||barsSource.includes('demo')||barsSource.includes('Portfolio')?barsSource:'bundled daily OHLC');
      }
    }finally{if(loadingSymbol===symbol)loadingSymbol=''}
  }
  function applySeries(next){
    series=next==='candles'?'candles':'line';
    try{localStorage.setItem('md-look-series',series)}catch{}
    syncSeriesButtons();
    if(series==='candles'){
      const bumped=dailyRangeForCandles();
      const loading=loadCandles(true).then(()=>{paint();if(!bumped&&typeof drawChart==='function')drawChart()});
      if(!bumped){paint();if(typeof drawChart==='function')drawChart()}
      return loading;
    }
    paint();
    if(typeof drawChart==='function')drawChart();
    return Promise.resolve();
  }
  function applyRange(range){
    if(window.Chart43?.backToLive)Chart43.backToLive();
    if(typeof setChartRange==='function')setChartRange(range);
    if(wantsCandles()&&['1H','1D'].includes(range)){
      const feed=document.getElementById('look43-feed');
      if(feed)feed.textContent='Candles need a daily range (1W+) · showing the line for '+range+'.';
    }else if(wantsCandles())loadCandles();
    paint();
  }
  function openAsk(){
    if(window.Ask48?.openFrom){Ask48.openFrom({symbol:E.selected,range:E.range,area:'chart'});return}
    if(typeof changeView==='function')changeView('intelligence');
    notice('Intelligence opened · Ask panel loads when available.');
  }
  function resetView(){
    if(window.Chart43?.reset){Chart43.reset();return}
    if(typeof drawChart==='function')drawChart();
  }
  function deskAction(action){
    if(window.Desk68?.go){Desk68.go(action);return}
    const map={move:'company',compare:'comparison',financials:'company'};
    if(typeof changeView==='function')changeView(map[action]||'company');
    notice('Opened '+(map[action]||'company')+' · full desk helpers need the loaded modules.');
  }
  function applyEdition(next){
    const edition=next==='professional'?'professional':'signal';
    if(window.Desk43?.apply)Desk43.apply(edition);
    else{
      document.body.dataset.edition=edition;
      window.dispatchEvent(new CustomEvent('marketdesk:edition-change',{detail:{edition}}));
    }
    if(edition==='professional'&&['1H','1D'].includes(E.range))dailyRangeForCandles();
    loadCandles(true);
    paint();
  }
  function onControlClick(event){
    const style=event.target.closest('[data-look-series]');
    if(style){event.preventDefault();event.stopPropagation();applySeries(style.dataset.lookSeries);return true}
    const range=event.target.closest('[data-look-range]');
    if(range){event.preventDefault();event.stopPropagation();applyRange(range.dataset.lookRange);return true}
    const next=event.target.closest('[data-desk68]');
    if(next){event.preventDefault();event.stopPropagation();deskAction(next.dataset.desk68);return true}
    if(event.target.closest('#look43-ask')){event.preventDefault();event.stopPropagation();openAsk();return true}
    if(event.target.closest('#look43-reset')){event.preventDefault();event.stopPropagation();resetView();return true}
    return false;
  }
  function wireToolbarButtons(root){
    if(!root)return;
    root.querySelectorAll('[data-look-series]').forEach(button=>{
      button.onclick=(event)=>{event.preventDefault();applySeries(button.dataset.lookSeries)};
    });
    root.querySelectorAll('[data-look-range]').forEach(button=>{
      button.onclick=(event)=>{event.preventDefault();applyRange(button.dataset.lookRange)};
    });
    root.querySelectorAll('[data-desk68]').forEach(button=>{
      button.onclick=(event)=>{event.preventDefault();deskAction(button.dataset.desk68)};
    });
    const ask=root.querySelector('#look43-ask');
    if(ask)ask.onclick=(event)=>{event.preventDefault();openAsk()};
    const reset=root.querySelector('#look43-reset');
    if(reset)reset.onclick=(event)=>{event.preventDefault();resetView()};
  }
  function bindControls(){
    if(controlsBound)return;
    controlsBound=true;
    // Capture phase so chart series/range clicks win even if a parent stops bubbling.
    document.addEventListener('click',event=>{
      if(event.target.closest('[data-look-series],[data-look-range],[data-desk68],#look43-ask,#look43-reset'))onControlClick(event);
    },true);
  }
  function syncSeriesButtons(){
    document.querySelectorAll('[data-look-series]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lookSeries===series)));
  }
  function syncSeriesDock(){
    const professional=document.body.dataset.edition==='professional';
    let dock=document.getElementById('chart43-series');
    if(professional){dock?.remove();return}
    const host=document.getElementById('chart43-tools')||document.getElementById('overview-ranges');
    if(!host)return;
    if(!dock){
      dock=document.createElement('div');
      dock.id='chart43-series';
      dock.className='look43-series chart43-series';
      dock.setAttribute('role','group');
      dock.setAttribute('aria-label','Chart series');
      dock.innerHTML='<button type="button" data-look-series="line">Line</button><button type="button" data-look-series="candles">Candles</button>';
      if(host.id==='chart43-tools')host.prepend(dock);else host.after(dock);
      wireToolbarButtons(dock);
    }
    syncSeriesButtons();
  }
  function ensure(){
    bindControls();
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
      // Public demo: My Desk opens Overview (Home is soft-hidden / Mac-shaped).
      rail.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
        let view=button.dataset.view;
        if(view==='home'&&(document.documentElement.dataset.demoMode==='true'||window.MarketDeskHost?.demoMode))view='overview';
        changeView(view);
      }));
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
        setSelected(symbol);
        changeView((document.documentElement.dataset.demoMode==='true'||window.MarketDeskHost?.demoMode)?'overview':'home');
        paint();
      });
      top.querySelector('#look43-mode').addEventListener('click',event=>{
        const button=event.target.closest('[data-v43-edition]');
        if(button)applyEdition(button.dataset.v43Edition);
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
        const sector=event.target.closest('[data-look-sector]');
        if(sector){heat=sector.dataset.lookSector;paintHeat()}
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
    const savedLabel=E.savedSession
      ?'Saved session'
      :(window.MarketDeskHost?.quoteSource==='live'?'Live quote (cached)':'Recorded prices');
    head.innerHTML=professional?`<div><strong>${escapeHtml(E.selected||'')}</strong><span>${escapeHtml(name)}</span></div><div><b>${escapeHtml(price)}</b><em class="${up?'up':'down'}">${escapeHtml(move)}</em></div><span class="look43-saved">${escapeHtml(savedLabel)}</span>`:`<div><h2>${escapeHtml(name)}</h2><span class="look43-pill">${escapeHtml(E.selected||'')}</span></div><div class="look43-price"><b>${escapeHtml(price)}</b><em class="${up?'up':'down'}">${escapeHtml(move)}</em></div><span class="look43-saved">${escapeHtml(savedLabel)}</span>`;
    const ranges=professional?['1H','1D','1W','1M']:['1H','1D','1W','1M','3M','1Y'];
    const toolbar=document.getElementById('look43-tools');
    if(toolbar.dataset.edition!==document.body.dataset.look+'-68'){
      toolbar.dataset.edition=document.body.dataset.look+'-68';
      toolbar.innerHTML=`${professional?'':`<div class="look43-series"><button type="button" data-look-series="line" aria-pressed="${series!=='candles'}">Line</button><button type="button" data-look-series="candles" aria-pressed="${series==='candles'}">Candles</button></div>`}<div class="look43-ranges">${ranges.map(range=>`<button type="button" data-look-range="${range}" aria-pressed="${E.range===range}">${range}</button>`).join('')}</div><button type="button" id="look43-ask">Ask Intelligence</button><button type="button" id="look43-reset">Reset</button><button type="button" data-journal="chart">Save evidence</button><button type="button" data-desk68="move">Investigate this move</button><button type="button" data-desk68="compare">Compare a company</button><button type="button" data-desk68="financials">Supported financials</button>`;
      wireToolbarButtons(toolbar);
      window.Annotate60?.mount?.();
    }
    syncSeriesButtons();
    toolbar.querySelectorAll('[data-look-range]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lookRange===E.range)));
    syncSeriesDock();
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
    more.textContent=[brief,forecast,note,barsSource&&wantsCandles()?'OHLC: '+barsSource:''].filter(Boolean).join(' ');
    detail.append(label,more);
    coverage.append(summary,detail);
    const observed=E.verifiedAt?new Date(E.verifiedAt).toLocaleTimeString('en-GB',{hour12:false})+' last recorded trade':'No trade recorded this session';
    const feed=document.getElementById('look43-feed');
    if(feed&&!(wantsCandles()&&barsSource&&(E.demoMode||window.MarketDeskHost?.demoMode))){
      feed.textContent=(['1H','1D'].includes(E.range)?observed+' · collector '+(E.backgroundCollector?'on':'off'):'Daily chart uses saved closes · '+observed);
    }
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
    const key=[E.selected,E.range,document.body.dataset.edition,E.savedSession,(E.watch||[]).join(','),price,E.chartPoints?.length,E.chartPoints?.at?.(-1)?.t,document.getElementById('chart-forecast-legend')?.textContent?.slice(0,48),series].join('|');
    if(key!==paintKey){paintKey=key;paint()}
    else syncSeriesDock();
    if(E.selected!==eventsKey){eventsKey=E.selected||'';paintEvents()}
    if(E.selected!==barsSymbol||(wantsCandles()&&!bars.length))loadCandles();
    if((document.body.dataset.edition||'')+'|'+(E?.watch||[]).join(',')!==heatKey){heatKey=(document.body.dataset.edition||'')+'|'+(E?.watch||[]).join(',');paintHeat()}
    if((document.body.dataset.edition||'')+'|'+E?.selected!==tapeKey){tapeKey=(document.body.dataset.edition||'')+'|'+E?.selected;paintTape()}
  }
  const start=()=>{ensure();refresh();setInterval(()=>{if(document.visibilityState==='visible')refresh()},4000)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('marketdesk:edition-change',()=>setTimeout(refresh,0));
  window.addEventListener('marketdesk:ready',()=>setTimeout(()=>{loadCandles(true);refresh()},0));
  window.addEventListener('marketdesk:layout',()=>setTimeout(syncSeriesDock,0));
  return {candleBars,refresh,loadCandles,setSeries:applySeries,get series(){return series},get bars(){return bars.slice()},get barsSource(){return barsSource}};
})();
