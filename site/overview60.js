/* Coverage overview. Equity sessions and crypto days stay in separate counts. */
const Overview60=(()=>{
  let seq=0;
  function mount(){
    const view=document.getElementById('view-heatmap');
    if(!view||document.getElementById('overview60'))return;
    view.insertAdjacentHTML('afterbegin','<article class="surface" id="overview60"><h2>Coverage overview</h2><p id="overview60-status" role="status">Reading saved closes…</p><div class="crypto38-tools"><button type="button" class="ghost-btn" id="overview60-refresh">Refresh overview</button></div><div id="overview60-body"></div></article>');
    document.getElementById('overview60-refresh').addEventListener('click',load);
  }
  function list(rows, action){
    return (rows||[]).map(row=>`<li><button type="button" data-overview-symbol="${row.symbol}" data-overview-action="${action}">${row.symbol}</button> ${Number.isFinite(row.changePct)?row.changePct.toFixed(2)+'%':row.reason||''}</li>`).join('');
  }
  function render(data){
    const equity=data.equity||{}, crypto=data.crypto||{};
    document.getElementById('overview60-body').innerHTML=`<section><h3>Stocks · ${equity.calendar||''}</h3><p>Evaluated ${equity.evaluated||0}. Included ${equity.included||0}. Period ${equity.start||'—'} to ${equity.end||'—'}.</p><p>Advancing ${equity.advancing||0}. Declining ${equity.declining||0}. Unchanged ${equity.unchanged||0}.</p><p>${equity.notice||''}</p><h4>Sectors</h4><ul>${(equity.sectors||[]).map(row=>`<li>${row.name}: ${row.changePct}% across ${row.count}</li>`).join('')||'<li>No sector has two included companies.</li>'}</ul><h4>Unusual moves</h4><ul>${list(equity.unusual,'chart')||'<li>None at the 3% line.</li>'}</ul><details><summary>Excluded ${((equity.excluded)||[]).length}</summary><ul>${list(equity.excluded,'chart')}</ul></details><details><summary>Included companies</summary><ul>${list(equity.companies,'compare')}</ul></details></section><section><h3>Crypto · ${crypto.calendar||''}</h3><p>Evaluated ${crypto.evaluated||0}. Included ${crypto.included||0}. Period ${crypto.start||'—'} to ${crypto.end||'—'}.</p><p>Advancing ${crypto.advancing||0}. Declining ${crypto.declining||0}.</p><p>${crypto.notice||''}</p><ul>${list(crypto.companies,'crypto')}</ul><details><summary>Excluded</summary><ul>${list(crypto.excluded,'crypto')}</ul></details></section>`;
  }
  async function load(){
    const id=++seq;
    const status=document.getElementById('overview60-status');
    if(status)status.textContent='Reading saved closes…';
    try{
      const response=await fetch('/api/v3/overview60');
      const data=await response.json();
      if(id!==seq)return;
      if(!response.ok||data.error)throw Error(data.error||'The overview could not be read.');
      render(data);
      if(status)status.textContent=data.notice||'';
    }catch(error){
      if(id===seq&&status)status.textContent=error.message;
    }
  }
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-overview-symbol]');
    if(!button)return;
    const symbol=button.dataset.overviewSymbol;
    if(button.dataset.overviewAction==='crypto'&&window.changeView){changeView('crypto');return;}
    if(typeof setSelected==='function'&&!symbol.includes('-'))setSelected(symbol);
    if(button.dataset.overviewAction==='compare'&&window.changeView)changeView('comparison');
    else if(window.changeView)changeView('home');
  });
  document.addEventListener('DOMContentLoaded',()=>{mount();const previous=window.changeView;if(typeof previous==='function')window.changeView=function(view){const result=previous.apply(this,arguments);if(view==='heatmap')load();return result;};});
  return window.Overview60={mount,load};
})();
