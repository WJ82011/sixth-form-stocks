/* Annotations stay on the instrument, price and time. Drawing uses the chart scale. */
const Annotate60=(()=>{
  let items=[],symbol='',tool='',selected='',history=[],draft=null;
  function mount(){
    const tools=document.getElementById('look43-tools');
    if(!tools||document.getElementById('annotate60'))return;
    const bar=document.createElement('div');
    bar.id='annotate60';
    bar.innerHTML='<button type="button" data-annotate="level">Level</button><button type="button" data-annotate="trend">Trend</button><button type="button" data-annotate="note">Note</button><button type="button" data-annotate="measure">Measure</button><button type="button" id="annotate60-undo">Undo</button><button type="button" id="annotate60-remove">Remove</button><input id="annotate60-text" aria-label="Annotation note" placeholder="Note" maxlength="180"><span id="annotate60-status" role="status"></span>';
    tools.append(bar);
    bar.addEventListener('click',event=>{
      const button=event.target.closest('[data-annotate]');
      if(button){tool=button.dataset.annotate;draft=null;const layer=document.getElementById('annotate60-layer');if(layer)layer.style.pointerEvents='auto';status('Click the chart.');return;}
      if(event.target.id==='annotate60-undo')undo();
      if(event.target.id==='annotate60-remove')removeSelected();
    });
    const wrap=document.querySelector('#home43 .chart-wrap')||document.querySelector('.chart-wrap');
    if(wrap&&!document.getElementById('annotate60-layer')){
      const layer=document.createElement('div');
      layer.id='annotate60-layer';
      wrap.append(layer);
      layer.addEventListener('pointerdown',place);
      wrap.addEventListener('keydown',key);
    }
    load();
  }
  function status(text){const node=document.getElementById('annotate60-status');if(node)node.textContent=text||'';}
  async function load(){
    const wanted=typeof E!=='undefined'?E.selected:'';
    if(!wanted)return;
    const data=await fetch('/api/v3/annotate60?symbol='+encodeURIComponent(wanted)).then(r=>r.json());
    if(wanted!==E.selected)return;
    symbol=wanted;items=data.items||[];
    if(typeof drawChart==='function')drawChart();
  }
  function nearest(event){
    const canvas=document.getElementById('overview-chart');
    const points=(E.chartPoints||[]).filter(point=>Number.isFinite(point.t)&&Number.isFinite(point.p));
    if(!canvas||points.length<1)return null;
    const box=canvas.getBoundingClientRect();
    const ratio=Math.max(0,Math.min(1,(event.clientX-box.left)/Math.max(1,box.width)));
    const index=Math.round(ratio*(points.length-1));
    return points[Math.max(0,Math.min(points.length-1,index))];
  }
  async function place(event){
    if(!tool)return;
    const point=nearest(event);
    if(!point){status('No recorded point there.');return;}
    let next=null;
    if(tool==='level')next={kind:'level',price:point.p,label:'Price level'};
    if(tool==='note'){const text=document.getElementById('annotate60-text').value.trim();if(!text){status('Write the note first.');return;}next={kind:'note',t:point.t,price:point.p,text};}
    if(tool==='trend'||tool==='measure'){
      if(!draft){draft=point;status('Click the second recorded point.');return;}
      next={kind:tool,t1:draft.t,p1:draft.p,t2:point.t,p2:point.p};
      draft=null;
    }
    if(!next)return;
    history=items.slice();
    await send([].concat(items,[next]));
    tool='';
    const layer=document.getElementById('annotate60-layer');if(layer)layer.style.pointerEvents='none';
  }
  async function send(list){
    const wanted=E.selected;
    const response=await fetch('/api/v3/annotate60',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'replace',symbol:wanted,items:list})});
    const data=await response.json();
    if(wanted!==E.selected)return;
    if(!response.ok||data.error){status(data.error||'The annotation was not saved.');return;}
    items=data.items||[];symbol=wanted;status((data.items||[]).filter(item=>item.kind==='measure').slice(-1).map(item=>item.label).join(''));
    if(typeof drawChart==='function')drawChart();
  }
  async function undo(){
    const wanted=E.selected;
    const response=await fetch('/api/v3/annotate60',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'undo',symbol:wanted})});
    const data=await response.json();
    if(wanted!==E.selected)return;
    status(data.error||data.notice||'');
    if(data.items){items=data.items;if(typeof drawChart==='function')drawChart();}
  }
  async function removeSelected(){
    if(!selected){status('Select an annotation on the chart first.');return;}
    const wanted=E.selected;
    const response=await fetch('/api/v3/annotate60',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'remove',symbol:wanted,id:selected})});
    const data=await response.json();
    if(wanted!==E.selected)return;
    if(data.items){items=data.items;selected='';if(typeof drawChart==='function')drawChart();}
    status(data.error||'Removed.');
  }
  function key(event){
    if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='z'){event.preventDefault();undo();}
    else if(event.key==='Delete'||event.key==='Backspace'){event.preventDefault();removeSelected();}
    else if(event.key==='Escape'){tool='';draft=null;status('');}
  }
  function paint(ctx,X,Y){
    if(symbol!==E.selected){load();return;}
    ctx.save();
    items.forEach(item=>{
      ctx.strokeStyle=item.id===selected?'#f2c14e':'#7eb6ff';
      ctx.fillStyle='#d5e2f2';
      ctx.lineWidth=item.id===selected?2:1.25;
      ctx.font='12px -apple-system,sans-serif';
      if(item.kind==='level'){
        const y=Y(item.price);
        ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(ctx.canvas.width,y);ctx.stroke();
        ctx.fillText(item.label+' '+item.price,8,y-4);
      }else if(item.kind==='note'){
        ctx.beginPath();ctx.arc(X(item.t),Y(item.price),4,0,Math.PI*2);ctx.fill();
        ctx.fillText(item.text,X(item.t)+8,Y(item.price)-6);
      }else{
        ctx.beginPath();ctx.moveTo(X(item.t1),Y(item.p1));ctx.lineTo(X(item.t2),Y(item.p2));ctx.stroke();
        if(item.label)ctx.fillText(item.label,X(item.t2)+6,Y(item.p2));
      }
    });
    ctx.restore();
  }
  function hit(x,y,X,Y){
    let best='',score=18;
    items.forEach(item=>{
      const px=item.kind==='level'?x:X(item.t||item.t2), py=item.kind==='level'?Y(item.price):Y(item.price||item.p2);
      const distance=Math.hypot(px-x,py-y);
      if(distance<score){score=distance;best=item.id;}
    });
    selected=best;
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(mount,0));
  const previous=window.setSelected;
  if(typeof previous==='function')window.setSelected=function(sym){const result=previous.apply(this,arguments);load();return result;};
  return window.Annotate60={paint,mount,hit,load};
})();
