/* Research journal. The evidence saved with an idea is not replaced by a later price. */
const Journal49=(()=>{
'use strict';
const KEY='md-reborn-journal';
let draftSeq=0,draft=null,editing='';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ny=ms=>Number.isFinite(Number(ms))?new Date(Number(ms)).toLocaleDateString('en-CA',{timeZone:'America/New_York'}):'';
const stamp=ms=>Number.isFinite(Number(ms))?new Date(Number(ms)).toLocaleString('en-GB',{timeZoneName:'short'}):'Not recorded';
function load(){try{const raw=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(raw)?raw:[];}catch{return [];}}
function persist(list){if(typeof saveJSON==='function')saveJSON(KEY,list);else localStorage.setItem(KEY,JSON.stringify(list));}
function merge(local,remote){
 const chosen=new Map(),order=[];
 for(const item of [...(Array.isArray(remote)?remote:[]),...(Array.isArray(local)?local:[])]){
  if(!item||!item.id)continue;
  const previous=chosen.get(item.id);
  if(!previous){chosen.set(item.id,{...item,evidence:item.evidence||{}});order.push(item.id);continue;}
  const newer=(item.updatedAt||0)>=(previous.updatedAt||0)?item:previous;
  const older=newer===item?previous:item;
  const next={...newer,evidence:older.evidence||newer.evidence||{},createdAt:Math.min(older.createdAt||newer.createdAt,newer.createdAt||older.createdAt),history:[...(older.history||[]),...(newer.history||[])].slice(-20)};
  chosen.set(item.id,next);
 }
 return order.map(id=>chosen.get(id)).slice(0,200);
}
function chartPacket(){
 const points=(typeof E!=='undefined'&&E.chartPoints)||[];
 const first=points[0],last=points[points.length-1];
 const start=E.heatmapWindow&&E.heatmapWindow.start||ny(first&&first.t);
 const end=E.heatmapWindow&&E.heatmapWindow.end||ny(last&&last.t);
 return {origin:'chart',symbol:E.selected||'',range:E.range||'',start,end,evidence:{startPrice:first&&first.p,endPrice:last&&last.p,priceTs:last&&last.t||null,source:E.chartSource||'Recorded chart',capturedAt:Date.now()}};
}
function movePacket(){
 const data=window.Move44&&Move44.current&&Move44.current();
 if(!data||data.status!=='ready')return null;
 const links=[...(data.before||[]),...(data.uncertain||[])].filter(row=>row.source).slice(0,8).map(row=>({title:row.title,url:row.source}));
 return {origin:'move',symbol:data.symbol,range:'move',start:data.start,end:data.end,evidence:{startPrice:data.startPrice,endPrice:data.endPrice,source:data.source||'',basis:data.basis||'',qualification:data.evidence||'',links,capturedAt:Date.now()}};
}
function alertPacket(node){
 const card=node&&node.closest('[data-alert-symbol]');
 if(!card)return null;
 return {origin:'alert',symbol:card.dataset.alertSymbol,range:card.dataset.alertRange||'',start:card.dataset.alertStart||'',end:card.dataset.alertEnd||'',evidence:{startPrice:card.dataset.alertCompare?Number(card.dataset.alertCompare):null,endPrice:card.dataset.alertPrice?Number(card.dataset.alertPrice):null,priceTs:card.dataset.alertWhen?Number(card.dataset.alertWhen):null,source:card.dataset.alertSource||'',answer:card.dataset.alertRule||'',capturedAt:Date.now()}};
}
function answerPacket(){
 const data=window.Ask48&&Ask48.latest&&Ask48.latest();
 if(!data||!data.context)return null;
 const ev=data.evidence||{};
 return {origin:'answer',symbol:data.context.symbol,range:data.context.range||'',start:data.context.start||ev.start||'',end:data.context.end||ev.end||'',evidence:{startPrice:ev.startPrice,endPrice:ev.endPrice,source:ev.source||'',qualification:ev.qualification||'',answer:data.answer||'',links:(ev.items||[]).filter(item=>item.source).slice(0,8).map(item=>({title:item.title,url:item.source})),capturedAt:Date.now()}};
}
function openDraft(packet){
 if(!packet||!packet.symbol){$('journal49-status').textContent='Nothing on this screen can be saved yet.';return;}
 draft={seq:++draftSeq,packet};editing='';
 $('journal49-title').value=packet.symbol+' · '+(packet.start&&packet.end?packet.start+' to '+packet.end:packet.origin);
 $('journal49-expect').value='';$('journal49-reasons').value='';$('journal49-mind').value='';$('journal49-review').value='';
 $('journal49-dialog').showModal();
 $('journal49-form-status').textContent=packet.symbol+' · '+packet.origin+'. The prices below stay with this idea.';
}
function fields(){return {title:$('journal49-title').value.trim(),expectation:$('journal49-expect').value.trim(),reasons:$('journal49-reasons').value.trim(),changeMind:$('journal49-mind').value.trim(),reviewDate:$('journal49-review').value};}
function commit(){
 if(!draft||draft.seq!==draftSeq)return;
 if(!editing&&draft.packet.origin==='chart'&&typeof E!=='undefined'&&E.selected!==draft.packet.symbol){$('journal49-form-status').textContent='The chart company changed. Close this and save the company that is open now.';return;}
 const now=Date.now(),text=fields();
 if(!text.title){$('journal49-form-status').textContent='Add a title.';return;}
 const list=load();
 if(editing){
  const current=list.find(item=>item.id===editing);
  if(!current)return;
  current.history=[...(current.history||[]),{at:now,status:current.status,expectation:current.expectation,reasons:current.reasons,changeMind:current.changeMind,learned:current.learned,reviewDate:current.reviewDate}].slice(-20);
  Object.assign(current,text,{updatedAt:now});
 }else{
  list.unshift({id:crypto.randomUUID().replace(/-/g,'').slice(0,32),...draft.packet,...text,status:'open',learned:'',createdAt:now,updatedAt:now,history:[]});
 }
 persist(list.slice(0,200));draft=null;$('journal49-dialog').close();render();
}
function due(list){const today=new Date().toLocaleDateString('en-CA',{timeZone:'America/New_York'});return list.filter(item=>item.status==='open'&&item.reviewDate&&item.reviewDate<=today);}
function render(){
 const root=$('journal49-list');if(!root)return;
 const list=load();
 const company=($('journal49-company')&&$('journal49-company').value||'').trim().toUpperCase();
 const status=$('journal49-filter')?$('journal49-filter').value:'all';
 const query=($('journal49-search')&&$('journal49-search').value||'').trim().toLowerCase();
 const rows=list.filter(item=>(!company||item.symbol===company)&&(!status||status==='all'||item.status===status)&&(!query||(item.symbol+' '+item.title).toLowerCase().includes(query)));
 const waiting=due(list);
 $('journal49-due').innerHTML=waiting.length?waiting.map(item=>`<button type="button" data-journal-open="${esc(item.id)}">${esc(item.symbol)} · ${esc(item.title)} · review ${esc(item.reviewDate)}</button>`).join(''):'<p>No review is due.</p>';
 root.innerHTML=rows.length?rows.map(item=>`<article class="journal49-row"><button type="button" data-journal-open="${esc(item.id)}"><strong>${esc(item.symbol)}</strong> ${esc(item.title)}</button><span>${esc(stamp(item.createdAt))}</span><span>${esc(item.status)}</span></article>`).join(''):'<p>No journal entries match this filter.</p>';
}
async function openEntry(id){
 const item=load().find(row=>row.id===id);if(!item)return;
 try{sessionStorage.setItem('md-journal49',id);}catch(error){}
 editing=id;draft=null;
 const box=$('journal49-detail');
 let later='The latest saved close has not been read yet.';
 try{
  const response=await fetch('/api/v3/journal49?symbol='+encodeURIComponent(item.symbol),{cache:'no-store'});
  const data=await response.json();
  if(editing!==id)return;
  later=data.price==null?data.reason:`Latest saved close ${data.price} on ${data.date}. ${data.source}`;
 }catch(error){later=error.message;}
 if(editing!==id)return;
 const evidence=item.evidence||{};
 const changes=(item.history||[]).map(row=>`<li>${esc(stamp(row.at))} · ${esc(row.status||'open')} · ${esc(row.expectation||'No expectation recorded')}</li>`).join('');
 box.hidden=false;
 box.innerHTML=`<h3>${esc(item.title)}</h3><p>${esc(item.symbol)} · saved ${esc(stamp(item.createdAt))} · status ${esc(item.status)}</p><p>Original recorded price ${esc(evidence.endPrice??evidence.startPrice??'not saved')}${evidence.priceTs?' at '+esc(stamp(evidence.priceTs)):''}. Dates ${esc(item.start||'not set')} to ${esc(item.end||'not set')}.</p><p>${esc(later)}</p><p>${esc(evidence.qualification||evidence.answer||'')}</p><p>${esc(evidence.source||'')}</p>${(evidence.links||[]).map(link=>`<p><a href="${esc(link.url)}" target="_blank" rel="noopener noreferrer">${esc(link.title||link.url)}</a></p>`).join('')}<h4>Earlier wording</h4>${changes?'<ul>'+changes+'</ul>':'<p>No later edit has been saved.</p>'}<label>What I learned<textarea id="journal49-learned">${esc(item.learned||'')}</textarea></label><label>Judgement<select id="journal49-status"><option value="open">Still open</option><option value="supported">Supported</option><option value="challenged">Challenged</option><option value="unresolved">Unresolved</option></select></label><div class="journal49-actions"><button type="button" data-journal-save="${esc(item.id)}">Save what I learned</button><button type="button" data-journal-reopen="${esc(item.id)}">Reopen the chart</button><button type="button" data-journal-edit="${esc(item.id)}">Edit the original note</button></div>`;
 $('journal49-status').value=item.status||'open';
}
function saveLearned(id){
 const list=load(),item=list.find(row=>row.id===id);if(!item)return;
 const now=Date.now();
 item.history=[...(item.history||[]),{at:now,status:item.status,expectation:item.expectation,reasons:item.reasons,changeMind:item.changeMind,learned:item.learned,reviewDate:item.reviewDate}].slice(-20);
 item.learned=$('journal49-learned').value.trim();
 item.status=$('journal49-status').value;
 item.updatedAt=now;
 persist(list);render();openEntry(id);
}
function editEntry(id){
 const item=load().find(row=>row.id===id);if(!item)return;
 editing=id;draft={seq:++draftSeq,packet:item};
 $('journal49-title').value=item.title;$('journal49-expect').value=item.expectation||'';$('journal49-reasons').value=item.reasons||'';$('journal49-mind').value=item.changeMind||'';$('journal49-review').value=item.reviewDate||'';
 $('journal49-form-status').textContent='Editing keeps the original prices and adds the previous wording to the history.';
 $('journal49-dialog').showModal();
}
function reopen(id){
 const item=load().find(row=>row.id===id);if(!item||typeof setSelected!=='function')return;
 const seq=++draftSeq;
 setSelected(item.symbol);
 if(seq!==draftSeq)return;
 if(item.range&&item.range!=='move'&&typeof setChartRange==='function')setChartRange(item.range);
 if(item.start&&item.end&&window.Move44)Move44.open({symbol:item.symbol,start:item.start,end:item.end});
 if(item.origin==='answer'&&typeof changeView==='function')changeView('intelligence');
 else if(item.origin==='forecast'&&typeof changeView==='function')changeView('forecast');
 else if(typeof changeView==='function')changeView('home');
}
function download(){
 const lines=['Market Desk research journal',''];
 for(const item of load()){
  const evidence=item.evidence||{};
  lines.push(item.title,item.symbol+' · '+item.status+' · '+stamp(item.createdAt),'Dates: '+(item.start||'not set')+' to '+(item.end||'not set'),'What I think might happen: '+(item.expectation||'Not written.'),'Reasons: '+(item.reasons||'Not written.'),'What would change my mind: '+(item.changeMind||'Not written.'),'Review date: '+(item.reviewDate||'Not set'),'What I learned: '+(item.learned||'Not written.'),'Original prices: '+(evidence.startPrice??'not saved')+' to '+(evidence.endPrice??'not saved'),'Source: '+(evidence.source||'Not recorded.'));
  for(const link of evidence.links||[])lines.push('Link: '+(link.title||'')+' · '+link.url);
  lines.push('','------------------------------------------------------------','');
 }
 const blob=new Blob([lines.join('\n')],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='MarketDesk-Journal-'+new Date().toISOString().slice(0,10)+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function mount(){
 const view=$('view-research');if(!view||$('journal49'))return;
 const panel=document.createElement('section');panel.id='journal49';panel.className='surface journal49';
 panel.innerHTML='<div class="section-tag">RESEARCH JOURNAL</div><h2>Ideas saved from the screen</h2><div id="journal49-due" class="journal49-due"></div><div class="journal49-filters"><input id="journal49-search" placeholder="Search title or company" aria-label="Search journal"><input id="journal49-company" maxlength="12" placeholder="Company" aria-label="Filter by company"><select id="journal49-filter" aria-label="Filter by status"><option value="all">All statuses</option><option value="open">Open</option><option value="supported">Supported</option><option value="challenged">Challenged</option value="unresolved">Unresolved</option></select><button type="button" id="journal49-export" class="ghost-btn">Export journal</button></div><div id="journal49-list"></div><div id="journal49-detail" hidden></div><p id="journal49-status"></p>';
 view.insertBefore(panel,view.children[1]||null);
 const dialog=document.createElement('dialog');dialog.id='journal49-dialog';
 dialog.innerHTML='<form id="journal49-form"><h2>Save to research</h2><p id="journal49-form-status"></p><label>Title<input id="journal49-title" maxlength="160" required></label><label>What I think might happen<textarea id="journal49-expect" maxlength="4000"></textarea></label><label>Reasons<textarea id="journal49-reasons" maxlength="4000"></textarea></label><label>What would change my mind<textarea id="journal49-mind" maxlength="4000"></textarea></label><label>Review date<input id="journal49-review" type="date"></label><div class="journal49-actions"><button class="primary-btn" type="submit">Save idea</button><button type="button" id="journal49-cancel" class="ghost-btn">Cancel</button></div></form>';
 document.body.append(dialog);
 $('journal49-form').onsubmit=event=>{event.preventDefault();commit();};
 $('journal49-cancel').onclick=()=>dialog.close();
 ['journal49-search','journal49-company','journal49-filter'].forEach(id=>$(id).addEventListener('input',render));
 $('journal49-export').onclick=download;
 panel.addEventListener('click',event=>{
  const open=event.target.closest('[data-journal-open]');
  const save=event.target.closest('[data-journal-save]');
  const edit=event.target.closest('[data-journal-edit]');
  const again=event.target.closest('[data-journal-reopen]');
  if(open)openEntry(open.dataset.journalOpen);
  if(save)saveLearned(save.dataset.journalSave);
  if(edit)editEntry(edit.dataset.journalEdit);
  if(again)reopen(again.dataset.journalReopen);
 });
 render();
}
document.addEventListener('click',event=>{
 const button=event.target.closest('[data-journal]');if(!button)return;
 const origin=button.dataset.journal;
 const packet=origin==='chart'?chartPacket():origin==='move'?movePacket():origin==='alert'?alertPacket(button):origin==='compare'&&window.Compare52?Compare52.packet():origin==='scenario'&&window.Scenario53?Scenario53.packet():origin==='strategy'&&window.Strategy54?Strategy54.packet():origin==='scan'&&window.Scanner55?Scanner55.packet():origin==='stress'&&window.Stress58?Stress58.packet():answerPacket();
 openDraft(packet);
},true);
document.addEventListener('click',event=>{
 const next=event.target.closest('[data-select]');
 if(next&&draft&&draft.packet.origin==='chart'&&next.dataset.select!==draft.packet.symbol){draftSeq++;if($('journal49-form-status'))$('journal49-form-status').textContent='The chart company changed. This draft was not saved.';}
},true);
document.addEventListener('DOMContentLoaded',mount);
window.addEventListener('marketdesk:workspace-restored',render);
return {merge,refresh:render};
})();
