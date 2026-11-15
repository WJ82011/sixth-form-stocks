/* One company and period follow the chart, review, question and journal. */
const Desk50=(()=>{
'use strict';
const KEY='md-desk50-context',VISIT='md-desk50-visit';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function read(){try{return JSON.parse(sessionStorage.getItem(KEY)||'{}')}catch{return {}}}
function write(partial){const next={...read(),...partial};sessionStorage.setItem(KEY,JSON.stringify(next));return next;}
function rememberVisit(){const previous=Number(localStorage.getItem(VISIT)||0);if(!previous)localStorage.setItem(VISIT,String(Date.now()-86400000));return previous||Date.now()-86400000;}
async function visit(){
 const body=$('desk50-visit-body');if(!body)return;
 const since=rememberVisit();
 const symbols=(typeof E!=='undefined'&&E.watch||[]).slice(0,12).join(',');
 try{
  const response=await fetch('/api/v3/desk50?part=since&since='+since+'&symbols='+encodeURIComponent(symbols),{cache:'no-store'});
  const data=await response.json();
  const moves=(data.moves||[]).map(row=>`<button type="button" data-desk-symbol="${esc(row.symbol)}" data-desk-start="${esc(row.start)}" data-desk-end="${esc(row.end)}">${esc(row.symbol)} ${esc(row.start)} to ${esc(row.end)} · ${Number(row.returnPct).toFixed(2)}%</button>`).join('');
  const alerts=(data.alerts||[]).map(row=>`<p>${esc(row.symbol)} alert at ${esc(row.price)} · ${esc(row.rule||'saved rule')}</p>`).join('');
  const graded=(data.graded||[]).map(row=>`<p>${esc(row.symbol)} forecast ${esc(row.forecastPrice)} graded at ${esc(row.actualPrice)} · ${esc(row.anchorDay)} to ${esc(row.targetDay)}</p>`).join('');
  const due=(typeof Journal49!=='undefined'?JSON.parse(localStorage.getItem('md-reborn-journal')||'[]'):[]).filter(item=>item.status==='open'&&item.reviewDate);
  body.innerHTML=`<p>Saved records since ${esc(new Date(since).toLocaleString('en-GB'))}. Followed research is kept in What changed.</p><p><button type="button" id="desk50-open-changes">Open what changed</button></p>${moves||'<p>No newer saved close for the followed companies.</p>'}${alerts}${graded}${(data.gaps||[]).map(gap=>`<p>${esc(gap)}</p>`).join('')}${due.slice(0,4).map(item=>`<p>Review due: ${esc(item.symbol)} · ${esc(item.title)} · ${esc(item.reviewDate)}</p>`).join('')}`;
  const openChanges=body.querySelector('#desk50-open-changes');
  if(openChanges)openChanges.onclick=()=>{if(typeof changeView==='function')changeView('research');};
  body.querySelectorAll('[data-desk-symbol]').forEach(button=>button.onclick=()=>{if(typeof setSelected==='function')setSelected(button.dataset.deskSymbol);write({symbol:button.dataset.deskSymbol,start:button.dataset.deskStart,end:button.dataset.deskEnd});if(window.Move44)Move44.open({symbol:button.dataset.deskSymbol,start:button.dataset.deskStart,end:button.dataset.deskEnd});});
 }catch(error){body.textContent=error.message;}
 localStorage.setItem(VISIT,String(Date.now()));
}
async function status(){
 const node=$('desk50-status');if(!node||typeof E==='undefined'||!E.selected)return;
 try{
  const response=await fetch('/api/v3/desk50?symbol='+encodeURIComponent(E.selected),{cache:'no-store'});
  const data=await response.json();
  node.textContent=(data.detail||'')+' '+(data.source||'')+' Followed companies are collected first while this server is running.';
 }catch(error){node.textContent=error.message;}
}
function settings(){
 const grid=document.querySelector('#view-settings .settings-grid');if(!grid||$('desk50-backup'))return;
 const card=document.createElement('section');card.id='desk50-backup';card.className='surface settings-card settings-wide';
 card.innerHTML='<h3>Local backup</h3><p id="desk50-storage">Checking storage…</p><p>The backup includes the market database, alert rules, issued forecasts and the workspace file of watchlists, settings, notes and journal entries. A backup is taken with the database’s own backup tool while collection can keep running.</p><div class="journal49-actions"><button type="button" id="desk50-make" class="primary-btn">Back up now</button><button type="button" id="desk50-trim" class="ghost-btn">Keep the newest 5 backups</button></div><label>Restore a backup<select id="desk50-files"></select></label><button type="button" id="desk50-restore" class="ghost-btn">Restore selected backup</button><p id="desk50-backup-status"></p>';
 grid.prepend(card);
 const refresh=async()=>{
  const response=await fetch('/api/v3/desk50?part=storage',{cache:'no-store'});
  const data=await response.json();
  $('desk50-storage').textContent=`Database ${Math.round((data.databaseBytes||0)/1024)} KB · workspace ${Math.round((data.workspaceBytes||0)/1024)} KB · ${data.backupCount||0} backups. ${data.cleanup||''}`;
  $('desk50-files').innerHTML=(data.backups||[]).map(name=>`<option>${esc(name)}</option>`).join('')||'<option value="">No backup yet</option>';
 };
 $('desk50-make').onclick=async()=>{const result=await post('/api/v3/desk50-backup',{action:'backup'});$('desk50-backup-status').textContent='Saved '+result.file+'.';refresh();};
 $('desk50-trim').onclick=async()=>{if(!window.confirm('Delete older backups and keep the newest 5? The market database is not changed.'))return;const result=await post('/api/v3/desk50-backup',{action:'trim',confirm:'keep-newest-5'});$('desk50-backup-status').textContent=(result.removed||[]).length+' older backups deleted.';refresh();};
 $('desk50-restore').onclick=async()=>{const file=$('desk50-files').value;if(!file||!window.confirm('Restore '+file+'? A new backup of the current database is saved first.'))return;const result=await post('/api/v3/desk50-backup',{action:'restore',file,confirm:'restore-this-backup'});$('desk50-backup-status').textContent='Restored '+result.restored+'. Reload the page to read the restored workspace.';};
 refresh().catch(error=>{$('desk50-storage').textContent=error.message;});
}
function connect(){
 if(typeof window.setSelected==='function'&&!window.setSelected.desk50){
  const previous=window.setSelected;
  const wrapped=function(sym){const before=read().symbol;const result=previous.apply(this,arguments);write(before&&before!==sym?{symbol:sym,start:'',end:'',range:(typeof E!=='undefined'&&E.range)||''}:{symbol:sym,range:(typeof E!=='undefined'&&E.range)||''});return result;};
  wrapped.desk50=true;window.setSelected=wrapped;
 }
 if(window.Move44&&Move44.open&&!Move44.open.desk50){
  const previous=Move44.open;
  const wrapped=function(spec){write({symbol:spec.symbol,start:spec.start,end:spec.end,range:'move'});return previous.apply(this,arguments);};
  wrapped.desk50=true;Move44.open=wrapped;
 }
}
document.addEventListener('DOMContentLoaded',()=>{connect();settings();visit();status();});
return {read,write};
})();
