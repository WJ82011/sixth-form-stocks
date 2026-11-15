/* Decision practice. The server returns only the records the replay clock has reached. */
const Practice67=window.Practice67=(()=>{
  const state={id:'',symbol:'',timer:0,decision:'',end:0};
  const $=id=>document.getElementById(id);
  const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function speed(){return Number($('practice67-speed')?.value)||60}
  function post(body){
    return fetch('/api/v3/practice67',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(async response=>{
      const data=await response.json();
      if(!response.ok||data.error)throw new Error(data.error||'Practice could not continue.');
      return data;
    });
  }
  function clock(ms){return Number.isFinite(ms)?new Date(ms).toLocaleString('en-GB',{hour12:false,timeZone:'America/New_York'})+' New York':'Not reached'}
  function apply(packet){
    if(!packet||!packet.frame)return;
    state.id=packet.id;state.symbol=packet.symbol;state.end=packet.end;
    if(typeof E!=='undefined'&&E.selected===packet.symbol&&window.Replay43?.show)Replay43.show({...packet.frame,symbol:packet.symbol,day:packet.day});
    const box=$('practice67-readout');if(!box)return;
    const frame=packet.frame;
    const events=frame.timedEvents.length?frame.timedEvents.map(event=>'<li>'+esc(event.title)+' · '+esc(clock(event.publishedAt))+'</li>').join(''):'<li>No timed record has been reached.</li>';
    const decisions=(packet.decisions||[]).map(item=>'<li><button type="button" data-practice-review="'+esc(item.id)+'">'+esc(item.expectation)+'</button> · clock '+esc(clock(item.cursor))+'</li>').join('')||'<li>No decision saved yet.</li>';
    box.innerHTML='<p><strong>'+esc(packet.status)+'</strong> · '+esc(packet.symbol)+' · '+esc(clock(frame.cursor))+'</p><p>Revealed high '+esc(frame.high??'—')+' · low '+esc(frame.low??'—')+'. '+esc(frame.notice)+'</p><p>'+esc(frame.notReached)+' later records are hidden. '+esc(frame.unverifiedTiming)+' records have no verified publication time.</p><ul>'+events+'</ul><p>Decisions</p><ul>'+decisions+'</ul>';
    const status=$('practice67-status');
    if(status)status.textContent=packet.status==='ended'?'The session has ended. You can ask for a separate review.':'Practice is using only the records reached so far.';
  }
  function stopTimer(){clearInterval(state.timer);state.timer=0}
  async function tick(){
    try{
      const packet=await post({action:'play',id:state.id,speed:speed()});
      apply(packet);
      if(packet.status==='ended')stopTimer();
    }catch(error){stopTimer();$('practice67-status').textContent=error.message}
  }
  async function coverage(){
    const symbol=document.getElementById('tape-symbol')?.value||(typeof E!=='undefined'&&E.selected)||'';
    const day=$('practice67-day').value;
    $('practice67-status').textContent='Checking saved coverage…';
    const packet=await post({action:'preview',symbol,day});
    const cover=packet.coverage;
    $('practice67-status').textContent=packet.symbol+' · '+cover.tradeCount+' saved trades · '+cover.gapCount+' gaps · '+cover.timedEvents+' timed records · '+cover.unverifiedTiming+' without a verified time. '+cover.notice;
  }
  async function begin(){
    stopTimer();
    const symbol=document.getElementById('tape-symbol')?.value||(typeof E!=='undefined'&&E.selected)||'';
    const packet=await post({action:'start',symbol,day:$('practice67-day').value,startAt:null,startMode:$('practice67-mode').value});
    if(typeof setSelected==='function')setSelected(packet.symbol);
    if(typeof changeView==='function')changeView('home');
    apply(packet);
  }
  async function review(id){
    state.decision=id;
    const result=await post({action:'review',decisionId:id});
    const box=$('practice67-outcome');
    if(result.status!=='ready'){box.textContent=result.notice;return}
    const links=(result.links||[]).map(link=>'<a href="'+esc(link.url)+'" target="_blank" rel="noopener noreferrer">'+esc(link.title||link.url)+'</a>').join(' · ');
    box.innerHTML='<p>'+esc(result.notice)+'</p><p>Original expectation: '+esc(result.original.expectation)+'</p><p>Evidence I wrote: '+esc(result.original.evidence||'Not written.')+'</p><p>Recorded return '+Number(result.returnPct).toFixed(2)+'% from '+esc(result.startPrice)+' to '+esc(result.endPrice)+'.</p><p>'+(links||'No source link was saved with the reached events.')+'</p>';
  }
  function mount(){
    const tape=document.getElementById('view-tape');if(!tape||$('practice67'))return;
    const panel=document.createElement('section');
    panel.id='practice67';
    panel.innerHTML='<p class="desk-eyebrow">DECISION PRACTICE</p><h2>Practice a decision</h2><p>Choose a saved session, see the coverage, then move the clock yourself. Later prices stay on this Mac until you reach them. The review point is the end of that saved session.</p><div class="replay43-controls"><label>Session date<input id="practice67-day" type="date"></label><label>Starting point<select id="practice67-mode"><option value="open">First saved trade</option><option value="after-gap">After the first coverage gap</option></select></label><button type="button" id="practice67-coverage">Show coverage</button><button type="button" id="practice67-begin">Begin</button><button type="button" id="practice67-step">Step</button><button type="button" id="practice67-play">Play</button><button type="button" id="practice67-pause">Pause</button><button type="button" id="practice67-restart">Restart</button><button type="button" id="practice67-end">End session</button><label>Speed<select id="practice67-speed"><option value="30">30×</option><option value="60" selected>60×</option><option value="300">300×</option></select></label></div><p id="practice67-status" role="status">Choose the company on this page and a session date.</p><div id="practice67-readout"></div><label>What I expect<textarea id="practice67-expect"></textarea></label><label>Evidence I can see<textarea id="practice67-evidence"></textarea></label><label>What would change my mind<textarea id="practice67-mind"></textarea></label><button type="button" id="practice67-save">Save decision</button><div id="practice67-outcome"></div><label>What I learned<textarea id="practice67-learned"></textarea></label><label>Did the evidence support the idea?<select id="practice67-assessment"><option value="supported">It supported the idea</option><option value="challenged">It challenged the idea</option><option value="unclear">It is still unclear</option></select></label><button type="button" id="practice67-reflect">Save reflection</button><button type="button" id="practice67-journal">Add to journal</button><button type="button" id="practice67-pack">Include in a research pack</button>';
    tape.appendChild(panel);
    $('practice67-coverage').onclick=()=>coverage().catch(error=>{$('practice67-status').textContent=error.message});
    $('practice67-begin').onclick=()=>begin().catch(error=>{$('practice67-status').textContent=error.message});
    $('practice67-step').onclick=()=>post({action:'step',id:state.id,speed:speed()}).then(apply).catch(error=>{$('practice67-status').textContent=error.message});
    $('practice67-play').onclick=()=>{stopTimer();state.timer=setInterval(tick,400)};
    $('practice67-pause').onclick=()=>{stopTimer();post({action:'pause',id:state.id}).then(apply).catch(error=>{$('practice67-status').textContent=error.message})};
    $('practice67-restart').onclick=()=>{stopTimer();post({action:'restart',id:state.id}).then(apply).catch(error=>{$('practice67-status').textContent=error.message})};
    $('practice67-end').onclick=()=>{stopTimer();post({action:'end',id:state.id}).then(apply).catch(error=>{$('practice67-status').textContent=error.message})};
    $('practice67-save').onclick=()=>post({action:'decide',id:state.id,expectation:$('practice67-expect').value,evidence:$('practice67-evidence').value,changeMind:$('practice67-mind').value,reviewAt:state.end}).then(packet=>{apply(packet);$('practice67-status').textContent='Decision saved with the replay clock and the evidence that was visible. The review point is the end of this session.'}).catch(error=>{$('practice67-status').textContent=error.message});
    panel.addEventListener('click',event=>{const button=event.target.closest('[data-practice-review]');if(button)review(button.dataset.practiceReview).catch(error=>{$('practice67-status').textContent=error.message})});
    $('practice67-reflect').onclick=()=>post({action:'reflect',decisionId:state.decision,assessment:$('practice67-assessment').value,learned:$('practice67-learned').value}).then(apply).catch(error=>{$('practice67-status').textContent=error.message});
    $('practice67-journal').onclick=()=>post({action:'journal',decisionId:state.decision}).then(entry=>{
      const list=JSON.parse(localStorage.getItem('md-reborn-journal')||'[]');
      const next=[entry,...list.filter(item=>item.id!==entry.id)].slice(0,200);
      if(typeof saveJSON==='function')saveJSON('md-reborn-journal',next);
      else localStorage.setItem('md-reborn-journal',JSON.stringify(next));
      $('practice67-status').textContent='The original decision was added to the journal. The later reflection stays separate.';
    }).catch(error=>{$('practice67-status').textContent=error.message});
    $('practice67-pack').onclick=()=>post({action:'journal',decisionId:state.decision}).then(entry=>fetch('/api/v3/pack59',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'save',symbol:entry.symbol,wording:entry.expectation+' '+entry.reasons})})).then(response=>response.json()).then(pack=>{$('practice67-status').textContent=pack.id?'Research pack '+pack.id+' includes this practice note.':'The pack was not saved.'}).catch(error=>{$('practice67-status').textContent=error.message});
  }
  function onSymbol(next){
    if(!state.id)return;
    if(next!==state.symbol){stopTimer();if(window.Replay43?.active)Replay43.stop();const status=$('practice67-status');if(status)status.textContent='Practice is paused on '+state.symbol+'. This chart was not given those prices.';}
    else post({action:'pause',id:state.id}).then(packet=>{if(typeof changeView==='function')changeView('home');apply(packet)}).catch(()=>{});
  }
  document.addEventListener('DOMContentLoaded',mount);
  return {get id(){return state.id},get active(){return Boolean(state.id)},onSymbol};
})();
