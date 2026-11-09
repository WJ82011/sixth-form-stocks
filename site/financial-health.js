/* SEC accounts: dated evidence, separate periods, no invented health score. */
const FinancialHealth=(()=>{
 'use strict';
 const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const finite=x=>typeof x==='number'&&Number.isFinite(x),fact=(p,k)=>finite(p?.metrics?.[k]?.value)?p.metrics[k]:null;
 const money=x=>!finite(x)?'Not available':new Intl.NumberFormat('en-GB',{style:'currency',currency:'USD',notation:Math.abs(x)>=1e6?'compact':'standard',maximumFractionDigits:2}).format(x);
 const exact=x=>finite(x)?'USD '+x.toLocaleString('en-GB',{maximumFractionDigits:2}):'Not available';
 const date=x=>x?new Date(x+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'Unknown date';
 const label={revenue:'Sales',profit:'Net profit or loss',operatingCash:'Cash from operations',cash:'Cash & cash equivalents',assets:'Total assets',liabilities:'Total liabilities',debtCurrent:'Current portion of long-term debt',debtNoncurrent:'Non-current long-term debt'};
 let current='',report=null,seq=0,busy=false,compareSeq=0,compareBusy=false;
 function source(f){if(!f?.url)return '';try{const u=new URL(f.url);if(u.protocol!=='https:'||u.hostname!=='www.sec.gov'||u.username||u.password||!u.pathname.startsWith('/Archives/edgar/data/'))return '';return '<a href="'+esc(u.href)+'" target="_blank" rel="noopener noreferrer">'+esc(f.form)+' · filed '+esc(date(f.filed))+' ↗</a>'}catch{return ''}}
 async function get(path){const r=await fetch(path,{cache:'no-store'}),d=await r.json();if(!r.ok)throw Error(d.error||'Saved accounts could not be read.');return d}
 async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}),d=await r.json();if(!r.ok)throw Error(d.error||'The SEC update was unavailable.');return d}
 function selected(){return $('company-select')?.value||E.selected}
 function period(){return $('fh-period').value}
 function card(p,key,title,explanation){const f=fact(p,key);return '<article class="fh-stat"><span>'+esc(title)+'</span><strong title="'+esc(exact(f?.value))+'">'+esc(money(f?.value))+'</strong><p>'+esc(explanation)+'</p><small>'+source(f)+'</small></article>'}
 function chart(periods,key,title){
  const width=620,height=220,top=28,bottom=170,left=18,right=18,values=periods.map(p=>fact(p,key)?.value),valid=values.filter(finite);
  if(!valid.length)return '<article class="fh-chart"><h3>'+esc(title)+'</h3><p>No directly reported figures available for these periods.</p></article>';
  const min=Math.min(0,...valid),max=Math.max(0,...valid),span=max-min||1,y=v=>top+(max-v)/span*(bottom-top),zero=y(0),step=(width-left-right)/periods.length,bar=Math.min(60,step*.55);
  let svg='<svg viewBox="0 0 '+width+' '+height+'" role="img" aria-label="'+esc(title+' in USD; discrete reported periods. Missing values are labelled unavailable.')+'"><line x1="'+left+'" x2="'+(width-right)+'" y1="'+zero+'" y2="'+zero+'" class="fh-zero"/>';
  periods.forEach((p,i)=>{const v=values[i],x=left+step*(i+.5);if(finite(v)){const yy=Math.min(zero,y(v)),h=Math.max(1,Math.abs(y(v)-zero));svg+='<rect x="'+(x-bar/2)+'" y="'+yy+'" width="'+bar+'" height="'+h+'" rx="5" class="'+(v<0?'fh-negative':'fh-positive')+'"><title>'+esc(date(p.start)+' – '+date(p.end)+': '+exact(v))+'</title></rect>'}svg+='<text x="'+x+'" y="'+(finite(v)?Math.max(17,Math.min(192,y(v)+(v<0?17:-8))):100)+'" text-anchor="middle" class="fh-chart-value">'+esc(finite(v)?money(v):'N/A')+'</text><text x="'+x+'" y="211" text-anchor="middle">'+esc(p.type==='quarterly'?p.end.slice(2,7):p.end.slice(0,4))+'</text>'});
  return '<article class="fh-chart"><h3>'+esc(title)+'</h3>'+svg+'</svg><p>USD · '+(period()==='quarterly'?'Directly reported quarters':'Full financial years')+' · bars are separate reporting periods; hover for exact dates and values.</p></article>';
 }
 function render(){
  const out=$('fh-output');$('fh-export').disabled=!report||report.status==='not_loaded';
  if(!report||!['ok','unsupported'].includes(report.status)){out.innerHTML='<div class="fh-empty"><span aria-hidden="true">↗</span><h3>Start with the company’s own accounts.</h3><p>'+esc(report?.notice||'Choose Update SEC accounts to request official reported figures. No paid data subscription is needed.')+'</p><p>This does not use your Finnhub or Massive allowance.</p></div>';return}
  const periods=report[period()]||[],p=periods.at(-1);
  if(!p){out.innerHTML='<div class="fh-empty"><h3>No supported '+esc(period()==='annual'?'annual':'directly reported quarterly')+' figures.</h3><p>'+esc(report.coverage||report.notice)+'</p><p>US-GAAP in USD is supported first. Custom tags, IFRS and missing periods are not guessed.</p></div>';return}
  const growth=p.revenueGrowthPct,margin=p.netMarginPct;
  let story=period()==='annual'&&finite(growth)?'Sales '+(growth>=0?'rose ':'fell ')+Math.abs(growth).toFixed(1)+'% against the preceding comparable saved year.':'A dated view of the figures this company reported.';
  if(finite(margin))story+=' '+(margin<0?'It reported a net loss equal to '+Math.abs(margin).toFixed(1)+'% of sales.':'It kept '+margin.toFixed(1)+'% of sales as net profit.');
  const debtSource=fact(p,'debtNoncurrent');
  out.innerHTML='<div class="fh-story"><div><p class="desk-eyebrow">'+esc(report.symbol)+' / '+esc(report.name)+'</p><h3>'+esc(story)+'</h3><p>'+esc(date(p.start))+' – '+esc(date(p.end))+' · '+esc(p.durationDays)+' days · USD</p></div><span class="fh-date-badge">'+esc(period()==='annual'?'Annual accounts':'Directly reported quarter')+'</span></div>'+
   '<div class="fh-stats">'+card(p,'revenue','Sales','Money earned from selling products and services.')+card(p,'profit','Net profit or loss','What remained after the reported costs and taxes.')+card(p,'cash','Cash available','Cash and cash equivalents at the period end; excludes restricted cash.')+'<article class="fh-stat"><span>Reported long-term debt</span><strong title="'+esc(exact(p.longTermDebt))+'">'+esc(money(p.longTermDebt))+'</strong><p>Current and non-current portions. Other short-term borrowings and leases are excluded.</p><small>'+ (finite(p.longTermDebt)?source(debtSource):'Both portions must be reported in the same filing.')+'</small></article></div>'+
   '<div class="fh-charts">'+chart(periods,'revenue','How sales changed')+chart(periods,'profit','Profit and loss over time')+chart(periods,'operatingCash','Cash generated by operations')+'</div>'+
   '<details class="fh-evidence"><summary>Check every figure and its source</summary><div class="fh-table-wrap"><table><caption>Selected figures for '+esc(date(p.start))+' – '+esc(date(p.end))+'</caption><thead><tr><th>Reported item</th><th>Exact USD amount</th><th>Filing &amp; definition</th></tr></thead><tbody>'+Object.keys(label).map(key=>{const f=fact(p,key);return '<tr><th scope="row">'+esc(label[key])+'</th><td>'+esc(exact(f?.value))+'</td><td>'+(f?source(f)+'<small>us-gaap:'+esc(f.tag)+' · '+(f.start?esc(date(f.start))+' – ':'As at ')+esc(date(f.end))+'</small>':esc(p.metrics?.[key]?.missing||'No supported fact for this exact period.'))+'</td></tr>'}).join('')+'</tbody></table></div></details>'+
   (report.excludedPeriods?.length?'<div class="fh-warnings">'+report.excludedPeriods.map(w=>'<p>'+esc(w)+'</p>').join('')+'</div>':'')+
   (p.warnings?.length?'<div class="fh-warnings">'+p.warnings.map(w=>'<p>'+esc(w)+'</p>').join('')+'</div>':'')+
   '<p class="fh-notice">'+esc(report.ageNotice||'')+' '+(report.stale?'This saved response is more than seven days old. ':'')+esc(report.notice)+'</p>';
 }
 async function load(sym=selected()){
  current=sym;const id=++seq;report=null;$('fh-output').textContent='Reading the accounts saved on this Mac…';$('fh-export').disabled=true;$('fh-status').textContent=sym+' · reading saved accounts only.';
  try{const d=await get('/api/financials?symbol='+encodeURIComponent(sym));if(id!==seq||sym!==current)return;report=d;render();$('fh-status').textContent=d.fetchedAt?'Saved accounts retrieved '+new Date(d.fetchedAt).toLocaleString('en-GB')+'. Check reporting dates below.':d.notice}catch(e){if(id===seq){$('fh-status').textContent=e.message;$('fh-output').textContent='No figures are shown for this company.'}}
 }
 async function update(){
  if(busy)return;const sym=current||selected(),id=++seq;busy=true;$('fh-update').disabled=true;$('fh-status').textContent='Requesting '+sym+' accounts from the SEC. This can take a few seconds…';
  try{const d=await post('/api/financials/refresh',{symbol:sym});if(id!==seq||sym!==current)return;report=d;render();window.dispatchEvent(new Event('marketdesk:accounts-updated'));$('fh-status').textContent=d.refreshNotice||'Accounts saved.'}catch(e){if(id===seq)$('fh-status').textContent=e.message+' Earlier saved figures, if any, remain on screen.'}finally{busy=false;$('fh-update').disabled=false}
 }
 function choices(){return ['compare-a','compare-b','compare-c'].map(id=>$(id).value).filter(Boolean)}
 function renderComparison(data){
  const rows=data.rows||[],out=$('fh-compare-output');
  out.innerHTML='<p class="fh-match '+(data.aligned?'fh-matched':'')+'">'+esc(data.basis)+'</p><div class="fh-compare-cards">'+rows.map(r=>{const p=r.period;return '<article class="fh-compare-card"><p class="desk-eyebrow">'+esc(r.symbol)+'</p><h3>'+esc(r.name||r.symbol)+'</h3>'+(p?'<p>'+esc(date(p.start))+' – '+esc(date(p.end))+' · '+p.durationDays+' days</p><dl>'+['revenue','profit','cash','operatingCash'].map(k=>'<div><dt>'+esc(label[k])+'</dt><dd>'+esc(money(fact(p,k)?.value))+'</dd></div>').join('')+'<div><dt>Net profit margin</dt><dd>'+esc(finite(p.netMarginPct)?p.netMarginPct.toFixed(1)+'%':'Not available')+'</dd></div></dl><details><summary>Sources &amp; exact amounts</summary>'+['revenue','profit','cash','operatingCash'].map(k=>{const f=fact(p,k);return '<p>'+esc(label[k])+': '+esc(exact(f?.value))+'<br>'+source(f)+(f?'<small>us-gaap:'+esc(f.tag)+'</small>':'')+'</p>'}).join('')+'</details>':'<p>No supported annual SEC accounts saved. Use Update selected SEC accounts.</p>')+'</article>'}).join('')+'</div><p class="fh-notice">'+esc(data.notice)+'</p>';
 }
 async function compare(updateFirst=false){
  if(compareBusy)return;const symbols=choices(),id=++compareSeq,key=symbols.join(',');
  if(symbols.length<2||new Set(symbols).size!==symbols.length){$('fh-compare-status').textContent='Choose two or three different companies.';return}
  compareBusy=true;$('fh-compare').disabled=true;$('fh-compare-update').disabled=true;$('fh-compare-output').textContent='';const warnings=[];
  try{
   if(updateFirst)for(const sym of symbols){$('fh-compare-status').textContent='Updating SEC accounts: '+sym+'…';try{await post('/api/financials/refresh',{symbol:sym})}catch(e){warnings.push(sym+': '+e.message)}if(id!==compareSeq||key!==choices().join(','))return}
   const d=await get('/api/financials/compare?symbols='+encodeURIComponent(key));if(id!==compareSeq||key!==choices().join(','))return;renderComparison(d);$('fh-compare-status').textContent=warnings.length?warnings.join(' '):'Compared saved accounts. Check each period and source.';
  }catch(e){if(id===compareSeq)$('fh-compare-status').textContent=e.message}finally{compareBusy=false;$('fh-compare').disabled=false;$('fh-compare-update').disabled=false}
 }
 function open(){load(selected());if(document.querySelector?.('#view-company .fh-legacy')?.open&&typeof loadCompany==='function')loadCompany()}
 function setup(){
  if(!$('financial-health'))return;document.querySelector?.('#view-company .fh-legacy')?.addEventListener('toggle',event=>{if(event.currentTarget.open&&typeof loadCompany==='function')loadCompany()});$('fh-update').addEventListener('click',update);$('fh-period').addEventListener('change',render);$('company-select').addEventListener('change',()=>load(selected()));
  $('fh-compare').addEventListener('click',()=>compare(false));$('fh-compare-update').addEventListener('click',()=>compare(true));
  for(const id of ['compare-a','compare-b','compare-c'])$(id).addEventListener('change',()=>{compareSeq++;$('fh-compare-output').textContent='';$('fh-compare-status').textContent='Company choices changed. Compare again to see matching accounts.'});
  $('fh-export').addEventListener('click',()=>{if(!report||report.symbol!==current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='MarketDesk-'+current+'-SEC-accounts.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 }
 if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',setup,{once:true});
 return {open,load,update,compare,renderComparison,render,source,money,fact};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=FinancialHealth;
