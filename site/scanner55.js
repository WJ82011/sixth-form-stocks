/* Market Scanner. Cards are a view of one saved result; sorting does not rerun it. */
(function(){
 const $=id=>document.getElementById(id);
 let seq=0,last=null,savedId='';
 function esc(value){return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
 function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(async response=>{const data=await response.json();if(!response.ok||data.error)throw new Error(data.error||'The scan could not be run.');return data;});}
 function conditions(){
  const chosen=[];
  if($('s55-move').checked)chosen.push($('s55-move-mode').value==='history'?{kind:'session_move',threshold:'history',percentile:90}:{kind:'session_move',threshold:Number($('s55-move-threshold').value)});
  if($('s55-average').checked)chosen.push({kind:'above_average',sessions:Number($('s55-average-sessions').value)});
  if($('s55-high').checked)chosen.push({kind:'closing_high',sessions:Number($('s55-high-sessions').value)});
  if($('s55-volume').checked)chosen.push({kind:'unusual_volume',percentile:90});
  return chosen;
 }
 function body(action){return {action,id:savedId,title:$('s55-title').value||'Saved scan',conditions:conditions(),alert:$('s55-alert').checked,schedule:$('s55-schedule').checked,preset:$('s55-preset').value};}
 function packet(){
  const card=last&&last.matches&&last.matches[0];if(!card)return null;
  return {origin:'scan',symbol:card.symbol,range:'1M',start:card.start,end:card.end,evidence:{source:card.source,answer:card.calculation,basis:'Market Scanner',qualification:last.notice||'',endPrice:card.close>0&&card.close<=1e9?card.close:null,capturedAt:Date.now()}};
 }
 function paint(){
  const root=$('s55-output');if(!root||!last)return;
  const query=($('s55-filter').value||'').trim().toUpperCase();
  const shown=last.matches.filter(match=>!query||match.symbol.includes(query)||String(match.name||'').toUpperCase().includes(query));
  const key=$('s55-sort').value;
  shown.sort((a,b)=>key==='symbol'?a.symbol.localeCompare(b.symbol):(Number(b[key])||0)-(Number(a[key])||0));
  const counts=last.counts||{};
  root.innerHTML='<p>'+esc(last.plainEnglish)+'</p><p>Checked '+counts.checked+' · matched '+counts.matched+' · not enough data '+counts.insufficient+' · stale '+counts.stale+' · missing sessions '+counts.gap+' · split-sized '+counts.split+' · incomplete volume '+(counts.incompleteVolume||0)+'</p><div class="fh-compare-cards">'+shown.map(match=>'<article class="fh-compare-card"><button type="button" data-scan-symbol="'+esc(match.symbol)+'" data-scan-start="'+esc(match.start)+'" data-scan-end="'+esc(match.end)+'" data-scan-start-ts="'+(match.startTs||'')+'" data-scan-end-ts="'+(match.endTs||'')+'"><strong>'+esc(match.symbol)+'</strong> '+esc(match.name||'')+'</button><p>'+esc(match.calculation)+'</p><p>Measured '+Number(match.measured).toFixed(2)+' · comparison '+Number(match.comparison).toFixed(2)+' · '+esc(match.date)+' · '+esc(match.source)+'</p><p>'+esc(match.change||'')+'</p></article>').join('')+'</div><details><summary>Omissions</summary>'+(last.omissions||[]).slice(0,40).map(item=>'<p>'+esc(item.symbol)+' · '+esc(item.reason)+' · '+esc(item.detail)+'</p>').join('')+'</details>';
  root.querySelectorAll('[data-scan-symbol]').forEach(button=>button.onclick=()=>{
   const symbol=button.dataset.scanSymbol,start=button.dataset.scanStart,end=button.dataset.scanEnd;
   const startTs=Number(button.dataset.scanStartTs),endTs=Number(button.dataset.scanEndTs);
   try{
    if(typeof E!=='undefined')E.investigation={symbol,start,end,scanId:savedId};
    if(window.changeView)window.changeView(document.body.classList.contains('look43-on')?'home':'overview');
    if(window.setChartRange)window.setChartRange('1M');
    if(window.setSelected)window.setSelected(symbol);
    if(window.Chart43&&startTs&&endTs)window.Chart43.setWindow(startTs,endTs);
   }catch(error){}
   setTimeout(()=>{if(window.Move44)window.Move44.open({symbol,start,end});},450);
  });
 }
 async function run(action){
  const id=++seq;
  const data=await post('/api/v3/scanner55',body(action));
  if(id!==seq)return data;
  if(action==='explain'){$('s55-status').textContent=data.plainEnglish;return data;}
  if(action==='save'){savedId=data.id;try{sessionStorage.setItem('md-scanner55',data.id);}catch(error){}last=data.result;paint();$('s55-status').textContent='Saved '+data.id+'. Alerts created '+data.result.alertsCreated+'.';await refresh();return data;}
  last=data;paint();$('s55-status').textContent='Checked '+data.counts.checked+' companies from saved bars.';
  return data;
 }
 async function refresh(){
  const response=await fetch('/api/v3/scanner55?part=list',{cache:'no-store'});
  const data=await response.json();
  $('s55-saved').innerHTML=(data.saved||[]).map(row=>'<option value="'+esc(row.id)+'">'+esc(row.title)+'</option>').join('')||'<option value="">No saved scan</option>';
 }
 function applyPreset(preset){
  $('s55-title').value=preset.title;$('s55-move').checked=preset.conditions.some(item=>item.kind==='session_move');
  $('s55-average').checked=preset.conditions.some(item=>item.kind==='above_average');
  $('s55-high').checked=preset.conditions.some(item=>item.kind==='closing_high');
  $('s55-volume').checked=preset.conditions.some(item=>item.kind==='unusual_volume');
  $('s55-status').textContent=preset.plainEnglish;
 }
 function mount(){
  const view=$('view-screener');if(!view||$('scanner55'))return;
  const panel=document.createElement('section');panel.id='scanner55';panel.className='surface';
  panel.innerHTML='<div class="section-tag">MARKET SCANNER / SAVED DAILY BARS</div><h3>Build a scan from conditions.</h3><p>Each condition uses saved daily bars. A historical threshold is calculated from earlier observations and does not include the latest one.</p><div class="journal49-actions"><button type="button" data-preset="large-move" class="ghost-btn">Large daily move</button><button type="button" data-preset="above-average" class="ghost-btn">Above its recent average</button><button type="button" data-preset="closing-high" class="ghost-btn">New closing high</button></div><label>Name <input id="s55-title" value="Large daily move" maxlength="80"></label><label><input id="s55-move" type="checkbox" checked> Completed-session move</label><label>Threshold <select id="s55-move-mode"><option value="history">Historical percentile</option><option value="fixed">Fixed percent</option></select></label><label>Fixed % <input id="s55-move-threshold" type="number" value="5" step="0.1"></label><label><input id="s55-average" type="checkbox"> Above its average</label><label>Sessions <input id="s55-average-sessions" type="number" value="20"></label><label><input id="s55-high" type="checkbox"> New closing high</label><label>Earlier closes <input id="s55-high-sessions" type="number" value="20"></label><label><input id="s55-volume" type="checkbox"> Unusual daily volume</label><label><input id="s55-alert" type="checkbox"> Alert when a company newly qualifies</label><label><input id="s55-schedule" type="checkbox"> Run with the background schedule</label><input id="s55-preset" type="hidden" value=""><label>Show <input id="s55-filter" placeholder="Filter the cards"></label><label>Sort <select id="s55-sort"><option value="symbol">Symbol</option><option value="measured">Measured value</option></select></label><div class="journal49-actions"><button type="button" id="s55-explain" class="ghost-btn">Explain the conditions</button><button type="button" id="s55-run" class="primary-btn">Scan saved bars</button><button type="button" id="s55-save" class="ghost-btn">Save scan</button><button type="button" id="s55-refresh" class="ghost-btn">Refresh up to five stale histories</button><button type="button" class="ghost-btn" data-journal="scan">Save to research</button><button type="button" id="s55-why" class="ghost-btn">Why did this company match?</button></div><label>Saved scan <select id="s55-saved"></select></label><button type="button" id="s55-open" class="ghost-btn">Reopen saved scan</button><p id="s55-status" role="status"></p><div id="s55-output"></div>';
  view.insertBefore(panel,view.children[1]||null);
  panel.querySelectorAll('[data-preset]').forEach(button=>button.onclick=async()=>{
   const response=await fetch('/api/v3/scanner55?part=presets',{cache:'no-store'});
   const data=await response.json();
   const preset=(data.presets||[]).find(item=>item.id===button.dataset.preset);
   if(preset)applyPreset(preset);
  });
  $('s55-explain').onclick=()=>run('explain').catch(error=>{$('s55-status').textContent=error.message;});
  $('s55-run').onclick=()=>run('run').catch(error=>{$('s55-status').textContent=error.message;});
  $('s55-save').onclick=()=>run('save').catch(error=>{$('s55-status').textContent=error.message;});
  $('s55-filter').oninput=paint;$('s55-sort').onchange=paint;
  $('s55-refresh').onclick=async()=>{
   const symbols=(last&&last.omissions||[]).filter(item=>item.reason==='stale'||item.reason==='insufficient').slice(0,5).map(item=>item.symbol);
   const data=await post('/api/v3/scanner55',{action:'refresh',symbols});
   $('s55-status').textContent=data.notice+' Requested '+data.requested+'.';
  };
  $('s55-open').onclick=async()=>{
   const id=++seq;
   const response=await fetch('/api/v3/scanner55?id='+encodeURIComponent($('s55-saved').value),{cache:'no-store'});
   const data=await response.json();
   if(id!==seq)return;
   if(data.error){$('s55-status').textContent=data.error;return;}
   savedId=$('s55-saved').value;last=data.result;paint();$('s55-status').textContent=data.notice;
  };
  $('s55-why').onclick=()=>{
   const symbol=last&&last.matches&&last.matches[0]&&last.matches[0].symbol;if(!symbol||!savedId){$('s55-status').textContent='Save the scan first.';return;}
   const match=last.matches[0];
   if(window.Ask48){Ask48.openFrom({symbol,scanId:savedId,start:match.start,end:match.end});Ask48.ask('Why did this company match?');}
  };
  refresh().catch(()=>{});
 }
 document.addEventListener('DOMContentLoaded',mount);
 window.Scanner55={packet};
})();
