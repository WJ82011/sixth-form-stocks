/* The learning workbench uses only local model output and collector health. */
const Workbench40=(()=>{
  const $=id=>document.getElementById(id);
  const time=t=>Number.isFinite(t)&&t>0?new Date(t).toLocaleString('en-GB'):'Unavailable';
  const num=x=>Number.isFinite(x)?x.toFixed(2):'—';
  const money=x=>Number.isFinite(x)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'USD'}).format(x):'—';
  const jobs={stream:'Finnhub stream',quotes:'Stock quotes',crypto:'Crypto snapshots',cryptoHistory:'Crypto 24-hour history',news:'Company news',marketNews:'Market news',heatmap:'Heatmap history',history:'Daily history',model:'Model training'};
  let revision=0, working=false;
  async function health(){
    try{
      const data=await api('/api/collector');
      $('learning40-collector').textContent=data.lastTrade?'Last captured trade · '+time(data.lastTrade):'Waiting for a captured trade.';
      $('learning40-jobs').innerHTML=Object.entries(data.status||{}).map(([key,value])=>
        '<li><strong>'+escapeHtml(jobs[key]||key)+'</strong> · '+escapeHtml(value)+'</li>').join('');
    }catch{$('learning40-collector').textContent='Local server unavailable.';}
  }
  function render(data){
    const rows=data.rows||[];
    $('learning40-message').textContent=data.closes+' consecutive saved closes · '+(data.anchorDate||'no anchor date')+
      ' · evaluated '+time(data.trainedAt)+(data.stale?' · latest eligible close missing':'');
    const body=rows.map(row=>{
      const eligible=row.status==='learned'&&!data.stale;
      const method=row.status==='insufficient'?'More history needed':row.status==='learned'?'Passed both checks':row.calibrationPassed?'Later test favoured unchanged':'Calibration favoured unchanged';
      return '<tr><td>'+row.horizon+(row.horizon===1?' session':' sessions')+'</td><td>'+row.calibrationCases+' / '+row.testCases+
        '</td><td>'+num(row.calibrationErrorPP)+' / '+num(row.calibrationBaselinePP)+'</td><td>'+num(row.modelErrorPP)+' / '+num(row.baselineErrorPP)+'</td><td>'+method+'</td><td>'+
        (data.stale?'Waiting for latest close':eligible?money(row.price)+' ('+num(row.returnPct)+'%)':row.status==='baseline'?money(data.anchor?.p):'—')+
        '</td><td>'+(eligible?money(row.low)+' to '+money(row.high):'—')+'</td></tr>';
    }).join('');
    $('learning40-results').innerHTML=(data.quality?'<p>'+escapeHtml(data.quality)+'</p>':'')+
      (body?'<div class="v3-table-wrap"><table><thead><tr><th>Horizon</th><th>Calibration / test cases</th><th>Calibration error (pp)</th><th>Test error (pp)</th><th>Assessment</th><th>Scenario</th><th>Illustrative range</th></tr></thead><tbody>'+body+'</tbody></table></div>':'')+
      '<p>Error columns show learned / unchanged in percentage points. Each historical fit uses outcomes known at the time. The earlier calibration block tests the choice of model. The later block checks it against the unchanged-price baseline. The range uses earlier residuals and carries no probability guarantee.</p>';
  }
  async function train(refresh=false){
    if(working)return;
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
      if(id===revision)render(data);
    }catch(error){if(id===revision)$('learning40-message').textContent=error.message;}
    finally{
      working=false;
      $('learning40-train').disabled=$('learning40-refresh').disabled=$('learning40-symbol').disabled=false;
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
    $('learning40-symbol').onchange=()=>train();
    setInterval(()=>{if(E.view==='learning')health();},5000);
  });
  return {open};
})();
