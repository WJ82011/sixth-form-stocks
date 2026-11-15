/* Saved workspaces. Switching reads the saved copy and leaves unsaved wording on screen. */
const Workspace60=(()=>{
  let seq=0, current=null;
  function dirty(){
    const wording=document.getElementById('pack59-wording');
    const note=document.getElementById('note-thesis');
    return (wording&&wording.value&&wording.dataset.saved!==wording.value)||(note&&note.value&&note.dataset.saved!==note.value);
  }
  function mount(){
    const top=document.querySelector('.look43-top-actions');
    const board=document.getElementById('look43-board');
    if(!top||document.getElementById('workspace60'))return;
    const box=document.createElement('label');
    box.id='workspace60';
    box.innerHTML='Workspace <select id="workspace60-pick" aria-label="Saved workspace"></select>';
    top.prepend(box);
    box.querySelector('select').addEventListener('change',event=>apply(event.target.value));
    if(board&&!document.getElementById('workspace60-resize')){
      const handle=document.createElement('button');
      handle.id='workspace60-resize';handle.type='button';handle.textContent='Resize panels';
      handle.addEventListener('pointerdown',startResize);
      const reset=document.createElement('button');
      reset.id='workspace60-reset';reset.type='button';reset.textContent='Reset layout';
      reset.addEventListener('click',()=>saveLayout(null));
      board.before(handle, reset);
    }
    refresh();
  }
  async function refresh(){
    const id=++seq;
    const data=await fetch('/api/v3/workspace60').then(response=>response.json());
    if(id!==seq)return;
    const pick=document.getElementById('workspace60-pick');
    if(!pick)return;
    pick.innerHTML=['<option value="">Choose a workspace</option>'].concat((data.workspaces||[]).map(row=>`<option value="${row.id}">${row.name}</option>`)).join('');
    if(data.activeId)pick.value=data.activeId;
  }
  async function apply(ident){
    if(!ident)return;
    const keep=dirty();
    const id=++seq;
    const response=await fetch('/api/v3/workspace60',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'open',id:ident})});
    const data=await response.json();
    if(id!==seq)return;
    if(!response.ok||data.error){const feed=document.getElementById('look43-feed');if(feed)feed.textContent=data.error||'The workspace could not be opened.';return;}
    current=data;
    const symbol=(data.symbols||[]).find(item=>!item.includes('-'));
    if(symbol&&typeof setSelected==='function')setSelected(symbol);
    if(data.chartRange&&typeof setChartRange==='function')setChartRange(data.chartRange);
    if(!keep&&data.view&&typeof changeView==='function')changeView(data.view);
    if(data.layout&&data.layout.side)document.getElementById('look43-board').style.setProperty('--look43-side',data.layout.side+'px');
    if(data.links&&data.links.packId)sessionStorage.setItem('md-pack59',data.links.packId);
    const feed=document.getElementById('look43-feed');
    if(feed)feed.textContent=keep?'Unsaved wording stayed on screen. '+(data.since&&data.since.notice||''):(data.since&&data.since.notice)||data.notice||'';
  }
  function startResize(event){
    const board=document.getElementById('look43-board');
    const startX=event.clientX, start=board.getBoundingClientRect().width;
    const side=document.querySelector('.look43-side');
    const startSide=side?side.getBoundingClientRect().width:300;
    function move(next){
      const width=Math.max(220,Math.min(480,startSide-(next.clientX-startX)));
      board.style.setProperty('--look43-side',width+'px');
      board.dataset.side=String(Math.round(width));
    }
    function end(){
      window.removeEventListener('pointermove',move);
      window.removeEventListener('pointerup',end);
      saveLayout(Number(board.dataset.side||0));
    }
    window.addEventListener('pointermove',move);
    window.addEventListener('pointerup',end);
  }
  async function saveLayout(side){
    if(!current)return;
    const body={action:'save',id:current.id,name:current.name,symbols:current.symbols,comparisonSymbols:current.comparisonSymbols,chartRange:current.chartRange,view:current.view,useWatchlist:current.useWatchlist,links:current.links,layout:{side:side||null}};
    const data=await fetch('/api/v3/workspace60',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}).then(r=>r.json());
    if(data.error){const feed=document.getElementById('look43-feed');if(feed)feed.textContent=data.error;return;}
    current=data;
    if(!side)document.getElementById('look43-board').style.removeProperty('--look43-side');
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(mount,0));
  return window.Workspace60={mount,apply};
})();
