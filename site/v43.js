/* Standard / Professional switch, collapsible workstation and compact navigation. */
const Desk43=window.Desk43=(()=>{
  const reduced=()=>document.body?.dataset?.motion==='off'||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  function edition(){return document.body.dataset.edition==='professional'?'professional':'signal'}
  function apply(next){
    if(window.MarketDeskPreferences?.patch)MarketDeskPreferences.patch({edition:next});
    else document.body.dataset.edition=next;
    sync();
  }
  function sync(){
    const professional=edition()==='professional';
    document.querySelectorAll('[data-v43-edition]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.v43Edition===(professional?'professional':'standard'))));
    const label=document.getElementById('desk-edition-label');
    if(label){
      if(document.documentElement.dataset.demoMode==='true'||window.MarketDeskHost?.demoMode)label.textContent='DEMO / 01';
      else label.textContent=professional?'PROFESSIONAL / 02':'STANDARD / 01';
    }
    const heading=document.getElementById('desk-overview-edition');
    if(heading)heading.textContent=professional?'THE PROFESSIONAL MODE':'THE STANDARD MODE';
    const signal=document.querySelector('#edition-signal strong');
    if(signal)signal.textContent='Standard';
    const signalNote=document.querySelector('#edition-signal small');
    if(signalNote)signalNote.textContent='A spacious layout for reading and research';
  }
  function hide(name){
    const current=(document.body.dataset.v43Hide||'').split(' ').filter(Boolean);
    const next=current.includes(name)?current.filter(item=>item!==name):current.concat(name);
    document.body.dataset.v43Hide=next.join(' ');
    try{localStorage.setItem('md-reborn-v43-panels',next.join(' '))}catch{}
  }
  function tab(name){document.body.dataset.v43Tab=name}
  function mount(){
    const actions=document.querySelector('.focus-actions');
    if(actions&&!document.getElementById('v43-mode')){
      const group=document.createElement('div');
      group.id='v43-mode';group.className='v43-mode';group.setAttribute('role','group');group.setAttribute('aria-label','Standard or Professional mode');
      group.innerHTML='<button type="button" data-v43-edition="standard">Standard</button><button type="button" data-v43-edition="professional">Professional</button>';
      const nav=document.querySelector('.focus-nav');
      if(nav)nav.after(group);else actions.prepend(group);
      group.addEventListener('click',event=>{
        const button=event.target.closest('[data-v43-edition]');
        if(!button)return;
        apply(button.dataset.v43Edition==='professional'?'professional':'signal');
      });
    }
    const console=document.getElementById('pro-console');
    if(console&&!document.getElementById('v43-layout')){
      const bar=document.createElement('div');
      bar.id='v43-layout';bar.className='v43-layout';
      bar.innerHTML='<div class="v43-tabs" role="tablist" aria-label="Workstation panels"><button type="button" data-v43-tab="chart">Chart</button><button type="button" data-v43-tab="watch">Watchlist</button><button type="button" data-v43-tab="side">Trades</button></div><div class="v43-collapse"><button type="button" data-v43-hide="watch">Collapse watchlist</button><button type="button" data-v43-hide="side">Collapse details</button><button type="button" data-pro-nav="tape">Live Tape</button><button type="button" data-pro-nav="company">Company events</button></div>';
      console.querySelector('.pro-ops-head')?.after(bar);
      bar.addEventListener('click',event=>{
        const panel=event.target.closest('[data-v43-hide]');
        const chosen=event.target.closest('[data-v43-tab]');
        if(panel)hide(panel.dataset.v43Hide);
        if(chosen)tab(chosen.dataset.v43Tab);
      });
    }
    try{document.body.dataset.v43Hide=localStorage.getItem('md-reborn-v43-panels')||''}catch{}
    document.body.dataset.v43Tab='chart';
    document.body.classList.add('v43');
    if(!reduced())document.body.dataset.v43Motion='on';
    sync();
    window.addEventListener('marketdesk:edition-change',sync);
  }
  document.addEventListener('DOMContentLoaded',mount);
  return {apply,sync};
})();
