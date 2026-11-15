/* Saved-session replay. Later prices, headlines and session extremes stay hidden.
   Playback never arms or checks price alerts. */
const Replay43=window.Replay43=(()=>{
  const state={active:false,playing:false,cursor:0,speed:60,timer:0,events:[],trades:[],symbol:'',day:''};
  const reduced=()=>document.body?.dataset?.motion==='off'||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  function frame(cursor){
    const prices=state.trades.filter(row=>row.t<=cursor);
    const timed=[],undated=[];
    for(const event of state.events){
      if(Number.isFinite(event.publishedAt)){if(event.publishedAt<=cursor)timed.push(event)}
      else undated.push(event);
    }
    const values=prices.map(row=>row.p);
    const gaps=[];
    for(let i=1;i<prices.length;i++)if(prices[i].t-prices[i-1].t>5*60*1000)gaps.push({from:prices[i-1].t,to:prices[i].t,open:false});
    if(prices.length&&cursor-prices.at(-1).t>5*60*1000)gaps.push({from:prices.at(-1).t,to:cursor,open:true});
    return {prices,timed,undated,high:values.length?Math.max(...values):null,low:values.length?Math.min(...values):null,gaps,cursor};
  }
  function current(){return frame(state.cursor)}
  function prices(){return current().prices.map(row=>({t:row.t,p:row.p,source:'replay'}))}
  function render(){
    const box=document.getElementById('replay43-readout');if(!box)return;
    const view=current();
    const when=state.active?new Date(state.cursor).toLocaleString('en-GB',{hour12:false})+' local':'Replay is off';
    const gap=view.gaps.length?view.gaps.length+' coverage gap'+(view.gaps.length===1?'':'s')+' inside the revealed window.':'No coverage gap inside the revealed window.';
    const timed=view.timed.map(event=>'<li>'+escapeHtml(event.title)+' · '+escapeHtml(event.timeLabel||'')+'</li>').join('')||'<li>No timed event has been reached.</li>';
    const undated=view.undated.map(event=>'<li>'+escapeHtml(event.title)+' · timing unknown</li>').join('')||'<li>No date-only event in this saved timeline.</li>';
    box.innerHTML='<p><strong>'+escapeHtml(when)+'</strong> · '+escapeHtml(state.symbol||'No stock')+(state.day?' · '+escapeHtml(state.day):'')+'</p><p>'+gap+' High '+fmt(view.high)+' · low '+fmt(view.low)+' from revealed prices only.</p><p>Timed events</p><ul>'+timed+'</ul><p>Date-only events, kept separate</p><ul>'+undated+'</ul><p>Replay does not arm or trigger price alerts.</p>';
    window.Chart43?.sync();
    if(typeof drawChart==='function')drawChart();
    if(window.MarketDeskTerminal?.refresh)MarketDeskTerminal.refresh();
  }
  function fmt(value){return Number.isFinite(value)?value.toFixed(2):'—'}
  function stopTimer(){clearInterval(state.timer);state.timer=0;state.playing=false}
  function stop(){
    stopTimer();
    state.active=false;
    state.cursor=0;
    state.trades=[];
    state.events=[];
    state.symbol='';
    state.day='';
    const status=document.getElementById('replay43-status');
    if(status)status.textContent='Replay is off. Load a saved session to play again.';
    render();
  }
  function play(){
    if(!state.active)return;
    stopTimer();state.playing=true;
    const wait=reduced()?400:200;
    state.timer=setInterval(()=>{
      const last=state.trades.at(-1)?.t||state.cursor;
      state.cursor=Math.min(last,state.cursor+1000*state.speed);
      render();
      if(state.cursor>=last)stopTimer();
    },wait);
  }
  function step(){
    if(!state.active)return;
    stopTimer();
    const next=state.trades.find(row=>row.t>state.cursor);
    state.cursor=next?next.t:state.cursor;
    render();
  }
  async function load(){
    const symbol=tapeSelectedSymbol();
    const day=document.getElementById('tape-date')?.value||'';
    const status=document.getElementById('replay43-status');
    status.textContent='Reading the saved session…';
    try{
      const review=await tapeLoadReview(day);
      if(!review?.events?.length)throw new Error('This company has no saved trades for that session.');
      const events=await api('/api/v3/events42?symbol='+encodeURIComponent(symbol));
      if(tapeSelectedSymbol()!==symbol)throw new Error('The selected stock changed. Load its saved session again.');
      if(E.selected!==symbol)setSelected(symbol);
      stopTimer();
      state.trades=review.events.map(row=>({t:row.t,p:row.p,v:row.v})).filter(row=>Number.isFinite(row.t)&&Number.isFinite(row.p));
      state.events=events.events||[];
      state.symbol=symbol;state.day=day||'latest saved session';
      state.cursor=state.trades[0].t;state.active=true;
      status.textContent='Saved session loaded. Playback stays on this Mac.';
      if(typeof changeView==='function')changeView('overview');
      render();
    }catch(error){status.textContent=error.message}
  }
  function show(packet){
    stopTimer();
    state.trades=(packet.prices||[]).filter(row=>Number.isFinite(row.t)&&Number.isFinite(row.p));
    state.events=packet.timedEvents||[];
    state.cursor=packet.cursor||0;
    state.symbol=packet.symbol||state.symbol;
    state.day=packet.day||state.day;
    state.active=true;
    render();
  }
  function follow(){if(!state.active)return;state.cursor=state.trades.at(-1)?.t||state.cursor;render()}
  function mount(){
    const tape=document.getElementById('view-tape');if(!tape||document.getElementById('replay43'))return;
    const panel=document.createElement('section');
    panel.id='replay43';panel.className='replay43';
    panel.innerHTML='<div class="replay43-head"><div><p class="desk-eyebrow">MARKET REPLAY / SAVED SESSION</p><h2>Play a saved session</h2><p>The chart, trades and timed events move together. Anything later than the replay clock stays hidden.</p></div></div><div class="replay43-controls"><button type="button" id="replay43-load">Load saved session</button><button type="button" id="replay43-play">Play</button><button type="button" id="replay43-pause">Pause</button><button type="button" id="replay43-step">Step forward</button><label>Speed <select id="replay43-speed"><option value="30">30×</option><option value="60" selected>60×</option><option value="300">300×</option></select></label></div><p id="replay43-status" role="status">Choose a stock on this page, then load a saved session. No internet is required for records already on this Mac.</p><div id="replay43-readout"></div>';
    tape.appendChild(panel);
    panel.querySelector('#replay43-load').onclick=load;
    panel.querySelector('#replay43-play').onclick=play;
    panel.querySelector('#replay43-pause').onclick=()=>{stopTimer();render()};
    panel.querySelector('#replay43-step').onclick=step;
    panel.querySelector('#replay43-speed').onchange=event=>{state.speed=Number(event.target.value)||60};
  }
  document.addEventListener('DOMContentLoaded',mount);
  return {get active(){return state.active},get cursor(){return state.cursor},prices,frame:current,follow,stop,show,get symbol(){return state.symbol}};
})();
