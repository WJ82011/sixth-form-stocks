/* Compact review of one completed-session move. Saved prices and events only. */
const Move44=window.Move44=(()=>{
  let request=0, key='', shown=null;
  const $=id=>document.getElementById(id);
  const ny=ms=>new Date(ms).toLocaleDateString('en-CA',{timeZone:'America/New_York'});
  const money=value=>Number.isFinite(value)?value.toLocaleString('en-GB',{style:'currency',currency:'USD'}):'—';
  const pct=value=>Number.isFinite(value)?`${value>=0?'+':''}${value.toFixed(2)}%`:'—';
  function panel(){
    let node=$('move44');
    if(node)return node;
    node=document.createElement('section');
    node.id='move44';node.className='move44';node.hidden=true;
    node.innerHTML='<header><h2>Review this move</h2><button type="button" id="move44-close">Close</button></header><p id="move44-status" role="status"></p><div id="move44-body"></div>';
    document.body.append(node);
    node.querySelector('#move44-close').addEventListener('click',clear);
    return node;
  }
  function place(){
    const node=panel();
    const chart=document.getElementById('look43-coverage');
    const heat=document.getElementById('heat-story');
    const home=document.getElementById('view-home')?.classList.contains('active');
    if(home&&chart)chart.after(node);
    else if(heat)heat.after(node);
    else document.getElementById('main-chart-panel')?.after(node);
  }
  function clear(){
    request++;key='';shown=null;
    const node=panel();
    node.hidden=true;
    $('move44-status').textContent='';
    $('move44-body').innerHTML='';
  }
  function list(title,rows,total,empty){
    const items=(rows||[]).map(row=>{
      const link=row.source?`<a href="${escapeHtml(row.source)}" target="_blank" rel="noopener noreferrer">Original source</a>`:'No source link was saved.';
      const timing=row.timing==='date'?'Timing uncertain. The source gave a date without a time.':'';
      return `<li><strong>${escapeHtml(row.title)}</strong><small>${escapeHtml(row.kindLabel)} · ${escapeHtml(row.publisher)} · ${escapeHtml(row.timeLabel)}</small><small>${timing?escapeHtml(timing)+' ':''}${link}</small></li>`;
    }).join('');
    const more=total>rows.length?`<p>Showing ${rows.length} of ${total} saved items.</p>`:'';
    return `<section><h3>${title}</h3>${items?`<ul>${items}</ul>${more}`:`<p>${empty}</p>`}</section>`;
  }
  function render(data){
    const status=$('move44-status'), body=$('move44-body');
    if(data.status!=='ready'){
      status.textContent=(data.symbol||'Company')+' · '+(data.start||'')+' → '+(data.end||'');
      body.innerHTML=`<p>${escapeHtml(data.reason||'This move cannot be reviewed from the saved prices.')}</p><p>${escapeHtml((data.gaps||[]).join(' '))}</p>`;
      return;
    }
    const compare=data.comparison||{};
    const difference=compare.status==='ready'?`${compare.differencePP>=0?'+':''}${compare.differencePP.toFixed(2)} percentage points versus SPY`:'';
    status.textContent=`${data.symbol} · ${data.start} → ${data.end} · ${data.sessions.length} completed session${data.sessions.length===1?'':'s'}`;
    shown=data;
    body.innerHTML=`<p><strong>${escapeHtml(money(data.startPrice))}</strong> on ${escapeHtml(data.start)} to <strong>${escapeHtml(money(data.endPrice))}</strong> on ${escapeHtml(data.end)}. Return ${escapeHtml(pct(data.returnPct))}.</p><p>${escapeHtml(data.basis)}</p><p>${escapeHtml(data.source)}</p><p>${compare.status==='ready'?`SPY ${escapeHtml(money(compare.startPrice))} to ${escapeHtml(money(compare.endPrice))}, ${escapeHtml(pct(compare.returnPct))}. Difference ${escapeHtml(difference)}. Same close-to-close basis.`:`${escapeHtml(compare.reason||'SPY comparison is unavailable.')}`}</p>${(data.gaps||[]).map(gap=>`<p>${escapeHtml(gap)}</p>`).join('')}<p>${escapeHtml(data.evidence)}</p><button type="button" data-journal="move">Save to research</button>${list('Known before or during the move',data.before,data.beforeCount||0,'Nothing saved was published before the end of this move.')}${list('Reported afterwards',data.after,data.afterCount||0,'No saved coverage is timestamped after this move.')}${list('Date only · timing uncertain',data.uncertain,data.uncertainCount||0,'No date-only items are saved.')}`;
  }
  async function open(spec){
    const symbol=typeof safeSymbol==='function'&&safeSymbol(spec.symbol)?spec.symbol:'';
    if(!symbol||!spec.start||!spec.end)return;
    const next=symbol+'|'+spec.start+'|'+spec.end;
    const id=++request;key=next;
    place();
    const node=panel();
    node.hidden=false;
    $('move44-status').textContent='Reading saved prices for '+symbol+'…';
    $('move44-body').innerHTML='';
    try{
      const data=await api('/api/v3/move44?symbol='+encodeURIComponent(symbol)+'&start='+encodeURIComponent(spec.start)+'&end='+encodeURIComponent(spec.end));
      if(id!==request||key!==next||data.symbol&&data.symbol!==symbol)return;
      render(data);
    }catch(error){
      if(id!==request||key!==next)return;
      $('move44-status').textContent=symbol;
      $('move44-body').innerHTML='<p>'+escapeHtml(error.message)+'</p>';
    }
  }
  function fromPoint(point){
    if(!point||!Number.isFinite(point.t)||!E.selected)return;
    if(E.heatmapWindow?.start&&E.heatmapWindow?.end){
      open({symbol:E.selected,start:E.heatmapWindow.start,end:E.heatmapWindow.end});
      return;
    }
    const end=ny(point.t);
    const points=(window.Replay43?.active&&Replay43.prices?Replay43.prices():E.chartPoints)||[];
    const earlier=points.filter(row=>row.t<=point.t).map(row=>ny(row.t)).filter(day=>day<end);
    const start=earlier.length?earlier.at(-1):'';
    if(!start){
      place();panel().hidden=false;
      $('move44-status').textContent=E.selected;
      $('move44-body').innerHTML='<p>Select a later completed session. One price cannot show a move.</p>';
      return;
    }
    open({symbol:E.selected,start,end});
  }
  return {open,clear,fromPoint,current:()=>shown};
})();
if(new URLSearchParams(location.search).get('review440')==='1'){
  const marker=document.createElement('p');
  marker.id='move440-result';
  marker.textContent='RUNNING';
  document.documentElement.append(marker);
  document.addEventListener('DOMContentLoaded',()=>{
    const steps=[];
    const note=text=>marker.textContent=text;
    const wait=(test,left=80)=>new Promise(resolve=>{
      const tick=()=>{if(test()||left<=0)resolve(test());else{left--;setTimeout(tick,50)}};
      tick();
    });
    (async()=>{
      const ready=await wait(()=>typeof E!=='undefined'&&typeof setSelected==='function'&&typeof setChartRange==='function');
      if(!ready){note('FAIL page did not start');return}
      await Move44.open({symbol:'TTWO',start:'2026-10-30',end:'2026-11-06'});
      const ttwo=await wait(()=>document.getElementById('move44-body').textContent.includes('190.17')&&document.getElementById('move44-status').textContent.includes('TTWO'));
      steps.push(ttwo?'PASS Take-Two multi-day review':'FAIL Take-Two multi-day review');
      setSelected('AMD');
      const cleared=await wait(()=>document.getElementById('move44').hidden&&!document.getElementById('move44-body').textContent.includes('190.17'));
      steps.push(cleared?'PASS ticker change clears Take-Two':'FAIL ticker change clears Take-Two');
      await Move44.open({symbol:'AMD',start:'2026-10-30',end:'2026-11-06'});
      const amd=await wait(()=>document.getElementById('move44-status').textContent.includes('AMD')&&document.getElementById('move44-body').textContent.includes('504.80')&&!document.getElementById('move44-body').textContent.includes('190.17'));
      steps.push(amd?'PASS AMD replaces Take-Two':'FAIL AMD replaces Take-Two');
      setChartRange('1M');
      const ranged=await wait(()=>document.getElementById('move44').hidden&&document.getElementById('move44-body').textContent==='');
      steps.push(ranged?'PASS timeframe change clears the review':'FAIL timeframe change clears the review');
      await Move44.open({symbol:'TTWO',start:'2026-11-04',end:'2026-11-09'});
      const gap=await wait(()=>{
        const text=document.getElementById('move44-body').textContent;
        return text.includes('Missing saved SPY close on 2026-11-09')&&text.includes('2026-11-09 16:05')&&text.includes('do not explain');
      });
      steps.push(gap?'PASS missing SPY and after-hours coverage':'FAIL missing SPY and after-hours coverage');
      note(steps.join(' | '));
    })().catch(error=>note('FAIL '+error.message));
  });
}
