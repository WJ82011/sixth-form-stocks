/* Schedule, pause and the morning report for the local collector. */
const Overnight51=(()=>{
'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function when(ms){return ms?new Date(ms).toLocaleString('en-GB'):'not yet';}
function openJob(row){
 if(typeof setSelected==='function')setSelected(row.symbol);
 if(row.kind==='history'&&window.Move44)return;
 if((row.kind==='grade'||row.kind==='learn')&&typeof window.changeView==='function')window.changeView('learning');
}
async function report(){
 const body=$('overnight51-body');if(!body)return;
 const since=Number(localStorage.getItem('md-desk50-visit')||Date.now()-86400000);
 const response=await fetch('/api/v3/overnight51?part=morning&since='+since,{cache:'no-store'});
 const data=await response.json();
 const jobs=(data.jobs||[]).map(row=>`<button type="button" data-symbol="${esc(row.symbol)}" data-kind="${esc(row.kind)}">${esc(row.symbol)} ${esc(row.kind)} · ${esc(row.status)} · ${esc(row.detail)}</button>`).join('');
 const saved=(data.savedBars||[]).map(row=>`<p>${esc(row.symbol)}: ${esc(row.rowsTouched)} saved daily rows touched.</p>`).join('');
 const gaps=(data.gaps||[]).map(row=>`<p>${esc(row.note)} ${esc(new Date(row.from).toLocaleString('en-GB'))} to ${esc(new Date(row.to).toLocaleString('en-GB'))}.</p>`).join('');
 body.innerHTML=`<p>${esc(data.notice||'')}</p><p>Last saved history ${esc(when(data.lastHistoryAt))}. Last training ${esc(when(data.lastTrainingAt))}.</p>${saved}${jobs||'<p>No scheduled job has finished in this visit window.</p>'}${gaps}`;
 body.querySelectorAll('button').forEach(button=>button.onclick=()=>openJob({symbol:button.dataset.symbol,kind:button.dataset.kind}));
}
async function settings(){
 const grid=document.querySelector('#view-settings .settings-grid');if(!grid||$('overnight51-card'))return;
 const card=document.createElement('section');card.id='overnight51-card';card.className='surface settings-card settings-wide';
 card.innerHTML='<h3>Overnight research</h3><p id="overnight51-note"></p><label>Followed companies, comma separated. Leave blank to use the watchlist.<input id="overnight51-symbols" type="text" maxlength="180"></label><label>Collection from hour <input id="overnight51-start" type="number" min="0" max="24" value="0"> to hour <input id="overnight51-end" type="number" min="0" max="24" value="24"></label><label>Daily research hour <input id="overnight51-research" type="number" min="0" max="23" value="6"></label><label><input id="overnight51-quiet" type="checkbox"> Quiet mode: fewer quotes and one training company a day</label><div class="journal49-actions"><button type="button" id="overnight51-save" class="primary-btn">Save schedule</button><button type="button" id="overnight51-pause" class="ghost-btn">Pause</button></div><p id="overnight51-state"></p><div id="overnight51-jobs"></div>';
 grid.prepend(card);
 const paint=async()=>{
  const response=await fetch('/api/v3/overnight51?part=status',{cache:'no-store'});
  const data=await response.json();
  const saved=data.schedule||{};
  $('overnight51-symbols').value=(saved.symbols||[]).join(', ');
  $('overnight51-start').value=saved.startHour??0;
  $('overnight51-end').value=saved.endHour??24;
  $('overnight51-research').value=saved.researchHour??6;
  $('overnight51-quiet').checked=Boolean(saved.quiet);
  $('overnight51-pause').textContent=saved.paused?'Resume':'Pause';
  $('overnight51-note').textContent=data.notice||'';
  $('overnight51-state').textContent=`Database ${Math.round((data.databaseBytes||0)/1024)} KB. Last history ${when(data.lastHistoryAt)}. Last training ${when(data.lastTrainingAt)}. ${data.inWindow?'Inside collection hours.':'Outside collection hours.'}`;
  $('overnight51-jobs').innerHTML=(data.jobs||[]).map(row=>`<p>${esc(row.symbol)} ${esc(row.kind)} · ${esc(row.status)} · ${esc(row.detail)}</p>`).join('')||'<p>No job is queued for today.</p>';
 };
 $('overnight51-save').onclick=async()=>{
  const symbols=$('overnight51-symbols').value.split(',').map(item=>item.trim().toUpperCase()).filter(Boolean);
  const result=await post('/api/v3/overnight51',{action:'save',symbols,startHour:Number($('overnight51-start').value),endHour:Number($('overnight51-end').value),researchHour:Number($('overnight51-research').value),quiet:$('overnight51-quiet').checked});
  $('overnight51-state').textContent=result.notice||'Saved.';
  paint();
 };
 $('overnight51-pause').onclick=async()=>{
  const pausing=$('overnight51-pause').textContent==='Pause';
  await post('/api/v3/overnight51',{action:pausing?'pause':'resume'});
  paint();
 };
 paint().catch(error=>{$('overnight51-note').textContent=error.message;});
}
document.addEventListener('DOMContentLoaded',()=>{settings();report().catch(()=>{});});
return {report};
})();
