/* Market Desk v1.8 — official annual macro data + independent historical accuracy review. */
'use strict';
let macroPayload=null,macroBusy=false,accuracyBusy=false;
const MACRO_KEYS=[
 ['NY.GDP.MKTP.KD.ZG','Real GDP growth','% YoY'],
 ['FP.CPI.TOTL.ZG','Consumer price inflation','% YoY'],
 ['SL.UEM.TOTL.ZS','Unemployment (ILO modelled)','%'],
 ['NE.EXP.GNFS.ZS','Exports of goods/services','% of GDP'],
 ['FR.INR.LEND','Lending interest rate','% (not policy rate)']
];
const MACRO_EXPLAIN={
 'NY.GDP.MKTP.KD.ZG':'GDP growth shows how much the economy grew after allowing for inflation. A growing economy does not mean every stock will rise.',
 'FP.CPI.TOTL.ZG':'Inflation shows how quickly consumer prices changed over a year. It does not show how high prices are. Countries may measure it differently.',
 'SL.UEM.TOTL.ZS':'This estimate shows the share of people in the workforce who are available for work and looking for a job. It does not include everyone without a job.',
 'NE.EXP.GNFS.ZS':'Exports as a percentage of GDP describes international exposure of a national economy; it is not the same as a company’s overseas revenue share.',
 'FR.INR.LEND':'This World Bank figure shows a typical bank lending rate, where available. It is not the main rate set by the Bank of England or US Federal Reserve.'
};
const macroLatest=(country,code)=>macroPayload?.series?.[country]?.[code]?.at(-1)||null;
const macroDate=t=>Number.isFinite(t)?new Date(t).toLocaleString('en-GB'):'Unavailable';
function macroOnView(){if(!macroPayload)macroFetch(false)}
function macroStatus(message,error=false){const el=$('macro-status');if(!el)return;el.textContent=message;el.classList.toggle('compare-error',error)}
async function macroFetch(refresh=false){
 if(macroBusy)return;
 macroBusy=true;$('macro-refresh').disabled=true;
 macroStatus('Loading yearly UK and US figures from the World Bank…');
 try{
  const response=await api('/api/macro'+(refresh?'?refresh=1':''));
  if(response.status!=='ok'){macroStatus(response.error||'Yearly figures are unavailable. Missing values have not been guessed.',true);return}
  macroPayload=response;
  const origin=response.cached?'Verified local server cache':'Fresh World Bank response';
  macroStatus(origin+' · fetched '+macroDate(response.fetched_at)+(response.stale?' · REFRESH FAILED; EARLIER DATA ONLY':'')+(response.warning?' · '+response.warning:''));
  macroRender();
 }catch(err){macroStatus('Official macro data unavailable: '+err.message,true)}
 finally{macroBusy=false;$('macro-refresh').disabled=false}
}
function macroRender(){
 if(!macroPayload)return;
 $('macro-cards').innerHTML=MACRO_KEYS.map(([code,label,unit])=>{
  const parts=['GB','US'].map(country=>{
   const row=macroLatest(country,code);
   return '<div class="macro-country"><span>'+escapeHtml(country==='GB'?'UNITED KINGDOM':'UNITED STATES')+'</span>'+
       '<strong>'+(row?escapeHtml(row.value.toFixed(2))+'<small>%</small>':'Unavailable')+'</strong>'+
       '<small>'+(row?'Observation: '+row.year:'No verified observation')+'</small></div>';
  }).join('');
  return '<article class="surface macro-metric"><div class="section-tag">'+escapeHtml(unit)+'</div><h3>'+escapeHtml(label)+'</h3><div class="macro-pair">'+parts+'</div><a class="macro-source-link" href="https://data.worldbank.org/indicator/'+code+'?locations=GB-US" target="_blank" rel="noopener noreferrer">View official source and definition ↗</a></article>';
 }).join('');
 macroChart();
}
function macroChart(){
 const root=$('macro-chart'),code=$('macro-indicator').value;
 $('macro-context').textContent=(MACRO_EXPLAIN[code]||'')+' · Source: World Bank WDI. Annual observation years; latest available values may be several years old or revised.';
 if(!macroPayload){root.textContent='Economic history has not been loaded.';return}
 const all=['GB','US'].flatMap(c=>macroPayload.series[c]?.[code]||[]);
 if(all.length<2){root.innerHTML='<p class="macro-disclosure">Insufficient published data for this indicator. No data is fabricated.</p>';return}
 const years=[...new Set(all.map(r=>r.year))].sort((a,b)=>a-b);
 const lo=Math.min(...all.map(r=>r.value)),hi=Math.max(...all.map(r=>r.value));
 const delta=Math.max(1,hi-lo),min=lo-delta*.12,max=hi+delta*.12;
 const W=900,H=270,L=67,R=21,T=22,B=47;
 const x=y=>L+(y-years[0])*((W-L-R)/Math.max(1,years.at(-1)-years[0]));
 const y=v=>T+(max-v)*(H-T-B)/(max-min);
 let lines='',dots='';
 for(const [country,colour] of [['GB','#86dcd2'],['US','#c1a6ff']]){
  const points=macroPayload.series[country]?.[code]||[];
  let segments=[],current=[],lastYear=null;
  for(const p of points){if(lastYear!==null&&p.year-lastYear>1){if(current.length)segments.push(current);current=[]}current.push(p);lastYear=p.year;}
  if(current.length)segments.push(current);
  for(const segment of segments){
   if(segment.length>1)lines+='<polyline points="'+segment.map(p=>x(p.year).toFixed(1)+','+y(p.value).toFixed(1)).join(' ')+'" fill="none" stroke="'+colour+'" stroke-width="2.8" stroke-linejoin="round" stroke-linecap="round"/>';
  }
  dots+=points.map(p=>'<circle cx="'+x(p.year).toFixed(1)+'" cy="'+y(p.value).toFixed(1)+'" r="4" fill="'+colour+'"><title>'+country+' · '+p.year+' · '+p.value.toFixed(2)+'%</title></circle>').join('');
 }
 const ticks=[0,.25,.5,.75,1].map(t=>{
  const val=min+t*(max-min),yy=y(val).toFixed(1);
  return '<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yy+'" y2="'+yy+'" stroke="#354650" stroke-dasharray="3 5"/><text x="'+(L-11)+'" y="'+(+yy+4)+'" text-anchor="end" fill="#91a3af" font-size="11">'+val.toFixed(1)+'%</text>';
 }).join('');
 const yearsText=years.filter((n,i)=>i===0||i===years.length-1||i%2===0).map(n=>'<text x="'+x(n).toFixed(1)+'" y="'+(H-18)+'" text-anchor="middle" fill="#8c9fab" font-size="11">'+n+'</text>').join('');
 root.innerHTML='<div class="macro-legend"><span><i class="macro-dot uk"></i> United Kingdom</span><span><i class="macro-dot usa"></i> United States</span></div><svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Annual reported UK and US '+escapeHtml(MACRO_KEYS.find(m=>m[0]===code)?.[1]||'macro')+' values, not daily data">'+ticks+lines+dots+yearsText+'</svg>';
}
function accuracyOnView(){researchUpdatePickers();const s=$('accuracy-symbol'),existing=s.value;s.replaceChildren();for(const sym of E.watch){const opt=document.createElement('option');opt.value=sym;opt.textContent=sym+' · '+safeName(sym);s.appendChild(opt)}s.value=E.watch.includes(existing)?existing:E.selected}
function accuracyCell(label,row){
 if(!row)return '<article class="surface accuracy-score"><div class="section-tag">'+label+'</div><h3>Not enough past prices</h3><p>At least five separate past test periods with valid prices are needed.</p></article>';
 const difference=row.baselineMAPE-row.modelMAPE;
 const verdict=difference>0?'The model made smaller errors':'Predicting no change worked as well or better';
 return '<article class="surface accuracy-score"><div class="section-tag">'+label+' · '+row.samples+' separate past tests</div><h3>'+escapeHtml(verdict)+'</h3><div class="accuracy-values"><div><span>MODEL · AVERAGE PRICE ERROR</span><strong>'+row.modelMAPE.toFixed(2)+'%</strong></div><div><span>NO CHANGE · AVERAGE PRICE ERROR</span><strong>'+row.baselineMAPE.toFixed(2)+'%</strong></div></div><div class="accuracy-bars">'+
  [['Model',row.modelMAPE,'model'],['Baseline',row.baselineMAPE,'base']].map(([n,value,cls])=>'<div><small>'+n+'</small><span><i class="'+cls+'" style="width:'+Math.max(2,Math.min(100,value/Math.max(row.modelMAPE,row.baselineMAPE,0.01)*100)).toFixed(1)+'%"></i></span></div>').join('')+'</div><p>Error reduction compared with predicting no change: '+(difference>=0?'+':'')+difference.toFixed(2)+' percentage points. The direction was right in '+(row.directionAccuracy===null?'N/A':row.directionAccuracy.toFixed(1)+'%')+' of non-flat historical moves.</p></article>';
}
async function accuracyRun(){
 if(accuracyBusy)return;const sym=$('accuracy-symbol').value;
 if(!safeSymbol(sym))return;
 accuracyBusy=true;$('accuracy-run').disabled=true;$('accuracy-state').textContent='Checking past daily prices for '+sym+'…';
 try{
  const history=await historicalFor(sym);
  if(history.status!=='ok'||history.points.length<90)throw new Error(history.message||'More daily prices are needed to test past forecasts fairly.');
  const result5=ChartResearch.walkForward(history.points,5),result20=ChartResearch.walkForward(history.points,20);
  if(!result5&&!result20)throw new Error('There is not enough price history for separate past tests. More daily prices are needed.');
  const compare=[result5,result20].filter(Boolean),beats=compare.filter(r=>r.beatBaseline).length;
  $('accuracy-state').textContent=sym+' · '+history.points.length+' verified '+(history.provider==='massive'?'Massive EOD split-adjusted':'Finnhub daily')+' closes · '+(history.cached?'locally cached source':'retrieved from provider')+'.';
  $('accuracy-results').innerHTML='<div class="accuracy-summary surface"><div class="section-tag">TEST COMPARISON · NOT INVESTMENT ADVICE</div><h3>'+beats+' of '+compare.length+' tested time periods beat the baseline</h3><p>Simple unchanged-price forecasts are the reference test. Historical model outperformance is not guaranteed and is not evidence of profitable trading. The model has fixed rules and was not tuned during this test.</p></div><div class="accuracy-grid">'+accuracyCell('5 TRADING SESSIONS',result5)+accuracyCell('20 TRADING SESSIONS',result20)+'</div><p class="macro-disclosure">Method: non-overlapping historical evaluation, using only prior daily observations; no forward-looking news, no fabricated daily closes. MAPE = mean absolute percentage error. Sample sizes depend on available free-tier history. Last observed close: '+escapeHtml(new Date(history.points.at(-1).t).toLocaleDateString('en-GB'))+'.</p>';
 }catch(err){$('accuracy-state').textContent='Cannot evaluate '+sym+': '+err.message;$('accuracy-results').innerHTML='<div class="surface macro-method"><h3>Historical accuracy unavailable</h3><p>Missing provider history is not replaced with generated prices. Check Massive in Settings or choose another stock.</p></div>'}
 finally{accuracyBusy=false;$('accuracy-run').disabled=false}
}
function setupResearchV18(){
 $('macro-refresh').addEventListener('click',()=>macroFetch(true));
 $('macro-indicator').addEventListener('change',macroChart);
 $('accuracy-run').addEventListener('click',accuracyRun);
}
