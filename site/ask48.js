/* Chart questions from saved records. A late reply cannot replace a newer question. */
const Ask48=(()=>{
'use strict';
let seq=0,latest=null,lastQuestion='',opener=null;
let answered=null;
let current={symbol:'',range:'',start:'',end:'',kind:'',scanId:'',stressId:'',scenarioId:'',investigationId:'',product:'',packId:'',compareSymbols:'',journalId:''};
let screen={...current};
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DATED=new Set(['chart','heatmap','comparison','events','journal','']);
const AREAS={home:'chart',crypto:'crypto',heatmap:'heatmap',comparison:'comparison',company:'financials',forecast:'forecast',alerts:'alerts',portfolio:'portfolio',learning:'strategy',reports:'report',research:'journal',screener:'scan',valuation:'scenario'};
function ny(ms){const t=Number(ms);return Number.isFinite(t)?new Date(t).toLocaleDateString('en-CA',{timeZone:'America/New_York'}):'';}
function motionOff(){return document.body?.dataset?.motion==='off'||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;}
function key(ctx){return ['symbol','range','start','end','kind','scanId','stressId','scenarioId','investigationId','product','journalId','compareSymbols'].map(name=>ctx[name]||'').join('|');}
function blank(){return {symbol:'',range:'',start:'',end:'',kind:'',scanId:'',stressId:'',scenarioId:'',investigationId:'',product:'',packId:'',compareSymbols:'',journalId:''};}
function chartDates(){
 const symbol=typeof E!=='undefined'&&E.selected?E.selected:'';
 const range=typeof E!=='undefined'&&E.range?E.range:'';
 let start='',end='';
 const box=window.Chart43&&Chart43.window?Chart43.window():null;
 if(box&&Number.isFinite(box.from)&&Number.isFinite(box.to)){start=ny(box.from);end=ny(box.to);}
 if(!start){
  const points=typeof Replay43!=='undefined'&&Replay43.active&&typeof Replay43.prices==='function'?Replay43.prices():(typeof E!=='undefined'&&E.chartPoints)||[];
  if(points.length){start=ny(points[0].t);end=ny(points[points.length-1].t);}
 }
 return {symbol,range,start,end};
}
function journalRows(){try{return JSON.parse(localStorage.getItem('md-reborn-journal')||'[]');}catch(error){return [];}}
function screenFor(area){
 const next=blank();
 const chart=chartDates();
 next.kind=area||'';
 next.symbol=chart.symbol;
 if(DATED.has(next.kind)){next.range=chart.range;next.start=chart.start;next.end=chart.end;}
 if(next.kind==='heatmap'&&E&&E.heatmapWindow){next.start=E.heatmapWindow.start||next.start;next.end=E.heatmapWindow.end||next.end;}
 if(next.kind==='comparison')next.compareSymbols=sessionStorage.getItem('md-compare52')||'';
 if(next.kind==='scan')next.scanId=sessionStorage.getItem('md-scanner55')||'';
 if(next.kind==='portfolio')next.stressId=sessionStorage.getItem('md-stress58')||'';
 if(next.kind==='scenario')next.scenarioId=sessionStorage.getItem('md-scenario53')||'';
 if(next.kind==='report'){next.investigationId=sessionStorage.getItem('md-desk61')||'';next.packId=sessionStorage.getItem('md-pack59')||'';}
 if(next.kind==='crypto'){
  const pressed=document.querySelector('[data-crypto57][aria-pressed="true"], [data-crypto-pair][aria-pressed="true"]');
  next.product=(pressed&&(pressed.dataset.crypto57||pressed.dataset.cryptoPair))||'BTC-USD';
  next.symbol=next.product;next.range='crypto';next.start='';next.end='';
 }
 if(next.kind==='journal'){
  const id=sessionStorage.getItem('md-journal49')||'';
  const item=journalRows().find(row=>row.id===id)||journalRows().find(row=>row.symbol===next.symbol)||{};
  next.journalId=item.id||'';next.symbol=item.symbol||next.symbol;next.start=item.start||'';next.end=item.end||'';next.range='';
 }
 return next;
}
function describe(ctx){
 const bits=[];
 if(ctx.symbol)bits.push(ctx.symbol);
 if(ctx.kind)bits.push(ctx.kind);
 if(ctx.range&&ctx.kind!=='crypto')bits.push(ctx.range);
 if(ctx.start&&ctx.end)bits.push(ctx.start+' to '+ctx.end);
 if(ctx.kind==='comparison'&&ctx.compareSymbols)bits.push(ctx.compareSymbols);
 if(ctx.scanId)bits.push('saved scan');
 if(ctx.stressId)bits.push('saved portfolio test');
 if(ctx.scenarioId)bits.push('saved scenario');
 if(ctx.investigationId)bits.push('saved investigation');
 if(ctx.journalId)bits.push('saved research');
 return bits.join(' · ')||'no record attached';
}
const SUGGEST={
 chart:['What happened during this move?','How reliable is this forecast?','What announcements were published during this move?'],
 heatmap:['How much did the stock move in the dates shown?'],
 comparison:['Which company performed best over these dates?','How did it compare with SPY?'],
 events:['What announcements were published during this move?'],
 financials:['What changed in these results?','How does this compare with last year?'],
 forecast:['Has this forecast model beaten its baseline?'],
 alerts:['What announcements were published during this move?'],
 scan:['Why did this company match my scan?'],
 portfolio:['Which holding contributed most to this portfolio change?'],
 scenario:['How did these results differ from my saved scenario?'],
 strategy:['Has this forecast model beaten its baseline?'],
 journal:['Which evidence supports or challenges my saved idea?','What changed since my last review?','Which of my assumptions should I revisit?'],
 report:['What changed since I saved this investigation?'],
 crypto:['How has this crypto model performed?']
};
function chip(label,field){
 const button=document.createElement('button');button.type='button';button.textContent=label+' ×';button.setAttribute('aria-label','Remove '+label);
 button.onclick=()=>{current[field]='';if(field==='start')current.end='';show();noteDifference();};
 return button;
}
function show(){
 const box=$('intel64-chips');if(!box)return;
 box.replaceChildren();
 if(current.symbol)box.append(chip(current.symbol,'symbol'));
 if(current.start&&current.end)box.append(chip(current.start+' to '+current.end,'start'));
 if(current.range)box.append(chip(current.range,'range'));
 if(current.kind)box.append(chip(current.kind,'kind'));
 if(current.scanId)box.append(chip('saved scan','scanId'));
 if(current.stressId)box.append(chip('saved portfolio test','stressId'));
 if(current.scenarioId)box.append(chip('saved scenario','scenarioId'));
 if(current.investigationId)box.append(chip('saved investigation','investigationId'));
 if(current.journalId)box.append(chip('saved research','journalId'));
 const ideas=$('intel64-suggestions');
 if(ideas){ideas.replaceChildren();(SUGGEST[current.kind]||SUGGEST.chart).forEach(text=>{const button=document.createElement('button');button.type='button';button.textContent=text;button.onclick=()=>{$('intel64-question').value=text;ask(text);};ideas.append(button);});}
}
function noteDifference(){
 const node=$('intel64-screen');if(!node)return;
 node.textContent=key(screen)===key(current)?'':'This page is now '+describe(screen)+'. This conversation is still '+describe(current)+'. The next question keeps this conversation until you choose Use this page.';
}
function openPanel(){
 const panel=$('intel64');if(!panel)return;
 panel.hidden=false;document.body.classList.add('intel64-open');
 if($('intel64-return'))$('intel64-return').hidden=true;
 if(motionOff())panel.classList.add('intel64-in');
 else requestAnimationFrame(()=>panel.classList.add('intel64-in'));
 if(typeof drawChart==='function')setTimeout(drawChart,motionOff()?0:180);
 $('intel64-question')?.focus();
 loadSaved();
}
function closePanel(){
 const panel=$('intel64');
 if(panel){panel.classList.remove('intel64-in');panel.hidden=true;}
 document.body.classList.remove('intel64-open');
 if(typeof drawChart==='function')setTimeout(drawChart,40);
 if(opener&&document.contains(opener)&&typeof opener.focus==='function')opener.focus();
}
function clearAnswer(){
 if($('intel64-answer'))$('intel64-answer').textContent='';
 if($('intel64-kind'))$('intel64-kind').textContent='';
 if($('intel64-figures'))$('intel64-figures').replaceChildren();
 if($('intel64-evidence')){$('intel64-evidence').hidden=true;$('intel64-evidence').innerHTML='';}
}
function labelFor(kind){return kind==='user assumption'?'Assumption':kind==='model output'?'Forecast':'Fact';}
function usePage(){current={...screen};show();noteDifference();$('intel64-status').textContent='The next question will use '+describe(current)+'. The answer below stays until you ask.';}
function openFrom(ctx){
 opener=document.activeElement;
 const area=ctx.area||ctx.kind||AREAS[typeof E!=='undefined'?E.view:'']||'chart';
 const live=screenFor(area);
 ['symbol','range','start','end','scanId','stressId','scenarioId','investigationId','product','packId','compareSymbols','journalId'].forEach(name=>{if(ctx[name])live[name]=ctx[name];});
 if(live.symbol==='PORTFOLIO')live.symbol=(typeof E!=='undefined'&&E.selected)||'';
 if(ctx.area||ctx.kind)live.kind=ctx.area||ctx.kind;
 const previousAnswer=answered&&$('intel64-answer')?.textContent?{...answered}:null;
 screen=live;current={...live};
 openPanel();show();noteDifference();
 if(previousAnswer&&key(previousAnswer)!==key(current))$('intel64-status').textContent='The next question uses '+describe(current)+'. The answer below is still about '+describe(previousAnswer)+'.';
 if(ctx.question){$('intel64-question').value=ctx.question;ask(ctx.question);}
}
function sync(){if(typeof E!=='undefined'&&AREAS[E.view])screen=screenFor(AREAS[E.view]);noteDifference();}
async function revealChart(symbol,start,end){
 if(!symbol){$('intel64-status').textContent='No company is attached, so the chart was not opened.';return;}
 if(typeof setSelected==='function')setSelected(symbol);
 if(typeof changeView==='function')changeView('home');
 if(typeof setChartRange==='function'&&current.range&&current.range!=='crypto'&&E.range!==current.range)setChartRange(current.range);
 let points=null;
 for(let attempt=0;attempt<20;attempt++){
  points=(E.chartPoints||[]).filter(point=>ny(point.t)>=start&&ny(point.t)<=end);
  if(E.selected===symbol&&points.length>=2)break;
  await new Promise(resolve=>setTimeout(resolve,100));
  points=null;
 }
 if(start&&end&&points&&points.length>=2&&window.Chart43){Chart43.setWindow(points[0].t,points[points.length-1].t);$('intel64-status').textContent='The chart is showing '+symbol+' from '+start+' to '+end+'.';}
 else $('intel64-status').textContent=start&&end?(symbol+' is open. Those dates are not in the prices loaded on this chart.'):(symbol+' is open. This answer has no cited period to highlight.');
 const narrow=window.matchMedia('(max-width:800px)').matches;
 if(narrow){closePanel();if($('intel64-return'))$('intel64-return').hidden=false;}
}
function openEvent(title,symbol){
 if(typeof setSelected==='function'&&symbol)setSelected(symbol);
 if(typeof changeView==='function')changeView('company');
 const host=$('events42')||$('view-company');
 const match=[...(host?host.querySelectorAll('button,article,li,p'):[])].find(node=>(node.textContent||'').includes(title));
 if(match){match.scrollIntoView({block:'center'});match.classList.add('intel64-hit');$('intel64-status').textContent='The company page is showing that announcement.';}
 else $('intel64-status').textContent='That announcement is not in the company list on this screen.';
 if(window.matchMedia('(max-width:800px)').matches){closePanel();if($('intel64-return'))$('intel64-return').hidden=false;}
}
function openResearch(symbol){
 if(typeof changeView==='function')changeView('research');
 const id=current.journalId||sessionStorage.getItem('md-journal49')||'';
 const button=[...document.querySelectorAll('[data-journal-open]')].find(node=>node.dataset.journalOpen===id||(node.textContent||'').includes(symbol));
 if(button){button.click();$('intel64-status').textContent='The research entry for '+symbol+' is open.';}
 else $('intel64-status').textContent=symbol?('No research entry for '+symbol+' is in the list on this screen.'):'No research entry is attached.';
 if(window.matchMedia('(max-width:800px)').matches){closePanel();if($('intel64-return'))$('intel64-return').hidden=false;}
}
function render(data){
 latest=data;answered={...current};
 const scroller=$('intel64-scroll');
 const kept=scroller?scroller.scrollTop:0;
 const ev=data.evidence||{};
 $('intel64-kind').textContent=labelFor(ev.kind||data.kind);
 $('intel64-answer').textContent=data.answer||'';
 const figures=$('intel64-figures');figures.replaceChildren();
 const rows=ev.figures||[];
 if(rows.length){
  const table=document.createElement('table');
  rows.forEach(row=>{const line=document.createElement('tr');const name=document.createElement('td');name.textContent=row.label||'';const value=document.createElement('td');value.textContent=(row.value??'—')+' '+(row.unit||'');line.append(name,value);table.append(line);});
  figures.append(table);
 }
 const startPrice=Number(ev.startPrice),endPrice=Number(ev.endPrice);
 if(Number.isFinite(startPrice)&&Number.isFinite(endPrice)&&startPrice>0&&endPrice>0){
  const spark=document.createElement('div');spark.id='intel64-spark';spark.setAttribute('aria-hidden','true');
  const max=Math.max(startPrice,endPrice);
  [startPrice,endPrice].forEach(price=>{const bar=document.createElement('span');bar.style.height=Math.max(8,Math.round(price/max*44))+'px';bar.title=String(price);spark.append(bar);});
  const caption=document.createElement('p');caption.textContent='Start '+startPrice+' · End '+endPrice;
  figures.append(spark,caption);
 }
 const detail=$('intel64-evidence');
 detail.hidden=false;
 const gaps=(ev.gaps||[]).map(gap=>'<p>'+esc(gap)+'</p>').join('');
 detail.innerHTML='<summary>Calculation and sources</summary><p>'+esc(ev.coverage||ev.qualification||'')+'</p><p>'+esc(ev.source||'')+'</p>'+gaps;
 const citedStart=ev.start||current.start||'';
 const citedEnd=ev.end||current.end||'';
 const symbol=current.symbol||'';
 const actions=document.createElement('div');actions.id='intel64-links';
 const chartButton=document.createElement('button');chartButton.type='button';chartButton.textContent='Open the cited chart';
 chartButton.onclick=()=>revealChart(symbol,citedStart,citedEnd);
 actions.append(chartButton);
 (ev.items||[]).slice(0,6).forEach(item=>{
  const button=document.createElement('button');button.type='button';
  button.textContent=(item.kindLabel?item.kindLabel+' · ':'')+(item.timeLabel?item.timeLabel+' · ':'')+(item.title||'Saved announcement');
  button.onclick=()=>openEvent(item.title||'',symbol);
  actions.append(button);
 });
 if(current.journalId||current.kind==='journal'||data.kind==='idea'){
  const research=document.createElement('button');research.type='button';research.textContent='Open the research entry';
  research.onclick=()=>openResearch(symbol);
  actions.append(research);
 }
 detail.append(actions);
 if(scroller)scroller.scrollTop=kept;
 $('intel64-status').textContent=data.supported?'Answered from saved records on this Mac.':'This question is outside the calculations saved on this Mac.';
 if($('intel64-progress'))$('intel64-progress').hidden=true;
}
async function ask(question){
 const text=String(question||'').trim();
 if(!text){$('intel64-status').textContent='Enter a question first.';return;}
 const id=++seq,sent={...current};
 lastQuestion=text;
 if($('intel64-progress'))$('intel64-progress').hidden=false;
 $('intel64-status').textContent=(navigator.onLine===false?'This Mac is offline. ':'')+'Asking about '+describe(sent)+'.';
 try{
  const idea=journalRows().find(item=>item.id===sent.journalId)||journalRows().find(item=>item.symbol===sent.symbol)||{};
  const params=new URLSearchParams({symbol:sent.symbol,range:sent.range,start:sent.start,end:sent.end,kind:sent.kind,question:text,capturedAt:idea.createdAt||'',originalPrice:(idea.evidence&&(idea.evidence.endPrice||idea.evidence.startPrice))||'',expectation:idea.expectation||'',journalStatus:idea.status||'',compareSymbols:sent.compareSymbols||sessionStorage.getItem('md-compare52')||'',scenarioId:sent.scenarioId||'',scanId:sent.scanId||'',product:sent.product||'',stressId:sent.stressId||'',packId:sent.packId||sessionStorage.getItem('md-pack59')||'',investigationId:sent.investigationId||'',practiceId:(window.Practice67&&Practice67.id)||''});
  const response=await fetch('/api/v3/ask48?'+params.toString(),{cache:'no-store'});
  const data=await response.json();
  if(id!==seq)return;
  if(!response.ok||data.error){if($('intel64-progress'))$('intel64-progress').hidden=true;$('intel64-status').textContent=(data.error||'The question could not be answered.')+' The answer on screen was kept.';return;}
  const incoming=data.context||{};
  Object.keys(incoming).forEach(name=>{if(incoming[name])current[name]=incoming[name];});
  show();noteDifference();render(data);
 }catch(error){
  if(id!==seq)return;
  if($('intel64-progress'))$('intel64-progress').hidden=true;
  $('intel64-status').textContent='Saved records could not be read. The answer on screen was kept. '+(error.message||'');
 }
}
async function loadSaved(){
 const id=seq,symbol=current.symbol;if(!$('intel64-saved')||!symbol)return;
 try{
  const response=await fetch('/api/v3/ask48?saved=1&symbol='+encodeURIComponent(symbol),{cache:'no-store'});
  const data=await response.json();
  if(id!==seq||symbol!==current.symbol)return;
  const rows=data.saved||[];
  $('intel64-saved').innerHTML=rows.length?rows.map(item=>`<button type="button" data-ask48-id="${esc(item.id)}">${esc(item.context&&item.context.symbol)} · ${esc(item.context&&item.context.start)} to ${esc(item.context&&item.context.end)} · ${esc(item.question)}</button>`).join(''):'<p>No saved answer for this company yet.</p>';
  $('intel64-saved').querySelectorAll('[data-ask48-id]').forEach(button=>button.onclick=()=>{
   const item=rows.find(row=>String(row.id)===button.dataset.ask48Id);
   if(!item){$('intel64-status').textContent='That saved answer is not on this Mac.';return;}
   seq++;current={...blank(),...(item.context||{})};show();render(item);
   $('intel64-status').textContent='Reopened the saved answer. Its original prices and dates were kept.';
  });
 }catch(error){if(id===seq&&$('intel64-saved'))$('intel64-saved').textContent='Saved answers could not be read. '+(error.message||'');}
}
function setup(){
 if($('intel64')||typeof window.changeView!=='function')return;
 const panel=document.createElement('aside');panel.id='intel64';panel.hidden=true;panel.setAttribute('aria-label','Intelligence');
 panel.innerHTML='<button type="button" id="intel64-resize" aria-label="Resize Intelligence" role="separator" aria-orientation="vertical" aria-valuemin="280" aria-valuemax="520" aria-valuenow="360" tabindex="0"></button><header><h2>Intelligence</h2><button type="button" id="intel64-close">Close</button></header><p id="intel64-screen"></p><div id="intel64-chips"></div><form><label for="intel64-question">Question<textarea id="intel64-question" rows="2" maxlength="400"></textarea></label><div id="intel64-actions"><button type="submit">Answer</button><button type="button" id="intel64-retry">Retry</button><button type="button" id="intel64-cancel">Cancel</button><button type="button" data-journal="answer">Save to research</button></div></form><div id="intel64-attach"><input id="intel64-record" maxlength="16" placeholder="Attach a company" aria-label="Attach a company"><button type="button" id="intel64-attach-btn">Attach</button><button type="button" id="intel64-use-page">Use this page</button></div><div id="intel64-suggestions"></div><p id="intel64-progress" hidden>Reading saved records.</p><p id="intel64-status" role="status"></p><div id="intel64-scroll"><p id="intel64-kind"></p><p id="intel64-answer"></p><div id="intel64-figures"></div><details id="intel64-evidence" hidden></details><div id="intel64-saved"></div></div>';
 document.body.append(panel);
 const back=document.createElement('button');back.id='intel64-return';back.hidden=true;back.type='button';back.textContent='Back to investigation';document.body.append(back);
 panel.querySelector('form').onsubmit=event=>{event.preventDefault();ask($('intel64-question').value);};
 $('intel64-close').onclick=closePanel;
 $('intel64-cancel').onclick=()=>{seq++;if($('intel64-progress'))$('intel64-progress').hidden=true;$('intel64-status').textContent='Cancelled. An earlier question will not replace this screen.';};
 $('intel64-retry').onclick=()=>{if(lastQuestion)ask(lastQuestion);else $('intel64-status').textContent='Ask a question before retrying.';};
 $('intel64-use-page').onclick=usePage;
 $('intel64-attach-btn').onclick=()=>{
  const symbol=String($('intel64-record').value||'').trim().toUpperCase();
  if(!/^[A-Z0-9.\-]{1,16}$/.test(symbol)){$('intel64-status').textContent='Enter a company symbol to attach. Nothing was changed.';return;}
  current.symbol=symbol;$('intel64-record').value='';show();noteDifference();
  $('intel64-status').textContent=symbol+' is attached. The answer below stays until you ask.';
 };
 $('intel64-return').onclick=()=>{back.hidden=true;openPanel();};
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('intel64').hidden){event.preventDefault();closePanel();}});
 panel.addEventListener('keydown',event=>{
  if(event.key!=='Tab'||!window.matchMedia('(max-width:800px)').matches)return;
  const items=[...panel.querySelectorAll('button,textarea,input,summary')].filter(item=>!item.disabled&&item.offsetParent!==null);
  if(!items.length)return;
  const first=items[0],last=items[items.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
 });
 const handle=$('intel64-resize');
 function setWidth(width){const next=Math.max(280,Math.min(520,width));document.documentElement.style.setProperty('--intel64-width',next+'px');handle.setAttribute('aria-valuenow',String(Math.round(next)));}
 handle.onpointerdown=event=>{
  if(window.matchMedia('(max-width:800px)').matches)return;
  event.preventDefault();
  const startX=event.clientX,start=panel.getBoundingClientRect().width;
  const limit=Math.min(520,Math.max(280,window.innerWidth-640));
  function move(e){setWidth(Math.min(limit,start+(startX-e.clientX)));}
  function up(){handle.removeEventListener('pointermove',move);handle.removeEventListener('pointerup',up);if(typeof drawChart==='function')drawChart();}
  handle.setPointerCapture(event.pointerId);
  handle.addEventListener('pointermove',move);
  handle.addEventListener('pointerup',up);
 };
 handle.onkeydown=event=>{
  if(window.matchMedia('(max-width:800px)').matches)return;
  const step=event.key==='ArrowLeft'?24:event.key==='ArrowRight'?-24:0;
  if(!step)return;
  event.preventDefault();
  setWidth(panel.getBoundingClientRect().width+step);
  if(typeof drawChart==='function')drawChart();
 };
 document.addEventListener('click',event=>{const hit=event.target.closest('[data-stock-research="intelligence"]');if(!hit)return;event.preventDefault();event.stopPropagation();openFrom({area:'chart'});},true);
 const previous=window.changeView;
 window.changeView=function(viewName){const result=previous.apply(this,arguments);if(AREAS[viewName]&&$('intel64')&&!$('intel64').hidden){screen=screenFor(AREAS[viewName]);noteDifference();}return result;};
 Object.entries(AREAS).filter(([view])=>view!=='home').forEach(([view,area])=>{
  const host=$('view-'+view);if(!host||host.querySelector('[data-intel]'))return;
  const button=document.createElement('button');button.type='button';button.className='ghost-btn';button.dataset.intel=area;button.textContent='Ask Intelligence';
  host.insertBefore(button,host.firstChild);
  button.addEventListener('click',()=>openFrom({area}));
 });
}
document.addEventListener('DOMContentLoaded',setup);
return {openFrom,sync,ask,latest:()=>latest};
})();
window.Ask48=Ask48;
