/* Portfolio stress tests. Results stay separate from the practice ledger. */
const Stress58=(()=>{
  const money=value=>Number.isFinite(value)?value.toLocaleString('en-US',{style:'currency',currency:'USD'}):'Withheld';
  let seq=0,last=null,positions=null,mode='run';
  function host(){
    const view=document.getElementById('view-portfolio');
    if(!view||document.getElementById('stress58'))return;
    view.insertAdjacentHTML('afterbegin','<article class="surface crypto57-panel" id="stress58"><h2>Portfolio Stress Lab</h2><p class="crypto38-foot" id="stress58-note">Cash stays unchanged. This does not edit the practice ledger.</p><div class="crypto38-tools"><label>Scope <select id="stress58-scope"><option value="all">All holdings</option><option value="symbol">One holding</option><option value="sector">One sector</option></select></label><input id="stress58-target" placeholder="Symbol or sector" aria-label="Holding or sector"><label>Change % <input id="stress58-percent" type="number" value="0" step="1" min="-100" max="300"></label></div><div id="stress58-weights"></div><div class="crypto38-tools"><button type="button" class="ghost-btn" id="stress58-run">Apply hypothetical change</button><label>From <input id="stress58-start" type="date"></label><label>To <input id="stress58-end" type="date"></label><button type="button" class="ghost-btn" id="stress58-history">Replay past returns</button></div><div id="stress58-results"></div><div class="crypto38-tools"><button type="button" class="ghost-btn" id="stress58-save">Save this test</button><input id="stress58-id" placeholder="Saved test" aria-label="Saved stress test"><button type="button" class="ghost-btn" id="stress58-open">Reopen saved test</button><button type="button" class="ghost-btn" id="stress58-explain">Explain in Intelligence</button><button type="button" class="ghost-btn" data-journal="stress">Save to research</button></div></article>');
  }
  function weights(){
    const fields=[...document.querySelectorAll('[data-stress-weight]')];
    if(!fields.length||fields.every(field=>field.value===''))return null;
    const out={};
    fields.forEach(field=>{out[field.dataset.stressWeight]=Number(field.value);});
    return out;
  }
  function bars(result){
    const rows=result.contributions||[];
    const scale=Math.max(...rows.map(row=>Math.abs(row.contributionUSD)),1);
    return rows.map(row=>`<div class="p46-row"><span>${row.symbol}</span><strong>${money(row.contributionUSD)}</strong><i style="width:${Math.abs(row.contributionUSD)/scale*100}%"></i></div>`).join('');
  }
  function render(packet){
    const result=packet.result||packet;
    last=packet.result?packet: {result};
    const box=document.getElementById('stress58-results');
    if(!box)return;
    const lines=(result.holdings||[]).map(row=>{
      const observed=(row.history&&row.history.observations||[]).map(item=>`${item.date} ${item.price} (${item.source})`).join(' → ');
      const gaps=row.history&&row.history.gaps&&row.history.gaps.length?` Missing ${row.history.gaps.join(', ')}.`:'';
      return `<p><strong>${row.symbol}</strong> · ${row.sector} · ${row.asset} · recorded ${money(row.valueUSD)} · allocated ${money(row.allocatedUSD)} · stressed ${money(row.stressedUSD)} · contribution ${money(row.contributionUSD)}. ${row.note||''} ${observed}${gaps}</p>`;
    }).join('');
    const common=result.common&&(result.common.start!==result.start||result.common.end!==result.end)?`<button type="button" class="ghost-btn" id="stress58-common">Use common period ${result.common.start} to ${result.common.end}</button>`:'';
    box.innerHTML=`<p>Cash ${money(result.cashUSD)} unchanged. Recorded ${money(result.recordedUSD)}. Stressed ${money(result.stressedUSD)}. Change ${money(result.changeUSD)}. ${result.status==='withheld'?'Combined total withheld.':''}</p>${bars(result)}${lines}${common}<p class="crypto38-foot">${(result.assumptions||[]).slice(0,3).join(' ')}</p>`;
    document.getElementById('stress58-common')?.addEventListener('click',()=>{
      document.getElementById('stress58-start').value=result.common.start;
      document.getElementById('stress58-end').value=result.common.end;
      history();
    });
  }
  async function post(body){
    const id=++seq;
    const response=await fetch('/api/v3/stress58',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)});
    const data=await response.json();
    if(id!==seq)return null;
    if(!response.ok||data.error)throw Error(data.error||'The stress test could not be calculated.');
    return data;
  }
  function payload(action){
    return {action,scope:document.getElementById('stress58-scope').value,percent:Number(document.getElementById('stress58-percent').value),
      symbol:document.getElementById('stress58-target').value.trim().toUpperCase(),sector:document.getElementById('stress58-target').value.trim(),
      weights:weights(),start:document.getElementById('stress58-start').value,end:document.getElementById('stress58-end').value};
  }
  async function run(){
    mode='run';
    const data=await post(payload('run'));
    if(data)render(data);
  }
  async function history(){
    mode='history';
    const data=await post(payload('history'));
    if(data)render(data);
  }
  function weightForm(){
    const box=document.getElementById('stress58-weights');
    const rows=positions?.holdings||[];
    box.innerHTML=rows.length?rows.map(row=>`<label>${row.symbol} weight % <input data-stress-weight="${row.symbol}" type="number" min="0" max="100" step="0.1" value="${row.weightPct??''}"></label>`).join(''):'<p class="crypto38-foot">No open holdings. A cash balance can still be shown, and it will not be shocked.</p>';
    box.querySelectorAll('input').forEach(input=>input.addEventListener('change',()=>{run().catch(error=>document.getElementById('stress58-note').textContent=error.message);}));
  }
  async function load(){
    host();
    try{
      const response=await fetch('/api/v3/stress58',{cache:'no-store'});
      positions=await response.json();
      weightForm();
      const note=document.getElementById('stress58-note');
      if(note)note.textContent=`Cash ${money(positions.cashUSD)}. ${(positions.assumptions||[])[0]||''}`;
    }catch(error){document.getElementById('stress58-note').textContent=error.message;}
  }
  function packet(){
    const result=(last&&last.result)||last||{};
    return {symbol:'PORTFOLIO',origin:'stress',title:'Portfolio stress '+(last&&last.id||''),start:result.start||'',end:result.end||'',
      evidence:{startPrice:result.recordedUSD,endPrice:result.stressedUSD,source:'Saved portfolio stress on this Mac',capturedAt:Date.now(),
        answer:`Recorded ${result.recordedUSD} USD, stressed ${result.stressedUSD} USD, cash ${result.cashUSD} USD.`,
        basis:(result.assumptions||[]).slice(0,2).join(' '),
        qualification:'This journal entry keeps the saved stress figures. It does not change the practice ledger.'}};
  }
  function setup(){
    host();
    document.getElementById('stress58-run')?.addEventListener('click',()=>run().catch(error=>document.getElementById('stress58-note').textContent=error.message));
    document.getElementById('stress58-percent')?.addEventListener('change',()=>run().catch(()=>{}));
    document.getElementById('stress58-history')?.addEventListener('click',()=>history().catch(error=>document.getElementById('stress58-note').textContent=error.message));
    document.getElementById('stress58-save')?.addEventListener('click',async()=>{
      const data=await post({...payload(mode),action:'save',mode});
      if(!data)return;
      last=data;document.getElementById('stress58-id').value=data.id;sessionStorage.setItem('md-stress58',data.id);render(data);
    });
    document.getElementById('stress58-open')?.addEventListener('click',async()=>{
      const ident=document.getElementById('stress58-id').value.trim();
      const response=await fetch('/api/v3/stress58?id='+encodeURIComponent(ident),{cache:'no-store'});
      const data=await response.json();
      if(data.error){document.getElementById('stress58-note').textContent=data.error;return;}
      last=data;render(data);
    });
    document.getElementById('stress58-explain')?.addEventListener('click',()=>{
      if(!window.Ask48)return;
      Ask48.openFrom({symbol:'PORTFOLIO',stressId:document.getElementById('stress58-id').value.trim()||sessionStorage.getItem('md-stress58')||''});
      Ask48.ask('What drives this portfolio result?');
    });
    load();
  }
  document.addEventListener('DOMContentLoaded',setup);
  return {packet,open:setup};
})();
