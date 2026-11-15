/* Company event timeline. Saved records only, unless Update events is pressed. */
const Events42=window.Events42=(()=>{
  const $=id=>document.getElementById(id);
  let packet=null, selected=null, horizon=1, requestId=0;
  const money=value=>Number.isFinite(value)?value.toLocaleString('en-GB',{style:'currency',currency:'USD'}):'—';
  const num=value=>Number.isFinite(value)?value.toFixed(2):'—';
  function symbol(){return $('company-select')?.value||''}
  function when(ms){return Number.isFinite(ms)?new Date(ms).toLocaleString('en-GB'):'not saved yet'}
  function comparison(){
    const row=(packet?.comparisons||{})[selected];
    return row?row[String(horizon)]:null;
  }
  function render(){
    const list=$('events42-list'), detail=$('events42-detail'), gaps=$('events42-gaps');
    if(!list||!detail)return;
    const events=packet?.events||[];
    $('events42-status').textContent=(packet?.symbol||'Company')+' · timeline saved '+when(packet?.updatedAt)+(packet?.offline?' · read from this Mac':' · just checked');
    gaps.innerHTML=(packet?.gaps||[]).map(note=>'<p>'+escapeHtml(note)+'</p>').join('');
    list.innerHTML=events.length?events.map(event=>'<button type="button" class="events42-item" data-event="'+escapeHtml(event.id)+'" aria-pressed="'+(event.id===selected)+'"><strong>'+escapeHtml(event.title)+'</strong><small>'+escapeHtml(event.kindLabel)+' · '+escapeHtml(event.timeLabel)+'</small></button>').join(''):'<p>No saved events for this company.</p>';
    const event=events.find(row=>row.id===selected);
    if(!event){detail.innerHTML='<p>Select an event to see its source and the price window.</p>';return}
    const result=comparison();
    const linkName=event.source&&event.source.includes('finnhub.io')?'News provider link':'Original source';
    const link=event.source&&event.source.startsWith('http')?'<p><a href="'+escapeHtml(event.source)+'" target="_blank" rel="noopener noreferrer">'+linkName+'</a></p>':'<p>No source link was supplied.</p>';
    let move='<p>No comparison is available.</p>';
    if(result){
      if(result.status==='ready'){
        move='<p><strong>'+escapeHtml(result.sentence)+'</strong></p><p>'+escapeHtml(packet.symbol)+' return '+num(result.stockReturnPct)+'% · SPY return '+num(result.benchmarkReturnPct)+'% · difference '+num(result.differencePP)+' percentage points.</p><p>Starting close '+escapeHtml(result.anchor)+' '+money(result.anchorPrice)+' · ending close '+escapeHtml(result.target)+' '+money(result.targetPrice)+'. SPY '+money(result.benchmarkAnchorPrice)+' to '+money(result.benchmarkTargetPrice)+'.</p><p>'+escapeHtml(result.basis)+' '+escapeHtml(result.timingNote)+(result.savedCopy?' Saved comparison from '+when(result.computedAt)+'.':'')+'</p><p>'+escapeHtml(result.explanation)+'</p>';
      }else move='<p>'+escapeHtml(result.reason||'The comparison is withheld.')+'</p><p>'+escapeHtml(result.explanation||'')+'</p>';
    }
    detail.innerHTML='<h3>'+escapeHtml(event.title)+'</h3><p>'+escapeHtml(event.kindLabel)+' · '+escapeHtml(event.publisher)+'</p>'+(event.reason?'<p>'+escapeHtml(event.reason)+'</p>':'')+'<p>'+escapeHtml(event.timeLabel)+(event.window?' · '+escapeHtml(event.window):'')+'</p>'+link+(event.note?'<p>'+escapeHtml(event.note)+'</p>':'')+'<div class="events42-horizons" role="group" aria-label="Reaction window"><button type="button" class="ghost-btn" data-events-horizon="1" aria-pressed="'+(horizon===1)+'">1 session</button><button type="button" class="ghost-btn" data-events-horizon="5" aria-pressed="'+(horizon===5)+'">5 sessions</button></div>'+move+'<button type="button" class="ghost-btn" id="events42-chart">Show this window on the chart</button>';
    const chart=$('events42-chart');
    if(chart&&result?.anchor&&result?.target)chart.onclick=()=>{
      E.heatmapWindow={start:result.anchor,end:result.target,label:'Event window'};
      E.range='6M';
      document.querySelectorAll('#overview-ranges button').forEach(button=>button.classList.toggle('active',button.dataset.range==='6M'));
      if(typeof setSelected==='function')setSelected(packet.symbol);
      if(typeof changeView==='function')changeView(document.getElementById('home43-chart')?'home':'overview');
    };
  }
  async function load(refresh){
    const current=symbol();
    const id=++requestId;
    if(!current){$('events42-status').textContent='Choose a company first.';return}
    $('events42-status').textContent=refresh?'Checking free sources…':'Reading saved events…';
    try{
      const next=refresh?await post('/api/v3/events42-refresh',{symbol:current}):await api('/api/v3/events42?symbol='+encodeURIComponent(current));
      if(id!==requestId||current!==symbol()||(next.symbol&&next.symbol!==current))return;
      packet=next;
      if(!packet.events.some(row=>row.id===selected))selected=packet.events[0]?.id||null;
      render();
    }catch(error){if(id===requestId&&current===symbol())$('events42-status').textContent=error.message}
  }
  function open(){if(E.view==='company')load(false)}
  document.addEventListener('DOMContentLoaded',()=>{
    $('events42-read')?.addEventListener('click',()=>load(false));
    $('events42-refresh')?.addEventListener('click',()=>load(true));
    $('events42-list')?.addEventListener('click',event=>{
      const button=event.target.closest('[data-event]');
      if(!button)return;
      selected=button.dataset.event;
      render();
    });
    $('events42-detail')?.addEventListener('click',event=>{
      const button=event.target.closest('[data-events-horizon]');
      if(!button)return;
      horizon=Number(button.dataset.eventsHorizon);
      render();
    });
    $('company-select')?.addEventListener('change',()=>{selected=null;if(E.view==='company')load(false)});
    document.querySelectorAll('[data-view="company"]').forEach(button=>button.addEventListener('click',()=>setTimeout(open,0)));
  });
  return {open};
})();
