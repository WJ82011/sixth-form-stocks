/* Four linked charts, a stepped investigation, model notes and data inspection. */
(function(){
  const state={board:null,fraction:null,jobId:'',inspectId:''};
  function post(body){
    return fetch('/api/v3/desk61',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(r=>r.json());
  }
  function text(data){
    return data.error || data.notice || data.detail || data.summary || data.answer || '';
  }
  function paint(canvas, panel){
    const ctx=canvas.getContext('2d');
    const width=canvas.width, height=canvas.height;
    ctx.clearRect(0,0,width,height);
    const points=panel.points||[];
    let min=Infinity, max=-Infinity, count=0;
    points.forEach(item=>{if(item.plot!=null){count++;min=Math.min(min,item.plot);max=Math.max(max,item.plot);}});
    if(!count){
      ctx.fillStyle='#9fb0c8';ctx.fillText('No saved closes in this range',16,28);return;
    }
    const span=max-min||1;
    const bucket=Math.max(1,Math.ceil(points.length/Math.max(1,width-24)));
    ctx.beginPath();ctx.strokeStyle='#4c8dff';ctx.lineWidth=2;
    let drawing=false;
    for(let index=0;index<points.length;index+=bucket){
      const slice=points.slice(index,index+bucket);
      const item=slice.find(row=>row.plot!=null);
      if(!item){drawing=false;continue;}
      const x=12+(index/(points.length-1||1))*(width-24);
      const y=height-16-((item.plot-min)/span)*(height-32);
      if(!drawing){ctx.moveTo(x,y);drawing=true;}else ctx.lineTo(x,y);
    }
    ctx.stroke();
    (panel.events||[]).forEach(row=>{
      const index=points.findIndex(item=>item.date && item.date===row.date);
      if(index<0)return;
      const x=12+(index/(points.length-1||1))*(width-24);
      ctx.fillStyle='#f5c16c';ctx.fillRect(x,14,3,8);
    });
    (panel.annotations||[]).forEach(row=>{
      if(row.price==null)return;
      const y=height-16-(((panel.mode==='percent'?100:row.price)-min)/span)*(height-32);
      ctx.strokeStyle='#8ec5ff';ctx.strokeRect(12,y,width-24,1);
    });
    if(state.fraction!=null){
      const x=12+state.fraction*(width-24);
      ctx.strokeStyle='rgba(255,255,255,.7)';ctx.beginPath();ctx.moveTo(x,8);ctx.lineTo(x,height-8);ctx.stroke();
      const index=Math.round(state.fraction*(points.length-1));
      const item=points[Math.max(0,Math.min(points.length-1,index))]||{};
      ctx.fillStyle='#fff';ctx.fillText((item.date||'gap')+' '+(item.plot==null?'missing':item.plot.toFixed(2)),16,16);
    }
    if(points.length>width)ctx.fillText(points.length+' closes stored',16,height-6);
  }
  function draw(){
    if(!state.board)return;
    document.querySelectorAll('[data-desk61-chart]').forEach(canvas=>{
      const panel=state.board.panels[Number(canvas.dataset.desk61Chart)];
      if(panel)paint(canvas,panel);
    });
  }
  function boardBody(){
    const symbols=['a','b','c','d'].map(key=>document.getElementById('desk61-'+key).value.trim()).filter(Boolean);
    return {symbols,start:document.getElementById('desk61-start').value,end:document.getElementById('desk61-end').value,
      shared:document.getElementById('desk61-shared').checked,mode:document.getElementById('desk61-mode').value};
  }
  function showBoard(data){
    state.board=data.panels?data:null;
    const host=document.getElementById('desk61-charts');
    host.innerHTML='';
    (data.panels||[]).forEach((panel,index)=>{
      const card=document.createElement('div');
      const title=document.createElement('p');
      title.className='desk61-note';
      title.textContent=panel.symbol+' · '+(data.mode==='percent'?'percentage from the first close':'saved price')+' · '+(panel.missing||[]).length+' missing · '+(panel.events||[]).length+' dated events';
      const canvas=document.createElement('canvas');
      canvas.width=640;canvas.height=180;canvas.dataset.desk61Chart=String(index);
      canvas.addEventListener('mousemove',event=>{
        const rect=canvas.getBoundingClientRect();
        state.fraction=Math.min(1,Math.max(0,(event.clientX-rect.left)/rect.width));
        draw();
      });
      canvas.addEventListener('mouseleave',()=>{state.fraction=null;draw();});
      card.append(title,canvas);host.append(card);
    });
    document.getElementById('desk61-board-status').textContent=data.error||data.notice||((data.panels||[]).length+' charts. Each company keeps its own closes.');
    draw();
  }
  function stepList(job){
    const host=document.getElementById('desk61-steps');
    host.innerHTML='';
    (job.steps||[]).forEach(step=>{
      const row=document.createElement('div');
      row.className='desk61-step';
      const refs=(step.refs||step.references||[]).map(ref=>ref.kind+' '+ref.id+' published '+(ref.publishedAt||'—')+' retrieved '+(ref.retrievedAt||'—')+' period '+(ref.periodStart||'—')).join(' · ');
      row.textContent=(step.status||'pending')+' · '+step.title+(step.detail?': '+step.detail:'')+(refs?' · '+refs:'');
      host.append(row);
    });
  }
  function mount(){
    if(document.getElementById('desk61-board')||!document.getElementById('view-comparison'))return;
    const board=document.createElement('section');
    board.className='surface desk61';board.id='desk61-board';
    board.innerHTML='<h2>Linked charts</h2><p>Up to four companies. A shared range uses the same New York sessions and leaves gaps empty.</p><div class="desk61-row"><label>One<input id="desk61-a" value="TTWO"></label><label>Two<input id="desk61-b" value="AAPL"></label><label>Three<input id="desk61-c"></label><label>Four<input id="desk61-d"></label><label>From<input id="desk61-start" type="date"></label><label>To<input id="desk61-end" type="date"></label><label>View<select id="desk61-mode"><option value="price">Price</option><option value="percent">Percentage</option></select></label><label>Shared<input id="desk61-shared" type="checkbox"></label><button type="button" class="primary-btn" id="desk61-draw">Show saved closes</button><button type="button" class="ghost-btn" id="desk61-save">Save board</button><button type="button" class="ghost-btn" id="desk61-open">Reopen saved</button></div><p id="desk61-board-status" class="desk61-note" role="status"></p><div id="desk61-charts" class="desk61-charts"></div>';
    document.getElementById('view-comparison').insertBefore(board, document.getElementById('view-comparison').firstChild);
    document.getElementById('desk61-draw').onclick=async()=>showBoard(await post({action:'board',...boardBody()}));
    document.getElementById('desk61-save').onclick=async()=>{
      const data=await post({action:'board-save',...boardBody()});
      if(data.id)sessionStorage.setItem('md-board61',data.id);
      showBoard(data);
    };
    document.getElementById('desk61-open').onclick=async()=>{
      const ident=sessionStorage.getItem('md-board61');
      if(!ident){document.getElementById('desk61-board-status').textContent='Save a board first.';return;}
      const data=await fetch('/api/v3/desk61?part=board&id='+encodeURIComponent(ident)).then(r=>r.json());
      showBoard(data);
    };
    const ask=document.getElementById('mdi-answer');
    if(ask){
      const panel=document.createElement('section');
      panel.className='surface desk61';panel.id='desk61-ask';
      panel.innerHTML='<h2>Investigate a week</h2><p>The steps appear before any return is calculated.</p><div class="desk61-row"><label>Question<input id="desk61-question" value="Investigate TTWO\'s latest completed weekly move."></label><button type="button" class="ghost-btn" id="desk61-plan">Show steps</button><button type="button" class="primary-btn" id="desk61-next">Run next step</button><button type="button" class="ghost-btn" id="desk61-cancel">Cancel</button><button type="button" class="ghost-btn" id="desk61-resume">Resume</button><button type="button" class="ghost-btn" id="desk61-trace">Trace evidence</button></div><p id="desk61-ask-status" class="desk61-note" role="status"></p><div id="desk61-steps" class="desk61-steps"></div>';
      ask.parentNode.insertBefore(panel, ask);
      document.getElementById('desk61-plan').onclick=async()=>{
        const data=await post({action:'propose',question:document.getElementById('desk61-question').value});
        state.jobId='';stepList(data);document.getElementById('desk61-ask-status').textContent=text(data);
      };
      document.getElementById('desk61-next').onclick=async()=>{
        const data=state.jobId?await post({action:'step',id:state.jobId}):await post({action:'start',question:document.getElementById('desk61-question').value});
        if(data.id){state.jobId=data.id;try{sessionStorage.setItem('md-desk61',data.id);}catch(error){}}
        stepList(data);document.getElementById('desk61-ask-status').textContent=text(data)||data.status||'';
      };
      document.getElementById('desk61-cancel').onclick=async()=>{
        if(!state.jobId)return;
        const data=await post({action:'cancel',id:state.jobId});
        document.getElementById('desk61-ask-status').textContent=text(data);
      };
      document.getElementById('desk61-resume').onclick=async()=>{
        if(!state.jobId)return;
        const data=await post({action:'resume',id:state.jobId});
        document.getElementById('desk61-ask-status').textContent=text(data);
      };
      document.getElementById('desk61-trace').onclick=async()=>{
        if(!state.jobId)return;
        const data=await fetch('/api/v3/desk61?part=trace&id='+encodeURIComponent(state.jobId)).then(r=>r.json());
        stepList(data);document.getElementById('desk61-ask-status').textContent='Each completed step lists its references.';
      };
    }
    const learning=document.getElementById('view-learning');
    if(learning){
      const panel=document.createElement('section');
      panel.className='surface desk61';
      panel.innerHTML='<h2>Model record</h2><p>Candidates stay saved, including ones that do not beat an unchanged price.</p><div class="desk61-row"><label>Company<input id="desk61-model-symbol" value="TTWO"></label><button type="button" class="primary-btn" id="desk61-evaluate">Score saved closes</button></div><p id="desk61-model-status" class="desk61-note" role="status"></p>';
      learning.insertBefore(panel, learning.firstChild);
      document.getElementById('desk61-evaluate').onclick=async()=>{
        const data=await post({action:'evaluate',symbol:document.getElementById('desk61-model-symbol').value});
        document.getElementById('desk61-model-status').textContent=(data.note||data.error||'')+' Active method: '+(data.activeMethod||'baseline')+'.';
      };
    }
    const settings=document.getElementById('view-settings');
    if(settings){
      const panel=document.createElement('section');
      panel.className='surface desk61';
      panel.innerHTML='<h2>Saved price check</h2><p>Inspection changes nothing. Repair only collapses duplicate Massive bars and can be undone. Imported history is left as you saved it.</p><div class="desk61-row"><label>Company<input id="desk61-health-symbol" value="TTWO"></label><button type="button" class="ghost-btn" id="desk61-inspect">Inspect</button><button type="button" class="primary-btn" id="desk61-repair">Repair duplicates</button><button type="button" class="ghost-btn" id="desk61-undo">Undo repair</button></div><p id="desk61-health-status" class="desk61-note" role="status"></p>';
      settings.insertBefore(panel, settings.firstChild);
      document.getElementById('desk61-inspect').onclick=async()=>{
        const data=await post({action:'inspect',symbol:document.getElementById('desk61-health-symbol').value});
        state.inspectId=data.id||'';
        const counts={};
        (data.problems||[]).forEach(item=>{counts[item.kind]=(counts[item.kind]||0)+1;});
        document.getElementById('desk61-health-status').textContent=data.error||data.notice+' '+Object.entries(counts).map(([kind,count])=>kind+' '+count).join(', ');
      };
      document.getElementById('desk61-repair').onclick=async()=>{
        const data=await post({action:'repair',symbol:document.getElementById('desk61-health-symbol').value,inspectId:state.inspectId});
        document.getElementById('desk61-health-status').textContent=text(data);
      };
      document.getElementById('desk61-undo').onclick=async()=>{
        const data=await post({action:'undo-repair',symbol:document.getElementById('desk61-health-symbol').value});
        document.getElementById('desk61-health-status').textContent=text(data);
      };
    }
  }
  window.Desk61={mount};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
