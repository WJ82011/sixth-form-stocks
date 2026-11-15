/* Four-company comparison from saved prices, filings and events. */
const Compare52=(()=>{
'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let seq=0,current=null;
function symbols(){return ['compare-a','compare-b','compare-c','compare-d'].map(id=>$(id)&&$(id).value).filter(Boolean);}
function packet(){
 if(!current||current.status!=='ok')return null;
 const lead=current.rows.slice().sort((a,b)=>b.indexEnd-a.indexEnd)[0];
 return {origin:'compare',symbol:lead.symbol,range:'move',start:current.start,end:current.end,evidence:{startPrice:100,endPrice:lead.indexEnd,source:lead.adjustment||'',answer:current.answer||'',qualification:current.notice||'',basis:current.symbols.join(', '),capturedAt:Date.now()}};
}
function chart(data){
 const points=data.rows.flatMap(row=>row.points);
 const lo=Math.min(100,...points.map(point=>point.index)),hi=Math.max(100,...points.map(point=>point.index)),span=hi-lo||1;
 const start=Date.parse(data.dates[0]),end=Date.parse(data.dates.at(-1));
 const paths=data.rows.map((row,index)=>{let prev=null;const path=row.points.map(point=>{const t=Date.parse(point.date),x=36+(t-start)/(end-start||1)*820,y=24+(hi-point.index)/span*180,move=!prev||t-prev>5*86400000;prev=t;return (move?'M':'L')+x.toFixed(1)+','+y.toFixed(1);}).join(' ');return '<path d="'+path+'" class="v3-line v3-line-'+index+'"/>';}).join('');
 return '<div class="v3-legend">'+data.rows.map((row,index)=>'<span class="v3-series-'+index+'">'+esc(row.symbol)+' · '+esc(row.latestDate)+' latest · '+row.returnPct.toFixed(2)+'%</span>').join('')+'</div><svg viewBox="0 0 900 250" role="img" aria-label="Four company comparison rebased to one hundred"><line x1="36" x2="856" y1="'+(24+(hi-100)/span*180)+'" y2="'+(24+(hi-100)/span*180)+'" class="v3-grid-line"/>'+paths+'<text x="36" y="242">'+esc(data.start)+'</text><text x="740" y="242">'+esc(data.end)+'</text></svg>';
}
function render(data){
 current=data;
 try{sessionStorage.setItem('md-compare52',(data.symbols||[]).join(','));}catch(error){}
 const root=$('compare52-output');if(!root)return;
 if(data.status!=='ok'){root.innerHTML='<p>'+esc(data.notice||'')+'</p>'+(data.rows||[]).map(row=>'<p>'+esc(row.symbol)+' latest saved '+esc(row.latestDate||'none')+' · '+esc(row.savedCloses||0)+' closes · '+esc(row.currency||'')+'</p>').join('');return;}
 const books=(data.financials&&data.financials.rows||[]).map(row=>'<article class="fh-compare-card"><p class="desk-eyebrow">'+esc(row.symbol)+'</p><p>'+esc(row.start||'No annual period')+' to '+esc(row.end||'')+' · '+esc(row.currency)+'</p><p>Revenue growth '+esc(row.revenueGrowthPct==null?'not available':Number(row.revenueGrowthPct).toFixed(2)+'%')+'</p><p>Operating margin: '+esc(row.operatingMarginNote)+'</p><p>Net margin '+esc(row.netMarginPct==null?'not available':Number(row.netMarginPct).toFixed(2)+'%')+'</p><p>Cash '+esc(row.cash==null?'not available':row.cash)+'</p><p>Debt '+esc(row.debt==null?'not available':row.debt)+'</p><p>'+esc(row.debtScope||'')+'</p>'+(row.filing?'<p><a href="'+esc(row.filing)+'" target="_blank" rel="noopener noreferrer">Filing</a></p>':'')+'</article>').join('');
 const events=(data.events||[]).map(row=>'<button type="button" data-symbol="'+esc(row.symbol)+'" data-start="'+esc(data.start)+'" data-end="'+esc(row.date)+'" data-source="'+esc(row.source)+'">'+esc(row.symbol)+' · '+esc(row.timeLabel)+' · '+esc(row.timingNote)+'</button>').join('');
 const gaps=data.rows.filter(row=>row.missingCount).map(row=>'<p>'+esc(row.symbol)+' is missing '+row.missingCount+' completed sessions inside '+esc(data.start)+' to '+esc(data.end)+'.</p>').join('');
 root.innerHTML='<p>'+esc(data.notice)+'</p>'+chart(data)+gaps+'<p>'+esc(data.financials.basis||'')+'</p><div class="fh-compare-cards">'+books+'</div><div id="compare52-events">'+events+'</div><p id="compare52-answer"></p>';
 root.querySelectorAll('button').forEach(button=>button.onclick=()=>{
  if(button.dataset.source)window.open(button.dataset.source,'_blank','noopener');
  if(window.Move44)Move44.open({symbol:button.dataset.symbol,start:button.dataset.start,end:button.dataset.end});
 });
}
async function load(params){
 const id=++seq;
 const response=await fetch('/api/v3/compare52?'+params,{cache:'no-store'});
 const data=await response.json();
 if(id!==seq)return null;
 if(!response.ok||data.error)throw new Error(data.error||'The comparison could not be read.');
 return data;
}
async function run(){
 const picked=symbols();
 $('compare52-status').textContent='Reading saved records…';
 try{
  const data=await load('symbols='+encodeURIComponent(picked.join(','))+'&start='+encodeURIComponent($('compare52-start').value)+'&end='+encodeURIComponent($('compare52-end').value));
  if(!data)return;
  render(data);$('compare52-status').textContent=data.status==='ok'?data.symbols.join(', ')+' · '+data.start+' to '+data.end+'.':data.notice;
 }catch(error){$('compare52-status').textContent=error.message;}
}
async function ask(question){
 const id=++seq;
 const params=new URLSearchParams({question,compareSymbols:symbols().join(','),start:$('compare52-start').value,end:$('compare52-end').value,symbol:symbols()[0]||''});
 const response=await fetch('/api/v3/ask48?'+params.toString(),{cache:'no-store'});
 const data=await response.json();
 if(id!==seq)return;
 if(current)current.answer=data.answer||'';
 const node=$('compare52-answer');if(node)node.textContent=data.answer||data.error||'';
 $('compare52-status').textContent=(data.context&&data.context.symbol?data.context.symbol+' · ':'')+(data.context&&data.context.start||'')+' to '+(data.context&&data.context.end||'');
}
function mount(){
 const view=$('view-comparison');if(!view||$('compare52'))return;
 const panel=document.createElement('section');panel.id='compare52';panel.className='surface';
 panel.innerHTML='<div class="section-tag">SAVED RECORDS / UP TO FOUR COMPANIES</div><h3>Compare the same completed sessions.</h3><p>Take-Two, Roblox, Unity and Sony are in the directory. The chart uses saved split-adjusted closes and starts each company at 100. It can be reopened offline.</p><label>From <input id="compare52-start" type="date"></label><label>To <input id="compare52-end" type="date"></label><div class="journal49-actions"><button type="button" id="compare52-run" class="primary-btn">Compare saved records</button><button type="button" id="compare52-save" class="ghost-btn">Save comparison</button><button type="button" class="ghost-btn" data-journal="compare">Save to research</button></div><label>Saved comparison <select id="compare52-saved"></select></label><button type="button" id="compare52-open" class="ghost-btn">Reopen saved comparison</button><button type="button" id="compare52-fresh" class="ghost-btn">Show the updated view</button><div class="mdi-prompts"><button type="button" data-compare-ask="Which company performed best over these dates?">Best performer</button><button type="button" data-compare-ask="How do their operating margins compare?">Operating margins</button></div><p id="compare52-status" role="status"></p><div id="compare52-output"></div>';
 const accounts=view.querySelector('.fh-comparison');
 view.insertBefore(panel,(accounts&&accounts.parentElement===view)?accounts:view.children[1]||null);
 const fourth=$('compare-d');
 if(!fourth){
  const label=document.createElement('label');label.textContent='COMPANY 04 (OPTIONAL)';
  const select=document.createElement('select');select.id='compare-d';
  label.append(select);const controls=view.querySelector('.compare-controls');if(controls)controls.append(label);
 }
 if(typeof researchUpdatePickers==='function')researchUpdatePickers();
 ['compare-a','compare-b','compare-c','compare-d'].forEach(id=>{const el=$(id);if(el)el.addEventListener('change',()=>{seq++;current=null;const out=$('compare52-output');if(out)out.textContent='';$('compare52-status').textContent='Company choices changed. Compare again.';});});
 $('compare52-run').onclick=run;
 $('compare52-save').onclick=async()=>{const result=await post('/api/v3/compare52',{action:'save',symbols:symbols(),start:$('compare52-start').value,end:$('compare52-end').value,title:symbols().join(' · ')});$('compare52-status').textContent='Saved '+result.saved.symbols.join(', ')+' from '+result.saved.start+' to '+result.saved.end+'.';await refreshList();};
 $('compare52-open').onclick=async()=>{const data=await load('id='+encodeURIComponent($('compare52-saved').value));if(!data)return;render(data.saved);$('compare52-status').textContent='Saved view '+data.saved.start+' to '+data.saved.end+'. Latest dates now: '+(data.fresh.rows||[]).map(row=>row.symbol+' '+((row.latestDate)||'none')).join(', ')+'.';};
 $('compare52-fresh').onclick=async()=>{const data=await load('id='+encodeURIComponent($('compare52-saved').value));if(!data)return;render(data.fresh);$('compare52-status').textContent='Updated view from the records saved now.';};
 panel.querySelectorAll('[data-compare-ask]').forEach(button=>button.onclick=()=>ask(button.dataset.compareAsk));
 refreshList().catch(error=>{$('compare52-status').textContent=error.message;});
}
async function refreshList(){
 const response=await fetch('/api/v3/compare52?part=list',{cache:'no-store'});
 const data=await response.json();
 $('compare52-saved').innerHTML=(data.saved||[]).map(row=>'<option value="'+esc(row.id)+'">'+esc(row.symbols)+' · '+esc(row.start)+' to '+esc(row.end)+'</option>').join('')||'<option value="">No saved comparison</option>';
}
document.addEventListener('DOMContentLoaded',mount);
return {packet,current:()=>current};
})();
