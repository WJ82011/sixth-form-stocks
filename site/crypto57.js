/* Crypto Forecast Lab. Historical tests stay separate from issued forecasts. */
const Crypto57=(()=>{
  const money=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'});
  const products=['BTC-USD','ETH-USD','SOL-USD','XRP-USD','DOGE-USD','ADA-USD','LINK-USD','AVAX-USD','LTC-USD'];
  let product='BTC-USD',seq=0;

  function host(){
    const crypto=document.getElementById('view-crypto');
    const forecast=document.getElementById('view-forecast');
    if(crypto&&!document.getElementById('crypto57')){
      crypto.insertAdjacentHTML('beforeend','<article class="surface crypto57-panel" id="crypto57"><h2>Crypto Forecast Lab</h2><p id="crypto57-note" class="crypto38-foot">Completed Coinbase USD candles. Times are UTC.</p><div class="crypto38-switches" id="crypto57-assets"></div><div id="crypto57-results"></div><div class="crypto38-tools"><button type="button" class="ghost-btn" id="crypto57-train">Train on saved candles</button><button type="button" class="ghost-btn" id="crypto57-explain">Explain in Intelligence</button></div></article>');
    }
    if(forecast&&!document.getElementById('crypto57-link')){
      forecast.insertAdjacentHTML('beforeend','<article class="surface crypto57-panel" id="crypto57-link"><h2>Crypto forecasts</h2><p class="crypto38-foot">Bitcoin, Ethereum and the other Coinbase USD markets use the Crypto page for training. Equity forecasts on this page stay on the New York calendar.</p><button type="button" class="ghost-btn" id="crypto57-open">Open the crypto forecast</button></article>');
      document.getElementById('crypto57-open').addEventListener('click',()=>{if(window.changeView)window.changeView('crypto');});
    }
  }
  function line(row){
    const gaps=row.gaps&&row.gaps.length?` ${row.gaps.length} gap${row.gaps.length===1?'':'s'} left visible.`:'';
    if(row.status==='insufficient'||row.status==='withheld')return `<p><strong>${row.label}</strong> · ${row.frequency} · ${row.reason}${gaps}</p>`;
    return `<p><strong>${row.label}</strong> · ${row.frequency} · train ${row.trainCount}, tune ${row.tuneCount}, later test ${row.testCount}. Error ${Number(row.modelErrorPP).toFixed(2)} pp · unchanged ${Number(row.unchangedErrorPP).toFixed(2)} · historical average ${Number(row.driftErrorPP).toFixed(2)}. Range contained the candle in ${Number(row.rangeCoveragePct).toFixed(0)}% of ${row.rangeCount} tests. ${row.status==='learned'?'Forecast saved.':'Forecast withheld.'}${gaps}</p>`;
  }
  function render(data){
    const box=document.getElementById('crypto57-results');
    if(!box)return;
    const issued=(data.issued||[]).map(row=>`<p>${row.record}: ${row.horizon} · ${money.format(row.forecastPrice)} · issued for ${row.target} UTC · ${row.outcome?row.outcome.rule:'Waiting for the target candle.'}</p>`).join('');
    box.innerHTML=(data.horizons||[]).map(line).join('')+(issued||'<p>No issued crypto forecast is saved for this market.</p>')+`<p class="crypto38-foot">${data.exchange||'Coinbase Exchange'} · ${data.quote||'USD'} · ${data.timezone||'UTC'}. ${data.notice||''}</p>`;
  }
  async function load(train){
    const id=++seq,expected=product;
    host();
    const note=document.getElementById('crypto57-note');
    if(note)note.textContent=train?'Training on saved candles…':'Reading the saved report…';
    try{
      const response=train
        ?await fetch('/api/v3/crypto57',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({product})})
        :await fetch('/api/v3/crypto57?product='+product,{cache:'no-store'});
      const data=await response.json();
      if(id!==seq||expected!==product)return;
      render(data.error?{horizons:[],notice:data.error}:data);
    }catch(error){if(id===seq&&note)note.textContent=error.message;}
  }
  function setup(){
    host();
    const box=document.getElementById('crypto57-assets');
    if(!box)return;
    box.innerHTML=products.map(item=>`<button type="button" class="ghost-btn" data-crypto57="${item}" aria-pressed="${item===product}">${item}</button>`).join('');
    box.querySelectorAll('[data-crypto57]').forEach(button=>button.addEventListener('click',()=>{
      product=button.dataset.crypto57;
      box.querySelectorAll('[data-crypto57]').forEach(item=>item.setAttribute('aria-pressed',String(item.dataset.crypto57===product)));
      load(false);
    }));
    document.getElementById('crypto57-train').addEventListener('click',()=>load(true));
    document.getElementById('crypto57-explain').addEventListener('click',()=>{
      if(!window.Ask48)return;
      Ask48.openFrom({symbol:product,product,range:'crypto'});
      Ask48.ask('How has this crypto model performed?');
    });
    load(false);
  }
  document.addEventListener('DOMContentLoaded',setup);
  return {load,setup};
})();
