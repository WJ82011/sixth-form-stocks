/* Market Desk 1.7 — transparent, evidence-led equity comparison. */
'use strict';
let compareResults=[], compareBusy=false;
const COMPARISON_FIELDS=[
 {group:'Valuation',label:'Total market value',key:'marketCap',unit:'USD bn',hint:'From the company profile. Market value is reported in millions of the company’s currency. Only US-dollar figures are converted to billions here.'},
 {group:'Valuation',label:'Price/earnings ratio (past year)',keys:['peBasicExclExtraTTM','peTTM'],unit:'×',hint:'Share price divided by earnings per share over the past year. It may be missing or not useful.'},
 {group:'Profitability',label:'Net profit margin (past year)',keys:['netProfitMarginTTM'],unit:'%',hint:'Share of sales left as profit over the past year. The dates may differ between companies.'},
 {group:'Profitability',label:'Operating profit margin (past year)',keys:['operatingMarginTTM'],unit:'%',hint:'Operating profit as a share of sales. Compare similar industries.'},
 {group:'Growth',label:'Yearly sales growth',keys:['revenueGrowthTTMYoy'],unit:'%',hint:'How sales changed over the past 12 months compared with the year before.'},
 {group:'Returns',label:'Return on shareholders’ equity (past year)',keys:['roeTTM'],unit:'%',hint:'Profit compared with shareholders’ equity in the accounts. Unusual equity values can make the figure misleading.'},
 {group:'Balance sheet',label:'Current ratio (annual)',keys:['currentRatioAnnual'],unit:'×',hint:'Short-term assets divided by short-term debts. A measure of the ability to cover upcoming bills.'},
 {group:'Balance sheet',label:'Debt / equity (annual)',keys:['totalDebtToEquityAnnual'],unit:'%',hint:'Debt compared with shareholders’ equity, usually shown as a percentage. Check how the provider defines it.'},
 {group:'Trading context',label:'52-week high',keys:['52WeekHigh'],unit:'price',hint:'Highest price over the past year. It does not tell you what the stock should be worth.'},
 {group:'Trading context',label:'52-week low',keys:['52WeekLow'],unit:'price',hint:'Lowest price over the past year. It does not tell you what the stock should be worth.'},
 {group:'Income',label:'Estimated yearly dividend yield',keys:['dividendYieldIndicatedAnnual'],unit:'%',hint:'An estimated dividend yield. Future payments are not guaranteed.'}
];
function compareFinite(v){if(v===null||v===undefined||v===''||typeof v==='boolean')return null;const n=Number(v);return Number.isFinite(n)&&Math.abs(n)<1e15?n:null}
function compareGet(row,field){
 if(field.key==='marketCap'){
  if(String(row.profile?.currency||'').toUpperCase()!=='USD')return null;
  const v=compareFinite(row.profile?.marketCapitalization);return v!==null&&v>0?v/1000:null;
 }
 const metric=row.metrics?.metric||{};
 for(const key of field.keys||[]){const v=compareFinite(metric[key]);if(v!==null)return v}
 return null;
}
function compareFormat(row,field){const x=compareGet(row,field);if(x===null)return '<span class="compare-na" title="Not supplied by provider">Unavailable</span>';
 const precision=field.unit==='USD bn'?2:field.unit==='price'?2:2;
 const val=x.toLocaleString('en-GB',{minimumFractionDigits:field.unit==='USD bn'?2:0,maximumFractionDigits:precision});
 const suffix=field.unit==='price'?(row.profile?.currency?' '+escapeHtml(row.profile.currency):' · currency unreported'):(field.unit==='USD bn'?' USD bn':field.unit==='×'?'×':field.unit==='% '||field.unit==='%'?'%':'');
 return '<strong class="compare-val">'+escapeHtml(val)+suffix+'</strong>';
}
function researchUpdatePickers(){
 const sources=typeof companyChoices==='function'?companyChoices():[...E.watch];
 for(const id of ['compare-a','compare-b','compare-c','report-symbol']){
  const el=$(id);if(!el)return;
  const existing=el.value;
  el.replaceChildren();if(id==='compare-c'){const o=document.createElement('option');o.value='';o.textContent='None / compare two';el.appendChild(o)}
  for(const sym of sources){const o=document.createElement('option');o.value=sym;o.textContent=sym+' · '+safeName(sym);el.appendChild(o)}
  const def=id==='compare-a'?'AAPL':id==='compare-b'?'MSFT':id==='compare-c'?'NVDA':E.selected;
  const value=[...el.options].some(o=>o.value===existing)?existing:[...el.options].some(o=>o.value===def)?def:(el.options[0]?.value||'');el.value=value;
 }
}
function compareOnView(){researchUpdatePickers()}
function compareSetState(message,isError=false){const el=$('compare-state');if(!el)return;el.textContent=message;el.classList.toggle('compare-error',isError)}
async function runComparison(){
 if(compareBusy)return;
 const symbols=[$('compare-a').value,$('compare-b').value,$('compare-c').value].filter(Boolean);
 if(symbols.length<2||new Set(symbols).size!==symbols.length){compareSetState('Choose at least two different companies.',true);return}
 if(!E.configured){compareSetState('Save your Finnhub API key in Settings first. Company figures come from Finnhub.',true);return}
 compareBusy=true;$('compare-run').disabled=true;compareResults=[];
 const failures=[];
 try{
  for(let i=0;i<symbols.length;i++){
   const sym=symbols[i];compareSetState('Retrieving '+sym+' ('+(i+1)+' / '+symbols.length+'). Cached results are reused where possible.');
   try{
    let data=E.fundamentals.get(sym),cached=Boolean(data),stale=false;
    const fetched=Number(data?.retrievedAt)||0;
    const received=Number(data?.clientReceivedAt)||fetched;
    // Finnhub fundamentals change slowly, but do not stamp old values as freshly retrieved.
    // Clear data older than thirty minutes; if refresh fails, disclose and use earlier data.
    if(!data||!fetched||Date.now()-received>30*60*1000){
      try{
       const fresh=await api('/api/company?symbol='+encodeURIComponent(sym));
       if(fresh?.symbol!==sym)throw new Error('Provider symbol mismatch');
       fresh.retrievedAt=Number(fresh.retrieved_at)||Date.now();fresh.clientReceivedAt=Date.now();data=fresh;cached=false;E.fundamentals.set(sym,data);
      }catch(err){if(!data)throw err;stale=true;failures.push(sym+': refresh unavailable ('+err.message+'); displaying an earlier cached response.');}
    }
    compareResults.push({symbol:sym,...data,loadedAt:Number(data.retrievedAt)||null,cacheStatus:stale?'STALE CACHED':cached?'BROWSER CACHE':data.metrics_cached||data.profile_cached?'SERVER CACHE':'FRESH PROVIDER RESPONSE'});
    if(data.profile?.name)E.names[sym]=data.profile.name;
    if(data.metrics_error)failures.push(sym+': some financial metrics unavailable ('+data.metrics_error+')');
   }catch(err){compareResults.push({symbol:sym,profile:{},metrics:{metric:{}},error:err.message,loadedAt:null,cacheStatus:'UNAVAILABLE'});failures.push(sym+': '+err.message)}
  }
  renderComparison();compareSetState('Compared '+symbols.length+' instruments · display updated '+new Date().toLocaleString('en-GB')+'. '+(failures.length?'Some data restricted; see warnings below.':'Missing figures have not been filled in.'),Boolean(failures.length));
 }finally{compareBusy=false;$('compare-run').disabled=false}
}
function renderComparison(){
 const pane=$('compare-output');if(!pane||!compareResults.length)return;
 const rows=COMPARISON_FIELDS.map(f=>{
   const cells=compareResults.map(d=>'<td>'+compareFormat(d,f)+'</td>').join('');
   return '<tr><th scope="row"><span>'+escapeHtml(f.label)+'</span><small>'+escapeHtml(f.hint)+'</small></th>'+cells+'</tr>';
 }).join('');
 const headers=compareResults.map(d=>{
   const p=d.profile||{};return '<th scope="col"><div class="compare-company-symbol">'+escapeHtml(d.symbol)+'</div><div class="compare-company-name">'+escapeHtml(p.name||safeName(d.symbol))+'</div><div class="compare-company-industry">'+escapeHtml(p.finnhubIndustry||'Sector unavailable')+'</div><div class="compare-company-currency">'+escapeHtml(p.currency||'Currency unavailable')+'</div></th>';
 }).join('');
 const errors=compareResults.filter(d=>d.error||d.metrics_error).map(d=>'<p><strong>'+escapeHtml(d.symbol)+'</strong>: '+escapeHtml(d.error||d.metrics_error)+'</p>').join('');
 const timestamps=compareResults.map(d=>'<span><strong>'+escapeHtml(d.symbol)+'</strong>: '+(d.loadedAt?escapeHtml(new Date(d.loadedAt).toLocaleString('en-GB')):'No verified retrieval')+' · '+escapeHtml(d.cacheStatus||'UNKNOWN')+'</span>').join(' · ');
 const note=errors?'<div class="compare-warning"><strong>Provider access / coverage</strong>'+errors+'</div>':'';
 pane.innerHTML='<div class="surface compare-board"><div class="panel-head"><div><div class="section-tag">02 / FINANCIAL FUNDAMENTALS</div><h3>Peer comparison matrix</h3></div><span class="source-tag">FINNHUB · VERIFIED SOURCE PATHS</span></div><div class="compare-table-scroll"><table class="compare-table"><thead><tr><th scope="col">FINANCIAL INDICATOR</th>'+headers+'</tr></thead><tbody>'+rows+'</tbody></table></div><div class="compare-foot"><strong>Provider:</strong> Finnhub /stock/profile2 + /stock/metric?metric=all. <strong>Per-company source retrieval:</strong> '+timestamps+'. <strong>Display generated:</strong> '+escapeHtml(new Date().toLocaleString('en-GB'))+'. <strong>Timing:</strong> quote, profile and fundamental data can have different observation/reporting dates; the API does not supply a matching fiscal date for every metric. No cross-company performance rankings or automatic valuations.</div>'+note+'</div>';
}
function comparisonToReport(){
 if(typeof reportsOnView!=='function'){toast('Reports workspace could not start.');return}
 changeView('reports');
 if(compareResults.length){
  const first=compareResults[0];$('report-symbol').value=first.symbol;
  if(!$('report-title').value)$('report-title').value=first.symbol+' — peer comparison and investment case';
  const date=new Date().toLocaleDateString('en-GB');
  const lines=['Company figures from Finnhub (copied into report '+date+'). Source retrieval times are displayed in Compare Companies; confirm reporting periods before treating these as contemporary financial statement figures.'];
  for(const d of compareResults){
   const names=d.profile?.name||d.symbol;
   const pe=compareGet(d,COMPARISON_FIELDS[1]),margin=compareGet(d,COMPARISON_FIELDS[2]);
   lines.push(d.symbol+' ('+names+'): P/E '+(pe===null?'unavailable':pe.toFixed(2)+'×')+'; net margin '+(margin===null?'unavailable':margin.toFixed(2)+'%')+'.');
  }
  if(!$('report-financial').value)$('report-financial').value=lines.join('\n');
  if(!$('report-sources').value)$('report-sources').value='Finnhub /stock/profile2 and /stock/metric?metric=all; retrieved '+date+'. Compare against companies’ published financial statements.';
  $('report-feedback').textContent='Comparison observations copied into your draft; validate reporting dates and write your own conclusion before saving.';
 }
}
