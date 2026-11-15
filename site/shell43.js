/* Chart-first home and a single company workspace. Existing sections stay in the page. */
const Shell43=window.Shell43=(()=>{
  const anchors=new Map();
  function pin(node){
    if(!node||anchors.has(node))return;
    const mark=document.createComment('shell43-anchor');
    node.parentNode.insertBefore(mark,node);
    anchors.set(node,mark);
  }
  function restore(node){
    const mark=anchors.get(node);
    if(mark?.parentNode&&mark.nextSibling!==node)mark.parentNode.insertBefore(node,mark.nextSibling);
  }
  function ensure(){
    const home=document.getElementById('view-home');
    if(home&&!document.getElementById('home43')){
      const dash=document.createElement('section');
      dash.id='home43';
      dash.className='home43';
      dash.innerHTML='<div id="home43-chart"></div>';
      home.prepend(dash);
      dash.addEventListener('click',event=>{
        const stock=event.target.closest('[data-select]');
        if(!stock)return;
        if(document.querySelector('.view.active')?.id==='view-home'&&typeof setSelected==='function'){setSelected(stock.dataset.select);paint();if(typeof drawChart==='function')drawChart();return}
        if(typeof openStock==='function')openStock(stock.dataset.select);
      });
    }
    const company=document.getElementById('view-company');
    if(company&&!document.getElementById('company43')){
      const block=document.createElement('div');
      block.id='company43';
      block.className='company43';
      block.innerHTML='<div class="company43-tabs" role="tablist" aria-label="Company workspace"><button type="button" data-company-tab="overview">Overview</button><button type="button" data-company-tab="events">Events</button><button type="button" data-company-tab="financials">Financials</button><button type="button" data-company-tab="research">Research</button></div><div id="company43-chart"></div><section id="company43-research" hidden><h2>Research</h2><p>Notes, comparisons and questions use the same selected company.</p><div class="company43-links"><button type="button" data-view="research">Research projects</button><button type="button" data-view="intelligence">Ask Intelligence</button><button type="button" data-view="comparison">Compare companies</button><button type="button" data-view="forecast">Forecasts</button><button type="button" data-journal="chart">Save to research</button></div></section>';
      const picker=company.querySelector('.instrument-picker');
      (picker||company).after(block);
      block.addEventListener('click',event=>{
        const tab=event.target.closest('[data-company-tab]');
        if(tab)companyTab(tab.dataset.companyTab);
      });
    }
    if(!document.getElementById('shell43-primary')){
      const nav=document.createElement('nav');
      nav.id='shell43-primary';
      nav.className='shell43-primary';
      nav.setAttribute('aria-label','Primary destinations');
      nav.innerHTML='<button type="button" data-view="home">My Desk</button><button type="button" data-view="markets">Explore</button><button type="button" data-view="company">Investigate</button><button type="button" data-view="research">My Research</button><button type="button" data-view="settings">Settings</button>';
      const anchor=document.querySelector('.focus-nav');
      if(anchor)anchor.after(nav);else document.querySelector('header')?.append(nav);
    }
    pin(document.getElementById('pro-console'));
    pin(document.getElementById('main-chart-panel'));
  }
  function companyTab(name){
    const allowed=['overview','events','financials','research'];
    const tab=allowed.includes(name)?name:'overview';
    document.body.dataset.companyTab=tab;
    const events=document.getElementById('events42');
    const health=document.getElementById('financial-health');
    const legacy=document.querySelector('#view-company .fh-legacy');
    const research=document.getElementById('company43-research');
    if(events)events.hidden=tab!=='events';
    if(health)health.hidden=tab!=='financials';
    if(legacy)legacy.hidden=tab!=='overview'&&tab!=='research';
    if(research)research.hidden=tab!=='research';
    document.querySelectorAll('button[data-company-tab]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.companyTab===tab)));
    try{sessionStorage.setItem('md-company-tab',tab)}catch{}
    if(tab==='events'&&window.Events42?.open)Events42.open();
    if(tab==='financials'&&window.FinancialHealth?.open)FinancialHealth.open();
    requestAnimationFrame(()=>{if(typeof drawChart==='function')drawChart()});
  }
  let placed='';
  function place(){
    ensure();
    const view=(document.querySelector('.view.active')?.id||'').replace('view-','');
    const professional=document.body.dataset.edition==='professional';
    const consoleNode=document.getElementById('pro-console');
    const host=document.getElementById('view-'+(view==='company'?'company':'home'));
    if(professional&&consoleNode&&view==='company'){
      if(host.firstChild!==consoleNode)host.prepend(consoleNode);
    }
    else if(consoleNode)restore(consoleNode);
    document.body.dataset.shellView=view||'';
    const panel=document.getElementById('main-chart-panel');
    const goal=chartSlot();
    if(panel&&goal&&panel.parentNode!==goal){
      goal.appendChild(panel);
      window.dispatchEvent(new Event('resize'));
      if(typeof drawChart==='function')requestAnimationFrame(drawChart);
    }
    paint();
    document.querySelectorAll('#shell43-primary [data-view]').forEach(button=>button.toggleAttribute('aria-current',button.dataset.view===view));
    const signature=[view,professional,goal?.id].join('|');
    if(signature===placed)return;
    placed=signature;
    let saved='overview';
    try{saved=sessionStorage.getItem('md-company-tab')||'overview'}catch{}
    companyTab(saved);
    window.dispatchEvent(new Event('marketdesk:layout'));
  }
  function paint(){
    if(typeof E==='undefined'||!document.getElementById('home43-symbol'))return;
    const quote=typeof quoteFor==='function'?quoteFor(E.selected):null;
    document.getElementById('home43-symbol').textContent=E.selected||'Choose a stock';
    document.getElementById('home43-name').textContent=E.names?.[E.selected]||'';
    document.getElementById('home43-price').textContent=quote?fmtUnit(E.selected,quote.p):'No saved price yet';
    const move=document.getElementById('home43-move');
    move.textContent=quote&&Number.isFinite(quote.change)?`${quote.change>=0?'+':''}${quote.change.toFixed(2)}% today`:'Daily move unavailable';
    const coverage=document.getElementById('chart-data-coverage')?.textContent||'Checking saved prices…';
    document.getElementById('home43-status').textContent=coverage.split('·').slice(0,2).join('·').trim();
    const list=document.getElementById('home43-watch');
    const rows=(E.watch||[]).slice(0,8);
    list.innerHTML=rows.length?rows.map(symbol=>{
      const row=quoteFor(symbol);
      const change=row&&Number.isFinite(row.change)?`${row.change>=0?'+':''}${row.change.toFixed(2)}%`:'—';
      return `<button type="button" data-select="${escapeHtml(symbol)}" aria-pressed="${symbol===E.selected}"><strong>${escapeHtml(symbol)}</strong><em>${escapeHtml(E.names?.[symbol]||symbol)}</em><span>${row?escapeHtml(fmtUnit(symbol,row.p)):'—'}</span><small>${escapeHtml(change)}</small></button>`;
    }).join(''):'<p>Your watchlist is empty. Add a company from Markets.</p>';
  }
  function chartSlot(){
    const view=document.body.dataset.shellView||(document.querySelector('.view.active')?.id||'').replace('view-','');
    if(view==='home')return document.getElementById('home43-chart');
    if(document.body.dataset.edition==='professional'&&['company','overview'].includes(view))return document.getElementById('pro-chart-mount');
    if(view==='company')return document.getElementById('company43-chart');
    return null;
  }
  document.addEventListener('DOMContentLoaded',()=>{
    ensure();
    place();
    document.body.addEventListener('click',event=>{
      const button=event.target.closest('#shell43-primary [data-view], .home43-side > button[data-view], .company43-links [data-view]');
      if(button&&typeof changeView==='function')changeView(button.dataset.view);
    });
    window.addEventListener('marketdesk:ready',place);
    const views=new MutationObserver(place);
    for(const view of document.querySelectorAll('.view'))views.observe(view,{attributes:true,attributeFilter:['class']});
    setInterval(()=>{if(document.visibilityState==='visible')paint()},2000);
  });
  window.addEventListener('marketdesk:edition-change',()=>setTimeout(place,0));
  return {place,chartSlot,companyTab,paint};
})();
