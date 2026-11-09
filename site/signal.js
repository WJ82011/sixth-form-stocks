/* Signal Edition: interface-only enhancements. No API or market data substitution. */
(function(){
  'use strict';
  const overlay=document.getElementById('command-overlay');
  const input=document.getElementById('command-input');
  const list=document.getElementById('command-options');
  const launcher=document.getElementById('command-launch');
  const close=document.getElementById('command-close');
  const session=document.getElementById('desk-session-label');
  const nav=Array.from(document.querySelectorAll('.nav-btn[data-view]'));
  const entries=nav.map(b=>({view:b.dataset.view,label:b.dataset.navLabel||b.textContent.trim().replace(/\s+/g,' ')}));
  let focusIndex=0,lastFocus=null;
  function matching(){const q=input.value.trim().toLowerCase();return entries.filter(x=>!q||x.label.toLowerCase().includes(q)||x.view.includes(q));}
  function draw(){
    const options=matching();focusIndex=Math.min(Math.max(focusIndex,0),Math.max(0,options.length-1));
    list.replaceChildren();
    if(!options.length){let empty=document.createElement('div');empty.className='command-option';empty.textContent='No matching workspace';list.append(empty);return}
    options.forEach((v,i)=>{
      const button=document.createElement('button');button.type='button';button.className='command-option'+(i===focusIndex?' active':'');
      button.setAttribute('data-view',v.view);
      const label=document.createElement('strong');label.textContent=v.label;
      const path=document.createElement('span');path.textContent='OPEN  ↗';
      button.append(label,path);
      button.addEventListener('mouseenter',()=>{focusIndex=i;list.querySelectorAll('button').forEach((node,j)=>node.classList.toggle('active',i===j));});
      button.addEventListener('click',()=>visit(v.view));
      list.append(button);
    });
  }
  function open(){if(!overlay.classList.contains('hidden'))return;lastFocus=document.activeElement;overlay.classList.remove('hidden');input.value='';focusIndex=0;draw();input.focus();}
  function dismiss(){overlay.classList.add('hidden');if(lastFocus?.focus)lastFocus.focus();}
  function visit(view){dismiss();const b=nav.find(v=>v.dataset.view===view);if(b)b.click();}
  launcher.addEventListener('click',open);close.addEventListener('click',dismiss);
  overlay.addEventListener('click',e=>{if(e.target===overlay)dismiss()});
  input.addEventListener('input',()=>{focusIndex=0;draw()});
  document.addEventListener('keydown',e=>{
    const command=(e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k';
    if(command){e.preventDefault();overlay.classList.contains('hidden')?open():dismiss();return}
    if(overlay.classList.contains('hidden'))return;
    if(e.key==='Escape'){e.preventDefault();dismiss();return}
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const count=matching().length;if(!count)return;focusIndex=(focusIndex+(e.key==='ArrowDown'?1:-1)+count)%count;draw();return}
    if(e.key==='Enter'){e.preventDefault();const item=matching()[focusIndex];if(item)visit(item.view);}
    if(e.key==='Tab'){e.preventDefault();input.focus();}
  });
  function updateSession(){
    if(!session)return;
    // Session classification from the existing, more complete US market-hours helper.
    // Do not infer a live data connection from this schedule.
    try{
      if(typeof window.marketSessionFor==='function'){
        const x=window.marketSessionFor('AAPL');
        const text=String(x?.label||x?.status||'SCHEDULE UNKNOWN').toUpperCase();
        session.textContent='US SESSION / '+text.slice(0,36);
      }else{
        session.textContent='US SESSION / SEE LIVE TAPE';
      }
    }catch(_){session.textContent='US SESSION / SEE LIVE TAPE'}
  }
  updateSession();setInterval(updateSession,60000);
})();
