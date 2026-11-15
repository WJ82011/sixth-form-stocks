/* Scenario Studio on the existing valuation page. */
const Scenario53=(()=>{
'use strict';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const NAMES=['cautious','central','optimistic'];
let seq=0,loaded=null,result=null,savedId='';
function packet(){
 if(!result||!loaded)return null;
 const central=(result.cases||[]).find(row=>row.name==='central')||{};
 return {origin:'scenario',symbol:loaded.symbol,range:'1Y',start:loaded.start||'',end:loaded.end||'',evidence:{source:result.baseline&&result.baseline.sourceNote||'',answer:(result.cases||[]).map(row=>row.name+' '+row.calculation).join(' '),qualification:result.notice||'',basis:loaded.currency||'',endPrice:central.enterpriseM||null,capturedAt:Date.now()}};
}
function assumptions(){
 return NAMES.map(name=>({name,growthPct:Number($('s53-'+name+'-growth').value),marginPct:Number($('s53-'+name+'-margin').value),multiple:Number($('s53-'+name+'-multiple').value),method:$('s53-method').value}));
}
function notes(){const source=$('s53-note-source'),text=$('s53-note-text'),date=$('s53-note-date');if(!source||!source.value)return [];return [{date:date.value,source:source.value,assumption:text.value}];}
function statementCurrency(){const filed=loaded&&loaded.currency&&loaded.currency!=='not recorded'?loaded.currency:'';const typed=$('s53-currency')&&$('s53-currency').value||'';return (filed||typed).trim().toUpperCase();}
function manual(){
 const out={};
 for(const key of ['revenue','cash','debt','shares']){
  const value=$('s53-manual-'+key);if(!value||value.value==='')continue;
  out[key]={valueM:Number(value.value),unit:'millions',currency:statementCurrency(),source:$('s53-note-'+key).value};
 }
 return out;
}
function render(data){
 result=data;
 const root=$('scenario53-output');if(!root)return;
 const detailed=$('scenario53-detail')&&$('scenario53-detail').checked;
 const cases=(data.cases||[]).map(row=>{const years=(row.years||[]).map(year=>'<p>Year '+year.year+' · simulated · revenue '+year.revenueM.toFixed(2)+' · profit '+year.operatingProfitM.toFixed(2)+' · value '+(year.enterpriseM==null?'hidden':year.enterpriseM.toFixed(2))+'</p>').join('');return '<article class="fh-compare-card"><p class="desk-eyebrow">'+esc(row.name)+'</p><p>Growth '+row.growthPct+'% · margin '+row.marginPct+'% · multiple '+row.multiple+' · '+esc(row.method)+'</p><p>Year-five company value '+esc(row.enterpriseM==null?'hidden':row.enterpriseM.toFixed(2)+' million')+' · per share '+esc(row.valuePerShare==null?'hidden':row.valuePerShare.toFixed(2))+'</p>'+(detailed?years+'<p>'+esc(row.calculation)+'</p>':'<p>Saved history is separate from these five simulated years.</p>')+'</article>';}).join('');
 const sense=data.sensitivity||{},max=Math.max(1,...(sense.rows||[]).map(row=>row.span||0));
 const bars=(sense.rows||[]).map(row=>'<p>'+esc(row.driver)+' · step '+esc(row.step)+(row.driver==='valuation multiple'?'':' percentage points')+'</p><div style="height:10px;border-radius:6px;background:#d7e4f5;width:'+Math.max(8,Math.round(((row.span||0)/max)*100))+'%"></div>').join('');
 const grid=data.grid||{};
 const cells=(grid.rows||[]).map(row=>'<p>'+esc(grid.y)+' '+esc(row.input)+': '+(row.values||[]).map(value=>value==null?'hidden':Number(value).toFixed(0)).join(' · ')+'</p>').join('');
 root.innerHTML='<p>'+esc(data.notice||'')+'</p><div class="fh-compare-cards">'+cases+'</div><h3>Which assumption moves the company value</h3><p>The widest bar moves one assumption. The grid moves '+esc(grid.x||'')+' and '+esc(grid.y||'')+' together. '+esc(sense.strongest?'Strongest single change: '+sense.strongest+'.':'')+'</p>'+bars+cells;
}
function showFigures(data){
 loaded=data;
 const history=(data.history||[]).map(row=>'<p>Saved year · '+esc(row.end||row.period||'')+' · revenue '+(row.revenueM==null?'not saved':Number(row.revenueM).toFixed(2)+' million '+esc(row.currency||''))+'</p>').join('');
 $('scenario53-figures').innerHTML=(data.rows||[]).map(row=>'<p><strong>'+esc(row.name)+'</strong> · '+esc(row.kind)+' · '+esc(row.valueM==null?'not saved':Number(row.valueM).toFixed(2)+' million '+row.currency)+' · '+esc(row.period||'no period')+' · '+esc(row.note)+'</p>'+(row.source?'<p><a href="'+esc(row.source)+'" target="_blank" rel="noopener noreferrer">Source filing</a></p>':'')).join('')+history+'<p>'+esc(data.method)+'</p>';
 const box=$('s53-currency');const known=!!(data.currency&&data.currency!=='not recorded');if(box){box.value=known?data.currency:'USD';box.readOnly=known;}
 for(const key of ['revenue','cash','debt','shares']){const row=(data.rows||[]).find(item=>item.name===key||(key==='operating profit'));}
 $('scenario53-status').textContent=data.symbol+' · '+(data.start||'no period')+' to '+(data.end||'')+' · '+data.currency;
}
async function load(){
 const id=++seq,symbol=($('scenario53-symbol').value||'').trim().toUpperCase();
 const response=await fetch('/api/v3/scenario53?symbol='+encodeURIComponent(symbol),{cache:'no-store'});
 const data=await response.json();
 if(id!==seq)return;
 if(!response.ok||data.error){$('scenario53-status').textContent=data.error||'The figures could not be read.';return;}
 showFigures(data);
}
async function run(action){
 const id=++seq;
 if(!loaded){$('scenario53-status').textContent='Load the saved figures first.';return;}
 const body={action,symbol:loaded.symbol,currency:statementCurrency(),start:loaded.start,end:loaded.end,rows:loaded.rows,manual:manual(),scenarios:assumptions(),notes:notes(),axes:[$('s53-axis-x').value,$('s53-axis-y').value],title:loaded.symbol+' scenarios',price:Number($('s53-price').value),unknown:$('s53-unknown').value,case:assumptions().find(row=>row.name==='central')};
 const data=await post('/api/v3/scenario53',body);
 if(id!==seq)return data;
 if(action==='save'){savedId=data.id;try{sessionStorage.setItem('md-scenario53',data.id);}catch(error){}render(data.saved.result);$('scenario53-status').textContent='Saved '+data.id+' with the original figures.';await refreshList();return data;}
 if(action==='solve')return data;
 render(data);$('scenario53-status').textContent='Calculated from the figures on screen. Nothing was saved yet.';
 return data;
}
async function refreshList(){
 const response=await fetch('/api/v3/scenario53?part=list',{cache:'no-store'});
 const data=await response.json();
 $('scenario53-saved').innerHTML=(data.saved||[]).map(row=>'<option value="'+esc(row.id)+'">'+esc(row.symbol)+' · '+esc(row.title)+'</option>').join('')||'<option value="">No saved scenario</option>';
}
function mount(){
 const view=$('view-valuation');if(!view||$('scenario53'))return;
 const panel=document.createElement('section');panel.id='scenario53';panel.className='surface';
 const fields=NAMES.map(name=>'<label>'+name+' growth %<input id="s53-'+name+'-growth" type="number" step="0.1" value="'+(name==='cautious'?0:name==='central'?8:15)+'"></label><label>'+name+' margin %<input id="s53-'+name+'-margin" type="number" step="0.1" value="'+(name==='cautious'?10:name==='central'?18:24)+'"></label><label>'+name+' multiple<input id="s53-'+name+'-multiple" type="number" step="0.1" value="'+(name==='cautious'?6:name==='central'?8:10)+'"></label>').join('');
 panel.innerHTML='<div class="section-tag">COMPANY SIMULATOR / FIVE YEARS</div><h3>See the saved years, then the simulated years.</h3><p>Company value uses the existing enterprise multiple on each simulated year. Year 5 is the value for the case. Cash and debt stay at the latest saved amounts. Forecast Lab is separate. Amounts are millions of the statement currency.</p><label>Company <input id="scenario53-symbol" value="TTWO" maxlength="12"></label><button type="button" id="scenario53-load" class="primary-btn">Load saved figures</button><label>Statement currency <input id="s53-currency" value="USD" maxlength="3"></label><div id="scenario53-figures"></div><div class="journal49-actions"><label>Missing revenue, millions <input id="s53-manual-revenue" type="number" step="0.01"></label><input id="s53-note-revenue" placeholder="Source note" maxlength="300"><label>Missing cash, millions <input id="s53-manual-cash" type="number" step="0.01"></label><input id="s53-note-cash" placeholder="Source note" maxlength="300"><label>Missing debt, millions <input id="s53-manual-debt" type="number" step="0.01"></label><input id="s53-note-debt" placeholder="Source note" maxlength="300"><label>Diluted shares, millions <input id="s53-manual-shares" type="number" step="0.0001"></label><input id="s53-note-shares" placeholder="Source note" maxlength="300"></div><label>Method <select id="s53-method"><option>EV/Operating profit</option><option>EV/Sales</option></select></label><div class="journal49-actions">'+fields+'</div><label><input id="scenario53-detail" type="checkbox"> Show the year-by-year calculation</label><label>Dated source <input id="s53-note-date" type="date"></label><input id="s53-note-source" placeholder="Filing or announcement link" maxlength="300"><input id="s53-note-text" placeholder="My assumption about this source" maxlength="500"><label>Horizontal axis <select id="s53-axis-x"><option value="growthPct">Revenue growth</option><option value="marginPct">Operating margin</option><option value="multiple">Multiple</option></select></label><label>Vertical axis <select id="s53-axis-y"><option value="marginPct">Operating margin</option><option value="growthPct">Revenue growth</option><option value="multiple">Multiple</option></select></label><label>Hypothetical share price <input id="s53-price" type="number" step="0.01"></label><label>Solve for <select id="s53-unknown"><option value="growthPct">Revenue growth</option><option value="multiple">Valuation multiple</option></select></label><div class="journal49-actions"><button type="button" id="scenario53-calc" class="primary-btn">Calculate scenarios</button><button type="button" id="scenario53-solve" class="ghost-btn">What would it take?</button><button type="button" id="scenario53-save" class="ghost-btn">Save scenarios</button><button type="button" class="ghost-btn" data-journal="scenario">Save to research</button></div><label>Saved scenario <select id="scenario53-saved"></select></label><button type="button" id="scenario53-open" class="ghost-btn">Reopen saved scenario</button><div class="mdi-prompts"><button type="button" data-scenario-ask="What assumptions produce this value?">Assumptions</button><button type="button" data-scenario-ask="What happens if revenue grows but margins fall?">Growth with lower margins</button><button type="button" data-scenario-ask="What changed this result?">What changed</button><button type="button" data-scenario-ask="Which assumption has the largest effect?">Largest effect</button></div><p id="scenario53-status" role="status"></p><div id="scenario53-output"></div>';
 view.insertBefore(panel,view.children[1]||null);
 $('scenario53-load').onclick=()=>load().catch(error=>{$('scenario53-status').textContent=error.message;});
 $('scenario53-calc').onclick=()=>run('calculate').catch(error=>{$('scenario53-status').textContent=error.message;});
 $('scenario53-solve').onclick=async()=>{try{const data=await run('solve');if(data)$('scenario53-status').textContent=data.status==='solved'?'Required '+data.label+' '+Number(data.value).toFixed(2)+'. '+data.reason:data.reason;}catch(error){$('scenario53-status').textContent=error.message;}};
 $('scenario53-save').onclick=()=>run('save').catch(error=>{$('scenario53-status').textContent=error.message;});
 $('scenario53-open').onclick=async()=>{
  const id=++seq;
  const response=await fetch('/api/v3/scenario53?id='+encodeURIComponent($('scenario53-saved').value),{cache:'no-store'});
  const data=await response.json();
  if(id!==seq)return;
  if(!response.ok||data.error){$('scenario53-status').textContent=data.error||'The scenario could not be opened.';return;}
  savedId=data.saved&&data.id||$('scenario53-saved').value;
  try{sessionStorage.setItem('md-scenario53',$('scenario53-saved').value);}catch(error){}
  loaded=data.saved.figures;result=data.saved.result;render(result);
  $('scenario53-status').textContent='Original scenario kept. Latest saved revenue: '+(data.comparison.latestRevenueM==null?'not saved':data.comparison.latestRevenueM)+'. Saved revenue: '+(data.comparison.originalRevenueM==null?'not saved':data.comparison.originalRevenueM)+'.';
 };
 panel.querySelectorAll('[data-scenario-ask]').forEach(button=>button.onclick=async()=>{
  const ident=sessionStorage.getItem('md-scenario53')||savedId;
  const response=await fetch('/api/v3/ask48?'+new URLSearchParams({question:button.dataset.scenarioAsk,symbol:(loaded&&loaded.symbol)||'TTWO',scenarioId:ident}),{cache:'no-store'});
  const data=await response.json();
  $('scenario53-status').textContent=data.answer||data.error||'';
 });
 refreshList().catch(()=>{});
}
document.addEventListener('DOMContentLoaded',mount);
return {packet,current:()=>result};
})();
