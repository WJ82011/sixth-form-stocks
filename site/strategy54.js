/* Strategy Lab. Saved daily bars, locked rules, and a record that stays out of the practice portfolio. */
(function(){
 const $=id=>document.getElementById(id);
 let seq=0,last=null,savedId='',step=0,inspected=false,locked='';
 const markers=[];
 function esc(value){return String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
 function post(url,body){return fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(async response=>{const data=await response.json();if(!response.ok||data.error)throw new Error(data.error||'The strategy could not be run.');return data;});}
 function rule(){
  const stop=$('s54-stop-on').checked?Number($('s54-stop').value):0;
  return {symbol:$('s54-symbol').value,start:$('s54-start').value,end:$('s54-end').value,laterStart:$('s54-later-start').value,laterEnd:$('s54-later-end').value,
   entry:side('entry'),exit:side('exit'),stopPct:stop,cash:Number($('s54-cash').value),sizePct:Number($('s54-size').value),costPct:Number($('s54-cost').value),slippagePct:Number($('s54-slip').value),
   inspectedLater:inspected,lockedFingerprint:locked,title:$('s54-symbol').value+' strategy'};
 }
 function side(name){
  const kind=$('s54-'+name+'-kind').value;
  return kind==='sma_cross'?{kind,fast:Number($('s54-'+name+'-fast').value),slow:Number($('s54-'+name+'-slow').value)}:{kind,lookback:Number($('s54-'+name+'-look').value)};
 }
 function packet(){
  const result=last&&last.development;if(!result)return null;
  return {origin:'strategy',symbol:last.symbol,range:'1Y',start:result.start,end:result.end,evidence:{source:result.coverage&&result.coverage.source||'',answer:last.plainEnglish,basis:'Strategy Lab simulation',qualification:result.portfolioNote||'',endPrice:result.endingValue>0&&result.endingValue<=1e9?result.endingValue:null,capturedAt:Date.now()}};
 }
 function paint(result){
  const canvas=$('s54-chart');if(!canvas||!result)return;
  const curve=result.curve||[],trades=result.trades||[];
  const width=canvas.width=canvas.clientWidth||640,height=canvas.height=180,ctx=canvas.getContext('2d');
  ctx.clearRect(0,0,width,height);if(curve.length<2)return;
  const values=curve.map(point=>point.equity),low=Math.min(...values),high=Math.max(...values),span=high-low||1;
  ctx.strokeStyle='#2f6fed';ctx.lineWidth=2;ctx.beginPath();
  curve.forEach((point,index)=>{const x=20+(width-40)*index/(curve.length-1),y=height-20-(point.equity-low)/span*(height-40);index?ctx.lineTo(x,y):ctx.moveTo(x,y);});
  ctx.stroke();
  trades.forEach(trade=>{const index=curve.findIndex(point=>point.date===trade.executeDate);if(index<0)return;const x=20+(width-40)*index/(curve.length-1),y=height-20-(curve[index].equity-low)/span*(height-40);ctx.fillStyle=trade.side==='buy'?'#2f6fed':'#c4493a';ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fill();});
 }
 function showTrade(trade){
  if(!trade){$('s54-detail').textContent='Open a trade to see the bars that triggered it.';return;}
  const rows=(trade.observations||[]).map(row=>row.date+' close '+Number(row.close).toFixed(2)).join('; ');
  $('s54-detail').textContent=trade.side+' signal '+trade.signalDate+' · '+trade.reason+' Observations: '+(rows||'none')+'. Executed '+trade.executeDate+' at '+Number(trade.executePrice).toFixed(4)+', fill '+Number(trade.fillPrice).toFixed(4)+'. '+trade.calculation+' Flags: '+(trade.flags||[]).join(', ');
 }
 function render(data){
  last=data;const root=$('s54-output');if(!root)return;
  const blocks=[data.development,data.later].filter(Boolean).map(result=>{
   const hold=result.buyAndHold||{};
   return '<article class="fh-compare-card"><p class="desk-eyebrow">'+(result===data.development?'DEVELOPMENT':'LATER PERIOD')+'</p><p>'+esc(result.start)+' to '+esc(result.end)+' · '+esc(result.coverage&&result.coverage.frequency)+'</p><p>Ending value '+Number(result.endingValue).toFixed(2)+' · return '+(result.totalReturn*100).toFixed(2)+'% · largest drop '+Number(result.maxDrawdown).toFixed(2)+' · costs '+Number(result.costs).toFixed(2)+' · completed trades '+result.tradeCount+' · orders '+result.fills+' · shares still open '+Number(result.endingShares).toFixed(4)+'</p><p>Buy and hold ending value '+Number(hold.endingValue||0).toFixed(2)+' · return '+((hold.totalReturn||0)*100).toFixed(2)+'%. '+esc(hold.note||'')+'</p><p>'+esc(result.dividendNote)+'</p><p>'+esc(result.coverage&&result.coverage.notice)+'</p><p>'+(result.coverage&&result.coverage.missingCount?result.coverage.missingCount+' missing sessions in this period.':'The saved sessions in this period are complete.')+'</p>'+(result.notes||[]).map(note=>'<p>'+esc(note)+'</p>').join('')+'</article>';
  }).join('');
  const trades=(data.development&&data.development.trades||[]).concat(data.later&&data.later.trades||[]);
  root.innerHTML='<p>'+esc(data.plainEnglish)+'</p><ul>'+(data.assumptions||[]).map(item=>'<li>'+esc(item)+'</li>').join('')+'</ul><p>'+esc(data.changeNote||'')+'</p><div class="fh-compare-cards">'+blocks+'</div><div class="journal49-actions"><button type="button" id="s54-prev" class="ghost-btn">Previous trade</button><button type="button" id="s54-next" class="ghost-btn">Next trade</button></div><div id="s54-trades">'+trades.map((trade,index)=>'<button type="button" data-s54-trade="'+index+'">'+esc(trade.executeDate)+' · '+esc(trade.side)+' · '+Number(trade.fillPrice).toFixed(2)+'</button>').join('')+'</div><p id="s54-detail"></p>';
  step=0;showTrade(trades[0]);
  $('s54-prev').onclick=()=>{step=Math.max(0,step-1);showTrade(trades[step]);};
  $('s54-next').onclick=()=>{step=Math.min(trades.length-1,step+1);showTrade(trades[step]);};
  root.querySelectorAll('[data-s54-trade]').forEach(button=>button.onclick=()=>{step=Number(button.dataset.s54Trade);showTrade(trades[step]);});
  paint(data.development);
  markers.length=0;trades.forEach(trade=>{if(trade.executeTs)markers.push({t:trade.executeTs,kind:trade.side});});
  if(window.E&&E.selected===data.symbol&&typeof drawChart==='function')drawChart();
  if(data.later){inspected=true;locked=data.fingerprint;}
 }
 async function run(action){
  const id=++seq,body={action,...rule()};
  const data=await post('/api/v3/strategy54',body);
  if(id!==seq)return data;
  if(action==='preview'){$('s54-status').textContent=data.plainEnglish;return data;}
  if(action==='save'){savedId=data.id;render(data.saved.result);$('s54-status').textContent='Saved '+data.id+' on this Mac. The practice portfolio was not changed.';await refresh();return data;}
  render(data);$('s54-status').textContent='Calculated from saved daily bars. Nothing was saved yet.';
  return data;
 }
 async function refresh(){
  const response=await fetch('/api/v3/strategy54?part=list',{cache:'no-store'});
  const data=await response.json();
  $('s54-saved').innerHTML=(data.saved||[]).map(row=>'<option value="'+esc(row.id)+'">'+esc(row.symbol)+' · '+esc(row.title)+'</option>').join('')||'<option value="">No saved strategy</option>';
 }
 function mount(){
  const view=$('view-indicators');if(!view||$('strategy54'))return;
  const panel=document.createElement('section');panel.id='strategy54';panel.className='surface';
  panel.innerHTML='<div class="section-tag">STRATEGY LAB / SAVED DAILY BARS</div><h3>Describe the rule, then test it.</h3><p>Choose a company and two date ranges. The later range uses the same locked settings. This record stays separate from the practice portfolio and from chart replay.</p><label>Company <select id="s54-symbol"><option>TTWO</option><option>AMD</option><option>AAPL</option></select></label><label>Development start <input id="s54-start" type="date" value="2026-01-02"></label><label>Development end <input id="s54-end" type="date" value="2026-06-30"></label><label>Later start <input id="s54-later-start" type="date" value="2026-07-01"></label><label>Later end <input id="s54-later-end" type="date" value="2026-11-12"></label><label>Entry <select id="s54-entry-kind"><option value="sma_cross">Moving-average cross</option><option value="breakout">Price breakout</option></select></label><label>Fast days <input id="s54-entry-fast" type="number" value="20"></label><label>Slow days <input id="s54-entry-slow" type="number" value="50"></label><label>Breakout sessions <input id="s54-entry-look" type="number" value="20"></label><label>Exit <select id="s54-exit-kind"><option value="sma_cross">Moving-average cross</option><option value="breakout">Price breakout</option></select></label><label>Fast days <input id="s54-exit-fast" type="number" value="20"></label><label>Slow days <input id="s54-exit-slow" type="number" value="50"></label><label>Breakout sessions <input id="s54-exit-look" type="number" value="20"></label><label><input id="s54-stop-on" type="checkbox"> Stop-loss</label><label>Stop % <input id="s54-stop" type="number" value="8" step="0.1"></label><label>Starting cash <input id="s54-cash" type="number" value="10000"></label><label>Position size % <input id="s54-size" type="number" value="100"></label><label>Cost % <input id="s54-cost" type="number" value="0" step="0.01"></label><label>Slippage % <input id="s54-slip" type="number" value="0" step="0.01"></label><div class="journal49-actions"><button type="button" id="s54-preview" class="ghost-btn">Describe the rule</button><button type="button" id="s54-run" class="primary-btn">Test the rule</button><button type="button" id="s54-save" class="ghost-btn">Save experiment</button><button type="button" class="ghost-btn" data-journal="strategy">Save to research</button></div><canvas id="s54-chart" style="width:100%;height:180px"></canvas><label>Saved experiment <select id="s54-saved"></select></label><button type="button" id="s54-open" class="ghost-btn">Reopen saved experiment</button><p id="s54-status" role="status"></p><div id="s54-output"></div>';
  view.insertBefore(panel,view.children[1]||null);
  $('s54-preview').onclick=()=>run('preview').catch(error=>{$('s54-status').textContent=error.message;});
  $('s54-run').onclick=()=>run('run').catch(error=>{$('s54-status').textContent=error.message;});
  $('s54-save').onclick=()=>run('save').catch(error=>{$('s54-status').textContent=error.message;});
  $('s54-open').onclick=async()=>{
   const id=++seq;
   const response=await fetch('/api/v3/strategy54?id='+encodeURIComponent($('s54-saved').value),{cache:'no-store'});
   const data=await response.json();
   if(id!==seq)return;
   if(data.error){$('s54-status').textContent=data.error;return;}
   render(data.saved.result);$('s54-status').textContent=data.notice;
  };
  ['s54-start','s54-end','s54-later-start','s54-later-end','s54-entry-fast','s54-entry-slow','s54-exit-fast','s54-exit-slow','s54-cash','s54-size','s54-cost','s54-slip','s54-stop'].forEach(id=>{const node=$(id);if(node)node.addEventListener('change',()=>{if(inspected)$('s54-status').textContent='The later period has been inspected. Running again will record that the settings changed.';});});
  refresh().catch(()=>{});
 }
 document.addEventListener('DOMContentLoaded',mount);
 window.Strategy54={packet,get markers(){return markers;}};
})();
