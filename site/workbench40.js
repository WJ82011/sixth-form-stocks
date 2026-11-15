/* The learning workbench uses only local model output and collector health. */
const Workbench40=(()=>{
  const $=id=>document.getElementById(id);
  const time=t=>Number.isFinite(t)&&t>0?new Date(t).toLocaleString('en-GB'):'Unavailable';
  const num=x=>Number.isFinite(x)?x.toFixed(2):'—';
  const money=x=>Number.isFinite(x)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'USD'}).format(x):'—';
  const jobs={stream:'Finnhub stream',quotes:'Stock quotes',crypto:'Crypto snapshots',cryptoHistory:'Crypto 24-hour history',cryptoForecast:'Crypto forecast training',news:'Company news',marketNews:'Market news',heatmap:'Heatmap history',history:'Daily history',model:'Model training'};
  let revision=0, working=false, shown=null, queued=false;
  async function health(){
    if(typeof E!=='undefined'&&E.demoMode){
      $('learning40-collector').textContent='Bundled demo collector · live jobs run on your Mac.';
    }
    try{
      const data=await api('/api/collector');
      $('learning40-collector').textContent=data.notice||data.lastTrade?('Last captured trade · '+time(data.lastTrade)):'Waiting for a captured trade.';
      $('learning40-jobs').innerHTML=Object.entries(data.status||{}).map(([key,value])=>
        '<li><strong>'+escapeHtml(jobs[key]||key)+'</strong> · '+escapeHtml(value)+'</li>').join('');
    }catch{$('learning40-collector').textContent='Local server unavailable.';}
  }
  function render(data){
    const rows=data.rows||[];
    const cover=data.coverage||{};
    $('learning40-message').textContent=(data.symbol||'')+' · last trained '+time(data.trainedAt)+
      ' · latest saved price '+(Number.isFinite(cover.latestSavedPrice)?money(cover.latestSavedPrice):'unavailable')+
      (cover.latestSavedDate?' on '+cover.latestSavedDate:'')+
      ' · '+((cover.usedCloses)||0)+' closes used'+(cover.droppedForGap?' · '+cover.droppedForGap+' earlier closes left out because a session is missing':'')+
      (data.stale?' · latest eligible close missing':'')+'. '+(cover.source||'');
    const body=rows.map(row=>{
      const eligible=row.status==='learned'&&!data.stale;
      const method=row.status==='insufficient'?'More history needed':row.status==='learned'?'Passed both checks':row.calibrationPassed?'Later test favoured unchanged':'Calibration favoured unchanged';
      return '<tr><td>'+row.horizon+(row.horizon===1?' session':' sessions')+'</td><td>'+row.calibrationCases+' / '+row.testCases+
        '</td><td>'+num(row.calibrationErrorPP)+' / '+num(row.calibrationBaselinePP)+'</td><td>'+num(row.modelErrorPP)+' / '+num(row.baselineErrorPP)+'</td><td>'+method+'</td><td>'+
        (data.stale?'Waiting for latest close':eligible?money(row.price)+' ('+num(row.returnPct)+'%)':row.status==='baseline'?money(data.anchor?.p):'—')+
        '</td><td>'+(eligible?money(row.low)+' to '+money(row.high):'—')+'</td></tr>';
    }).join('');
    $('learning40-results').innerHTML='<h3>Historical backtest</h3><p>This table is recalculated from saved prices. It is not the permanent forecast record.</p>'+(data.quality?'<p>'+escapeHtml(data.quality)+'</p>':'')+
      (body?'<div class="v3-table-wrap"><table><thead><tr><th>Horizon</th><th>Calibration / test cases</th><th>Calibration error (pp)</th><th>Test error (pp)</th><th>Assessment</th><th>Scenario</th><th>Illustrative range</th></tr></thead><tbody>'+body+'</tbody></table></div>':'')+
      '<p>Error columns show learned / unchanged in percentage points. Each historical fit uses outcomes known at the time. The earlier calibration block tests the choice of model. The later block checks it against the unchanged-price baseline. The range uses earlier residuals and carries no probability guarantee.</p>'+
      labView(data);
    renderScore(data.scorecard);
  }
  function spark(rows){
    const values=(rows||[]).map(row=>row.actualPrice).filter(value=>Number.isFinite(value));
    if(values.length<2)return '';
    const low=Math.min(...values), high=Math.max(...values);
    const path=values.map((value,index)=>{
      const x=index/(values.length-1)*280;
      const y=42-((value-low)/((high-low)||1))*36;
      return (index?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);
    }).join(' ');
    return '<svg class="lab45-spark" viewBox="0 0 280 48" width="280" height="48" aria-hidden="true"><path d="'+path+'" fill="none" stroke="#1d4ed8" stroke-width="2"/></svg>';
  }
  function labView(data){
    const blocks=(data.lab||[]).map(row=>{
      const models=(row.models||[]).map(model=>'<tr><td>'+escapeHtml(model.name)+'</td><td>'+escapeHtml((model.start||'Date unavailable')+' → '+(model.end||''))+'</td><td>'+model.count+'</td><td>'+num(model.averageErrorPP)+'</td><td>'+(model.rangeCoveragePct==null?'—':num(model.rangeCoveragePct)+'%')+'</td></tr>').join('');
      const misses=(row.misses||[]).map((miss,index)=>'<tr><td>'+escapeHtml(miss.anchorDate||'—')+'</td><td>'+escapeHtml(miss.targetDate||'—')+'</td><td>'+money(miss.forecastPrice)+'</td><td>'+money(miss.baselinePrice)+'</td><td>'+money(miss.actualPrice)+'</td><td><button type="button" data-lab-horizon="'+row.horizon+'" data-lab-miss="'+index+'">Open</button></td></tr>').join('');
      return '<section class="lab45-block"><h3>'+row.horizon+' trading session'+(row.horizon===1?'':'s')+'</h3><div class="lab45-note">'+spark(row.path)+'<p>'+escapeHtml(row.reason||'')+(row.shrinkage!=null?' Shrinkage '+row.shrinkage+' was chosen on the earlier dates ('+(row.calibration?.count||0)+' forecasts).':'')+(row.durability?' Recent dates '+num(row.durability.lateErrorPP)+' pp versus unchanged '+num(row.durability.lateBaselineErrorPP)+' pp. Range coverage '+num(row.durability.rangeCoveragePct)+'% against an expected '+row.durability.expectedCoveragePct+'%.':'')+'</p></div>'+(models?'<div class="v3-table-wrap"><table><thead><tr><th>Model</th><th>Dates tested</th><th>Forecasts</th><th>Average error (pp)</th><th>Close inside range</th></tr></thead><tbody>'+models+'</tbody></table></div>':'')+(misses?'<h3>Largest misses on the later test</h3><div class="v3-table-wrap"><table><thead><tr><th>Decision</th><th>Target</th><th>Volatility forecast</th><th>Unchanged</th><th>Actual</th><th></th></tr></thead><tbody>'+misses+'</tbody></table></div>':'')+'</section>';
    }).join('');
    return '<h3>Forecast Lab</h3><p>This is a historical backtest. It is kept separate from forecasts Market Desk issued in real time. All three rows in a horizon use the same dates. The later dates were not used to choose the model.</p>'+blocks+'<div id="learning40-detail"></div>';
  }
  function openMiss(horizon,index){
    const row=(shown?.lab||[]).find(item=>item.horizon===Number(horizon));
    const miss=row?.misses?.[Number(index)];
    const box=$('learning40-detail');
    if(!miss||!box)return;
    const known=(miss.inputs||[]).filter(item=>!miss.anchorDate||!item.date||item.date<=miss.anchorDate);
    const range=Number.isFinite(miss.low)?money(miss.low)+' to '+money(miss.high):'No range was saved for this case.';
    box.innerHTML='<h3>One miss</h3><p>Decision '+escapeHtml(miss.anchorDate||'date unavailable')+' · target '+escapeHtml(miss.targetDate||'date unavailable')+'.</p><p>Volatility forecast '+money(miss.forecastPrice)+'. Range '+escapeHtml(range)+'. Unchanged price '+money(miss.baselinePrice)+'. Actual close '+money(miss.actualPrice)+'.</p><p>Current-model price on this same decision: '+money(miss.currentPrice)+'. Error '+num(miss.errorPP)+' pp against an unchanged-price error of '+num(miss.baselineErrorPP)+' pp. '+(miss.inRange?'The actual close landed inside the range.':'The actual close landed outside the range.')+'</p><p>The model could use saved closes through the decision date. The actual close was not an input.</p><ul>'+known.map(item=>'<li>'+escapeHtml(item.date)+' · '+money(item.price)+'</li>').join('')+'</ul>';
  }
  function openIssued(id){
    const card=shown?.scorecard||{};
    const row=[...(card.pending||[]),...(card.graded||[])].find(item=>item.id===id);
    const box=$('learning40-detail');
    if(!row||!box)return;
    const outcome=row.outcome;
    const result=!outcome?'The target close is not saved yet.':outcome.status==='scored'
      ?'Actual close '+money(outcome.actualPrice)+'. Error '+num(outcome.absoluteErrorPP)+' pp. Unchanged-price error '+num(outcome.unchangedErrorPP)+' pp. '+(outcome.inRange?'Inside the range.':'Outside the range.')
      :(outcome.reason||outcome.status);
    const known=(row.knownCloses||[]).slice(-12);
    box.innerHTML='<h3>Issued forecast</h3><p>'+escapeHtml(row.symbol)+' · '+escapeHtml(row.method||'')+' · issued '+escapeHtml(time(row.issuedAt))+'.</p><p>Prediction '+money(row.forecastPrice)+'. Range '+money(row.low)+' to '+money(row.high)+'. Unchanged price '+money(row.baselinePrice)+'.</p><p>'+escapeHtml(result)+'</p><p>'+(known.length?'Prices saved with this forecast, through '+(row.knownThrough||'the decision date')+'.':'This older record did not keep the price window. The prediction itself is unchanged.')+'</p><ul>'+known.map(item=>'<li>'+escapeHtml(item.date)+' · '+money(item.price)+'</li>').join('')+'</ul><p>Training again does not replace this record.</p>';
  }
  function issuedRow(row){
    const outcome=row.outcome;
    const grade=!outcome?'Waiting for the target close':outcome.status==='scored'
      ?num(outcome.absoluteErrorPP)+' pp error · unchanged '+num(outcome.unchangedErrorPP)+' pp · '+(outcome.inRange?'inside range':'outside range')+' · '+(outcome.beatBaseline?'beat the baseline':'did not beat the baseline')
      :outcome.reason||outcome.status;
    return '<tr><td>'+escapeHtml(row.anchorDay)+'</td><td>'+row.horizon+'</td><td>'+escapeHtml(row.targetDay)+'</td><td>'+money(row.anchorPrice)+'</td><td>'+money(row.low)+' to '+money(row.high)+'</td><td>'+escapeHtml(row.method||'')+'</td><td>'+time(row.issuedAt)+'</td><td>'+grade+'</td><td><button type="button" data-issued-id="'+escapeHtml(row.id)+'">Open</button></td></tr>';
  }
  function renderScore(card){
    const box=$('learning40-scorecard');
    if(!box)return;
    if(!card){box.innerHTML='';return;}
    const summary=card.summary||{};
    const sample=summary.count?summary.count+' graded forecast'+(summary.count===1?'':'s')+' · average error '+num(summary.averageErrorPP)+' pp · unchanged-price error '+num(summary.baselineAverageErrorPP)+' pp · range contained the close in '+num(summary.rangeCoveragePct)+'% of '+summary.rangeCount+' graded ranges · '+(summary.beatBaseline?'the model beat the unchanged-price baseline on average':'the model did not beat the unchanged-price baseline on average')+'.':'No graded issued forecast yet. Sample size is 0. A backtest above is not counted here.';
    const table=rows=>rows.length?'<div class="v3-table-wrap"><table><thead><tr><th>Issued from</th><th>Horizon</th><th>Target session</th><th>Original price</th><th>Forecast range</th><th>Model</th><th>Issued</th><th>Result</th><th></th></tr></thead><tbody>'+rows.map(issuedRow).join('')+'</tbody></table></div>':'<p>None yet.</p>';
    box.innerHTML='<h3>Issued forecasts</h3><p>'+escapeHtml(card.message||'')+'</p><p>'+escapeHtml(sample)+'</p><h3>Pending</h3>'+table(card.pending||[])+'<h3>Graded</h3>'+table(card.graded||[])+'<p>'+escapeHtml(card.notice||'')+' '+escapeHtml(card.backtestNotice||'')+'</p>';
  }
  async function train(refresh=false){
    if(typeof E!=='undefined'&&E.demoMode&&refresh){
      $('learning40-message').textContent='Live price training needs server.py on your Mac.';
      $('learning40-collector').textContent='Background collector runs on your Mac · not on this public demo.';
      toast('Training from live prices needs server.py on your Mac. The bundled Forecast Lab below uses the demo snapshot.');
      return;
    }
    if(working){queued=true;return}
    const symbol=$('learning40-symbol').value;
    if(!symbol)return;
    const id=++revision;
    working=true;
    $('learning40-train').disabled=$('learning40-refresh').disabled=$('learning40-symbol').disabled=true;
    $('learning40-message').textContent=refresh?'Requesting eligible daily prices…':'Evaluating saved prices…';
    try{
      if(refresh){
        const end=Math.floor(Date.now()/1000);
        const query=new URLSearchParams({symbol,resolution:'D',from:String(end-731*86400),to:String(end),refresh:'1'});
        const response=await api('/api/candles?'+query);
        if(response.status!=='ok'||response.provider!=='massive')throw Error(response.message||'An active Massive connection is needed for this training source.');
      }
      const data=await api('/api/v3/learning?symbol='+encodeURIComponent(symbol));
      if(id!==revision||$('learning40-symbol').value!==symbol)return;
      shown=data;render(data);
    }catch(error){if(id===revision)$('learning40-message').textContent=error.message;}
    finally{
      working=false;
      $('learning40-train').disabled=$('learning40-refresh').disabled=$('learning40-symbol').disabled=false;
      if(queued){queued=false;train(false)}
    }
  }
  function open(){
    const picker=$('learning40-symbol'),choice=picker.value||E.selected;
    if(!working){
      picker.innerHTML=STOCK_DIRECTORY.map(row=>'<option value="'+escapeHtml(row.symbol)+'">'+escapeHtml(row.symbol+' · '+row.name)+'</option>').join('');
      if(DIRECTORY_BY_SYMBOL[choice])picker.value=choice;
      train();
    }
    health();
  }
  document.addEventListener('DOMContentLoaded',()=>{
    $('learning40-train').onclick=()=>train();
    $('learning40-refresh').onclick=()=>train(true);
    $('learning40-symbol').onchange=()=>{shown=null;$('learning40-results').innerHTML='';$('learning40-scorecard').innerHTML='';train()};
    if(new URLSearchParams(location.search).get('lab45')==='1'){
      const marker=document.createElement('p');
      marker.id='lab45-result';
      marker.textContent='RUNNING';
      document.documentElement.append(marker);
      const wait=(test,left=100)=>new Promise(resolve=>{const tick=()=>{if(test()||left<=0)resolve(test());else{left--;setTimeout(tick,50)}};tick()});
      (async()=>{
        const picker=$('learning40-symbol');
        if(!picker.options.length&&typeof STOCK_DIRECTORY!=='undefined')picker.innerHTML=STOCK_DIRECTORY.map(row=>'<option value="'+row.symbol+'">'+row.symbol+'</option>').join('');
        const run=async symbol=>{picker.value=symbol;picker.dispatchEvent(new Event('change'));return wait(()=>$('learning40-message').textContent.startsWith(symbol)&&$('learning40-results').textContent.includes('Forecast Lab'))};
        const ttwo=await run('TTWO');
        const withheld=$('learning40-results').textContent.includes('No volatility forecast was released');
        const amd=await run('AMD');
        const apple=await run('AAPL');
        const clear=! $('learning40-message').textContent.includes('TTWO') && !$('learning40-results').textContent.includes('TTWO');
        marker.textContent=[ttwo&&withheld?'PASS Take-Two lab':'FAIL Take-Two lab', amd?'PASS AMD replaces Take-Two':'FAIL AMD replaces Take-Two', apple&&clear?'PASS Apple replaces AMD':'FAIL Apple replaces AMD'].join(' | ');
      })().catch(error=>{marker.textContent='FAIL '+error.message});
    }
    document.getElementById('view-learning').addEventListener('click',event=>{
      const miss=event.target.closest('[data-lab-miss]');
      if(miss){openMiss(miss.dataset.labHorizon,miss.dataset.labMiss);return}
      const issued=event.target.closest('[data-issued-id]');
      if(issued)openIssued(issued.dataset.issuedId);
    });
    setInterval(()=>{if(E.view==='learning')health();},5000);
  });
  return {open};
})();
