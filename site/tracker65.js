/* What changed: followed companies and saved research, checked from local records. */
const Tracker65=(()=>{
'use strict';
let seq=0;
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','"':'&quot;',"'":'&#39;','>':'&gt;'}[c]));
function journalRows(){try{return JSON.parse(localStorage.getItem('md-reborn-journal')||'[]');}catch(error){return [];}}
function currentEntry(){
 const id=sessionStorage.getItem('md-journal49')||'';
 return journalRows().find(row=>row.id===id)||journalRows().find(row=>row.symbol===(typeof E!=='undefined'?E.selected:''))||null;
}
async function post(body){
 const response=await fetch('/api/v3/tracker65',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)});
 const data=await response.json();
 if(!response.ok||data.error)throw new Error(data.error||'The follow could not be saved.');
 return data;
}
function settings(){
 const digest={}, alert={};
 document.querySelectorAll('[data-track-kind]').forEach(box=>{
  const kind=box.dataset.trackKind, mode=box.dataset.trackMode;
  if(mode==='digest')digest[kind]=box.checked;
  if(mode==='alert')alert[kind]=box.checked;
 });
 return {digest, alert, thresholdPP:Number($('tracker65-threshold').value)||1};
}
function noteFor(entry){
 const scenarioId=sessionStorage.getItem('md-scenario53')||'';
 return {symbol:entry&&entry.symbol||(typeof E!=='undefined'?E.selected:''), journalId:entry&&entry.id||'', title:entry&&entry.title||'', start:entry&&entry.start||'', end:entry&&entry.end||'', reviewDate:entry&&entry.reviewDate||$('tracker65-review').value||'', status:entry&&entry.status||'open', expectation:entry&&entry.expectation||'', assumptions:{scenarioId, growthPct:$('tracker65-growth').value===''?null:Number($('tracker65-growth').value)}, settings:settings()};
}
function paint(data){
 const host=$('tracker65-list'); if(!host)return;
 const companies=data.companies||[];
 if(!companies.length){host.innerHTML='<p>No company or research entry is being followed yet.</p>';return;}
 host.innerHTML=companies.map(company=>{
  const items=(company.items||[]).map(item=>`<article class="tracker65-item"><p><strong>${esc(item.symbol)} · ${esc(item.title)}</strong> ${item.notify==='alert'?'· Alert':''}</p><p>Original ${esc(item.original)} · Updated ${esc(item.updated)}</p><p>${esc(item.dates||'')} ${esc(item.calculation||'')}</p><p>${esc(item.source||'')} ${item.gap?'Found after a recording gap.':''} ${item.acknowledgedAt?'Acknowledged.':'Waiting.'}</p><div class="tracker65-actions"><button type="button" data-track-chart="${esc(item.symbol)}">Open chart</button><button type="button" data-track-source="${esc(item.kind)}">Open source</button><button type="button" data-track-journal="${esc(company.journalId)}">Open investigation</button>${item.acknowledgedAt?'':`<button type="button" data-track-ack="${esc(company.followId)}" data-track-id="${esc(item.id)}">Acknowledge</button>`}</div></article>`).join('')||'<p>Nothing newly saved is waiting.</p>';
  return `<section><h3>${esc(company.symbol)} · ${esc(company.title)}</h3><p>Saved judgement ${esc(company.status)}. Review ${esc(company.reviewDate||'not set')}. Thesis: ${esc(company.expectation||'Not written.')} Edit the thesis in the research journal. Market Desk does not change it.</p>${items}</section>`;
 }).join('')+((data.reviews||[]).length?`<h3>Previous reviews</h3>`+(data.reviews||[]).map(row=>`<p>${esc(row.symbol)} · ${esc(row.notice)} · ${(row.items||[]).length} items</p>`).join(''):'');
 host.querySelectorAll('[data-track-chart]').forEach(button=>button.onclick=()=>{if(typeof setSelected==='function')setSelected(button.dataset.trackChart);if(typeof changeView==='function')changeView('home');});
 host.querySelectorAll('[data-track-source]').forEach(button=>button.onclick=()=>{const kind=button.dataset.trackSource;if(typeof changeView==='function')changeView(kind==='forecast'?'forecast':kind==='alert'?'alerts':kind==='assumption'?'valuation':'company');});
 host.querySelectorAll('[data-track-journal]').forEach(button=>button.onclick=()=>{const id=button.dataset.trackJournal;const target=document.querySelector(`[data-journal-open="${id}"]`);if(target)target.click();else $('tracker65-status').textContent='That research entry is not in the list on this screen.';});
 host.querySelectorAll('[data-track-ack]').forEach(button=>button.onclick=async()=>{await post({action:'acknowledge',followId:button.dataset.trackAck,ids:[button.dataset.trackId]});$('tracker65-status').textContent='Acknowledged. The original thesis and judgement were not edited.';load();});
}
async function load(){
 const id=++seq;
 const symbol=typeof E!=='undefined'?E.selected:'';
 try{
  const response=await fetch('/api/v3/tracker65?symbol='+encodeURIComponent(symbol||''),{cache:'no-store'});
  const data=await response.json();
  if(id!==seq)return;
  paint(data);
 }catch(error){if(id===seq&&$('tracker65-status'))$('tracker65-status').textContent='Saved changes could not be read. '+error.message;}
}
async function follow(entry){
 const id=++seq;
 const sent=noteFor(entry);
 $('tracker65-status').textContent='Saving the starting evidence for '+(sent.symbol||'the selected company')+'.';
 try{
  const data=await post({action:'follow',...sent});
  if(id!==seq)return;
  $('tracker65-status').textContent=data.notice||'Follow saved.';
  await load();
 }catch(error){if(id===seq)$('tracker65-status').textContent=error.message;}
}
function mount(){
 const host=$('view-research'); if(!host||$('tracker65'))return;
 const panel=document.createElement('section');
 panel.id='tracker65'; panel.className='surface';
 const kinds=[['announcement','Announcements'],['filing','Filings'],['revision','Revised figures'],['forecast','Graded forecasts'],['alert','Triggered alerts'],['assumption','Assumptions'],['missing','Missing data']];
 panel.innerHTML=`<h2>What changed?</h2><p>Follow a company or a saved research entry. Checks use the records already saved on this Mac, including the overnight research log.</p><div class="tracker65-controls"><label>Review date<input id="tracker65-review" type="date"></label><label>Revisit when growth differs by<input id="tracker65-threshold" type="number" min="0" max="100" value="1"> percentage points</label><label>Saved revenue-growth assumption<input id="tracker65-growth" type="number" step="0.01" placeholder="Optional"></label><button type="button" id="tracker65-company">Follow this company</button><button type="button" id="tracker65-entry">Follow the open research entry</button><button type="button" id="tracker65-check">Check saved records</button></div><div class="tracker65-choices">${kinds.map(([kind,label])=>`<span>${label} <label>Digest<input type="checkbox" data-track-kind="${kind}" data-track-mode="digest" checked></label> <label>Alert<input type="checkbox" data-track-kind="${kind}" data-track-mode="alert"></label></span>`).join('')}</div><p id="tracker65-status" role="status"></p><div id="tracker65-list"></div>`;
 host.insertBefore(panel, host.firstChild);
 $('tracker65-company').onclick=()=>follow(null);
 $('tracker65-entry').onclick=()=>{const entry=currentEntry();if(!entry){$('tracker65-status').textContent='Open a research entry first. Nothing was followed.';return;}follow(entry);};
 $('tracker65-check').onclick=async()=>{await post({action:'sweep'});$('tracker65-status').textContent='Checked the saved records.';load();};
 load();
}
document.addEventListener('DOMContentLoaded',mount);
return {load};
})();
window.Tracker65=Tracker65;
