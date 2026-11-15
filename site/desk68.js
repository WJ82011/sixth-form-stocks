/* Four activities. Existing views keep their addresses. */
const Desk68=window.Desk68=(()=>{
  const AREAS={
    home:'My Desk',overview:'My Desk',alerts:'My Desk',portfolio:'My Desk',tape:'My Desk',
    markets:'Explore',heatmap:'Explore',crypto:'Explore',screener:'Explore',comparison:'Explore',indicators:'Explore',news:'Explore',macro:'Explore',
    company:'Investigate',calendar:'Investigate',forecast:'Investigate',accuracy:'Investigate',valuation:'Investigate',intelligence:'Investigate',
    research:'My Research',reports:'My Research',learning:'My Research'
  };
  function regroup(){
    const nav=document.getElementById('nav');
    if(!nav||nav.dataset.desk68)return;
    const buttons=[...nav.querySelectorAll('.nav-btn[data-view]')];
    const buckets={};
    for(const button of buttons){
      const previous=button.closest('.sidebar-group')?.querySelector('summary')?.textContent?.replace(/\s+/g,' ').trim()||'the main list';
      button.dataset.was=previous;
      button.title='Previously in '+previous;
      const area=AREAS[button.dataset.view]||'Advanced';
      button.dataset.area=area;
      (buckets[area]||=[]).push(button);
    }
    nav.querySelectorAll('.sidebar-group').forEach(group=>group.remove());
    for(const name of ['My Desk','Explore','Investigate','My Research','Advanced']){
      const list=buckets[name];
      if(!list)continue;
      const details=document.createElement('details');
      details.className='sidebar-group';
      details.open=name==='My Desk';
      details.innerHTML='<summary><span>'+name+'</span><span class="sidebar-chevron" aria-hidden="true">⌄</span></summary><div class="sidebar-submenu"></div>';
      list.forEach(button=>details.querySelector('.sidebar-submenu').append(button));
      nav.append(details);
    }
    nav.dataset.desk68='1';
    const forecast=document.getElementById('view-forecast');
    if(forecast&&!document.getElementById('desk68-forecast')){
      const note=document.createElement('p');
      note.id='desk68-forecast';
      note.textContent='Forecast Lab checks whether a model beat an unchanged price on later dates, and it shows that uncertainty. Forecast Results keeps the older issued-forecast scorecard. The chart line appears only when this check passes.';
      forecast.prepend(note);
    }
    const accuracy=document.getElementById('view-accuracy');
    if(accuracy&&!document.getElementById('desk68-accuracy')){
      const note=document.createElement('p');
      note.id='desk68-accuracy';
      note.textContent='These rows are issued forecasts already saved on this Mac. They are not rebuilt by Forecast Lab. Open Forecast Lab to see whether a model was reliable.';
      accuracy.prepend(note);
    }
  }
  function go(action){
    const symbol=typeof E!=='undefined'?E.selected:'';
    if(!symbol)return;
    if(action==='move'){
      const box=window.Chart43?.window?.();
      const start=box?new Date(box.from).toLocaleDateString('en-CA',{timeZone:'America/New_York'}):'';
      const end=box?new Date(box.to).toLocaleDateString('en-CA',{timeZone:'America/New_York'}):'';
      changeView('company');
      window.Shell43?.companyTab?.('events');
      if(start&&end&&window.Move44?.open)Move44.open({symbol,start,end});
      return;
    }
    if(action==='compare'){
      changeView('comparison');
      const first=document.getElementById('desk61-a');
      if(first)first.value=symbol;
      return;
    }
    if(action==='financials'){
      changeView('company');
      window.Shell43?.companyTab?.('financials');
      const read=[...document.querySelectorAll('#view-company button')].find(button=>/Read saved results/i.test(button.textContent));
      if(read)read.click();
    }
  }
  return {regroup,go,AREAS};
})();
