/* Results review on the company page. Figures come from saved SEC facts. */
(function(){
  function post(body){
    return fetch('/api/v3/earnings62',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(r=>r.json());
  }
  function money(value){
    if(value==null||Number.isNaN(Number(value)))return 'unavailable';
    return 'USD '+Number(value).toLocaleString('en-GB',{maximumFractionDigits:0});
  }
  function draw(canvas, card){
    const ctx=canvas.getContext('2d');
    canvas.width=640; canvas.height=140;
    ctx.clearRect(0,0,640,140);
    const change=card.revenueChange||{};
    if(!change.available){ctx.fillStyle='#9fb0c8'; ctx.fillText(change.reason||'No comparable earlier period',16,40); return;}
    const values=[change.from, change.to];
    const max=Math.max(...values.map(Math.abs))||1;
    values.forEach((value,index)=>{
      const height=Math.max(4,Math.abs(value)/max*80);
      ctx.fillStyle=index?'#4c8dff':'#8ec5ff';
      ctx.fillRect(40+index*120,110-height,48,height);
      ctx.fillStyle='#d5e2f2'; ctx.fillText(money(value),40+index*120,124);
    });
    ctx.fillText('Earlier',40,20); ctx.fillText('Latest',160,20);
  }
  function render(data){
    const host=document.getElementById('earnings62-body');
    host.innerHTML='';
    if(data.operatingProfit){const line=document.createElement('p'); line.textContent=data.operatingProfit; host.append(line);}
    if(data.analystExpectations){const line=document.createElement('p'); line.textContent=data.analystExpectations; host.append(line);}
    (data.missingQuarters||[]).forEach(line=>{const p=document.createElement('p'); p.textContent=line; host.append(p);});
    (data.cards||[]).forEach(card=>{
      const block=document.createElement('section');
      const title=document.createElement('h3');
      title.textContent=(card.type==='annual'?'Full year':'Quarter')+' '+card.start+' to '+card.end+' · '+card.currency+' · '+card.durationDays+' days';
      const figures=document.createElement('p');
      const filed=(card.revenue&&card.revenue.filed)||(card.profit&&card.profit.filed)||'filing date not saved';
      figures.textContent='Revenue '+money(card.revenue&&card.revenue.value)+'. Net profit '+money(card.profit&&card.profit.value)+'. Net margin '+(card.netMarginPct==null?'unavailable':card.netMarginPct.toFixed(2)+'%')+'. Filed '+filed+'. '+(card.note||'');
      const canvas=document.createElement('canvas');
      block.append(title, figures, canvas);
      (card.warnings||[]).forEach(warning=>{const p=document.createElement('p'); p.textContent=warning; block.append(p);});
      host.append(block);
      draw(canvas, card);
    });
    document.getElementById('earnings62-status').textContent=data.status==='ready'?data.cards.length+' saved period'+(data.cards.length===1?'':'s')+'.':(data.notice||'');
  }
  function symbol(){
    return (document.getElementById('company-select')&&document.getElementById('company-select').value)||(window.E&&E.selected)||'AAPL';
  }
  function mount(){
    if(document.getElementById('earnings62')||!document.getElementById('view-company'))return;
    const panel=document.createElement('section');
    panel.className='fh-panel'; panel.id='earnings62';
    panel.innerHTML='<div class="fh-head"><div><p class="desk-eyebrow">RESULTS / SAVED FILINGS</p><h2>Results review</h2><p>Revenue and net profit from saved SEC facts. A missing figure stays missing.</p></div><div class="fh-actions"><button type="button" class="primary-btn" id="earnings62-read">Read saved results</button><button type="button" class="ghost-btn" id="earnings62-save">Save this review</button><button type="button" class="ghost-btn" id="earnings62-price">Price window</button><button type="button" class="ghost-btn" id="earnings62-open">Reopen saved</button></div></div><p id="earnings62-status" role="status">Choose a company, then read its saved results.</p><div id="earnings62-body"></div>';
    document.getElementById('view-company').insertBefore(panel, document.getElementById('events42'));
    document.getElementById('earnings62-read').onclick=async()=>{
      const data=await fetch('/api/v3/earnings62?symbol='+encodeURIComponent(symbol())).then(r=>r.json());
      render(data);
    };
    document.getElementById('earnings62-save').onclick=async()=>{
      const data=await post({action:'save', symbol:symbol()});
      render(data);
      if(data.id)sessionStorage.setItem('md-earnings62', data.id);
    };
    document.getElementById('earnings62-open').onclick=async()=>{
      const ident=sessionStorage.getItem('md-earnings62');
      if(!ident){document.getElementById('earnings62-status').textContent='Save a results review first.';return;}
      render(await fetch('/api/v3/earnings62?id='+encodeURIComponent(ident)).then(r=>r.json()));
    };
    document.getElementById('earnings62-price').onclick=async()=>{
      const data=await post({action:'reaction', symbol:symbol(), publishedAt:null});
      document.getElementById('earnings62-status').textContent=data.notice||data.error||'';
    };
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded', mount); else mount();
})();
