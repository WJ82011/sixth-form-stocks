/* Chart inspection: crosshair, pan, zoom, pin, reset and back to live.
   The view stays put when newer prices arrive unless Back to live is on. */
const Chart43=window.Chart43=(()=>{
  const state={live:true,from:null,to:null,pinned:null,drag:null,review:false};
  const reduced=()=>document.body?.dataset?.motion==='off'||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  function source(){
    if(window.Replay43?.active)return Replay43.prices();
    return (E.chartPoints||[]).filter(point=>Number.isFinite(point.t)&&Number.isFinite(point.p));
  }
  function span(){
    const points=source();
    if(points.length<2)return null;
    return {from:state.from??points[0].t,to:state.to??points.at(-1).t,points};
  }
  function lens(points){
    const clean=points.filter(point=>Number.isFinite(point.t)&&Number.isFinite(point.p));
    if(window.Replay43?.active){
      if(!clean.length)return {points:clean,from:Replay43.cursor,to:Replay43.cursor};
      return {points:clean,from:clean[0].t,to:Math.max(clean.at(-1).t,Replay43.cursor)};
    }
    if(state.live||state.from==null||state.to==null)return null;
    const shown=clean.filter(point=>point.t>=state.from&&point.t<=state.to);
    return {points:shown.length?shown:clean.slice(0,1),from:state.from,to:state.to};
  }
  function draw(){if(typeof drawChart==='function')drawChart()}
  function setWindow(from,to){
    const points=source();
    if(points.length<2)return;
    const first=points[0].t,last=points.at(-1).t,width=Math.max(last-first,1);
    const minSpan=Math.max(60_000,width/80);
    let start=from,end=to;
    if(end-start<minSpan){const mid=(start+end)/2;start=mid-minSpan/2;end=mid+minSpan/2}
    if(start<first){end+=first-start;start=first}
    if(end>last){start-=end-last;end=last}
    state.from=Math.max(first,start);state.to=Math.min(last,end);state.live=false;sync();draw();
  }
  function zoom(factor,anchor){
    const box=span();if(!box)return;
    const next=(box.to-box.from)*factor;
    const ratio=Math.max(0,Math.min(1,(anchor-box.from)/Math.max(1,box.to-box.from)));
    setWindow(anchor-next*ratio,anchor-next*ratio+next);
  }
  function pan(delta){const box=span();if(!box)return;setWindow(box.from+delta,box.to+delta)}
  function reset(){const points=source();if(!points.length)return;state.live=false;state.from=points[0].t;state.to=points.at(-1).t;sync();draw()}
  function fits(points){
    if(state.live||state.from==null||state.to==null)return true;
    return (points||[]).filter(point=>Number.isFinite(point.t)&&point.t>=state.from&&point.t<=state.to).length>=2;
  }
  function backToLive(){state.live=true;state.from=null;state.to=null;state.pinned=null;if(window.Replay43?.active)Replay43.stop();else{sync();draw()}}
  function pinAt(x){
    const canvas=document.getElementById('overview-chart');if(!canvas)return;
    const box=canvas.getBoundingClientRect();
    state.pinned={x:x??(box.width/2),at:Date.now()};
    state.review=true;
    draw();
  }
  function sync(){
    const note=document.getElementById('chart43-status');
    const back=document.getElementById('chart43-live');
    if(note)note.textContent=window.Replay43?.active?'Replay is showing only prices reached so far.':state.live?'Following the latest saved price.':'Inspecting older prices. The view stays here as new prices arrive.';
    if(back)back.hidden=state.live&&!window.Replay43?.active;
  }
  function toolbar(){
    const ranges=document.getElementById('overview-ranges');if(!ranges||document.getElementById('chart43-tools'))return;
    const bar=document.createElement('div');
    bar.id='chart43-tools';bar.className='chart43-tools';
    bar.innerHTML='<button type="button" id="chart43-reset">Reset view</button><button type="button" id="chart43-live" hidden>Back to live</button><button type="button" id="chart43-pin">Pin point</button><span id="chart43-status" role="status">Following the latest saved price.</span>';
    ranges.after(bar);
    bar.querySelector('#chart43-reset').onclick=reset;
    bar.querySelector('#chart43-live').onclick=backToLive;
    bar.querySelector('#chart43-pin').onclick=()=>pinAt();
    const canvas=document.getElementById('overview-chart');
    canvas.tabIndex=0;
    canvas.setAttribute('aria-keyshortcuts','ArrowLeft ArrowRight + - Home Escape');
    canvas.addEventListener('wheel',event=>{
      if(!source().length)return;
      event.preventDefault();
      const box=span();if(!box)return;
      const ratio=Math.max(0,Math.min(1,(event.clientX-canvas.getBoundingClientRect().left)/canvas.getBoundingClientRect().width));
      zoom(event.deltaY>0?1.18:0.84,box.from+(box.to-box.from)*ratio);
    },{passive:false});
    canvas.addEventListener('pointerdown',event=>{
      if(event.button!==0)return;
      canvas.setPointerCapture(event.pointerId);
      const box=span();
      state.drag=box?{x:event.clientX,from:box.from,to:box.to,moved:false}:null;
    });
    canvas.addEventListener('pointermove',event=>{
      if(!state.drag)return;
      const width=canvas.getBoundingClientRect().width||1;
      const delta=(state.drag.x-event.clientX)/width*(state.drag.to-state.drag.from);
      if(Math.abs(event.clientX-state.drag.x)>3)state.drag.moved=true;
      setWindow(state.drag.from+delta,state.drag.to+delta);
    });
    canvas.addEventListener('pointerup',event=>{
      if(state.drag&&!state.drag.moved)pinAt(event.clientX-canvas.getBoundingClientRect().left);
      state.drag=null;
    });
    canvas.addEventListener('keydown',event=>{
      const box=span();if(!box)return;
      const step=(box.to-box.from)*0.12;
      if(event.key==='ArrowLeft'){event.preventDefault();pan(-step)}
      else if(event.key==='ArrowRight'){event.preventDefault();pan(step)}
      else if(event.key==='+'||event.key==='='){event.preventDefault();zoom(0.8,(box.from+box.to)/2)}
      else if(event.key==='-'||event.key==='_'){event.preventDefault();zoom(1.25,(box.from+box.to)/2)}
      else if(event.key==='Home'){event.preventDefault();backToLive()}
      else if(event.key==='Escape'){state.pinned=null;draw()}
      else if(event.key==='0'){event.preventDefault();reset()}
    });
  }
  function paint(ctx,X,Y,points){
    if(window.Annotate60)Annotate60.paint(ctx,X,Y,points);
    const marks=window.Strategy54&&Strategy54.markers||[];
    if(marks.length&&points.length){
      ctx.save();
      marks.forEach(mark=>{
        const point=points.find(item=>item.t===mark.t);if(!point)return;
        ctx.fillStyle=mark.kind==='buy'?'#2f6fed':'#c4493a';
        ctx.beginPath();ctx.arc(X(point.t),Y(point.p),5,0,Math.PI*2);ctx.fill();
      });
      ctx.restore();
    }
    if(!state.pinned||!points.length){if(!points.length)state.review=false;return}
    const nearest=points.reduce((best,point)=>Math.abs(X(point.t)-state.pinned.x)<Math.abs(X(best.t)-state.pinned.x)?point:best,points[0]);
    ctx.save();
    ctx.fillStyle='#f2c14e';ctx.beginPath();ctx.arc(X(nearest.t),Y(nearest.p),5,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#f2c14e';ctx.font='11px -apple-system, sans-serif';ctx.textAlign='left';
    ctx.fillText('Pinned '+new Date(nearest.t).toLocaleString('en-GB'),X(nearest.t)+8,Y(nearest.p)-8);
    ctx.restore();
    if(state.review){state.review=false;window.Move44?.fromPoint(nearest)}
  }
  document.addEventListener('DOMContentLoaded',toolbar);
  return {lens,paint,reset,backToLive,setWindow,sync,fits,window:span,get live(){return state.live},reduced};
})();
