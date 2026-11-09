/* Compact, accessible navigation with interruptible disclosure motion. */
(()=>{
 'use strict';
 function setup(){
  const sidebar=document.getElementById('sidebar');if(!sidebar)return;
  const groups=Array.from(sidebar.querySelectorAll('.sidebar-group'));
  const buttons=Array.from(sidebar.querySelectorAll('.nav-btn[data-view]'));
  const media=typeof window!=='undefined'&&window.matchMedia?window.matchMedia('(prefers-reduced-motion: reduce)'):null;
  const running=new Map();let previousView=null;
  function motion(){return document.body?.dataset.motion!=='off'&&!media?.matches;}
  function setOpen(group,want,instant=false){
   const previous=running.get(group);
   if(previous&&previous.want===want&&!instant)return;
   if(!previous&&group.open===want)return;
   const start=group.getBoundingClientRect?.().height||0;
   if(previous){previous.animation.onfinish=null;previous.animation.oncancel=null;previous.animation.cancel();running.delete(group);}
   const summary=group.querySelector('summary'),content=group.querySelector('.sidebar-submenu');
   if(content)content.inert=!want;
   if(instant||!motion()||!group.animate||!start){group.open=want;group.style?.removeProperty('overflow');return;}
   group.open=true;
   const end=want?group.getBoundingClientRect().height:summary.getBoundingClientRect().height;
   group.style.overflow='hidden';
   const animation=group.animate([{height:start+'px'},{height:end+'px'}],{duration:220,easing:'cubic-bezier(.22,.75,.2,1)',fill:'both'});
   const state={want,animation};running.set(group,state);
   animation.onfinish=()=>{if(running.get(group)!==state)return;group.open=want;animation.onfinish=null;animation.oncancel=null;animation.cancel();group.style.removeProperty('overflow');running.delete(group);};
   animation.oncancel=()=>{if(running.get(group)!==state)return;group.open=want;group.style.removeProperty('overflow');running.delete(group);};
  }
  function closeOthers(group){for(const other of groups)if(other!==group)setOpen(other,false);}
  function sync(){
   const active=buttons.find(b=>b.classList.contains('active'));
   const view=active?.dataset.view||'',parent=active?.closest('.sidebar-group')||null;
   for(const button of buttons){if(button===active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}
   for(const group of groups)group.classList.toggle('is-current',group===parent);
   if(view!==previousView){for(const group of groups)setOpen(group,group===parent,previousView===null);previousView=view;}
  }
  for(const group of groups){
   const summary=group.querySelector('summary');
   summary.addEventListener('click',event=>{if(event.button>0||event.metaKey||event.ctrlKey||event.altKey)return;event.preventDefault();const want=!(running.get(group)?.want??group.open);if(want)closeOthers(group);setOpen(group,want);});
   group.addEventListener('toggle',()=>{if(group.open&&running.get(group)?.want!==false){const content=group.querySelector('.sidebar-submenu');if(content)content.inert=false;closeOthers(group);}});
   group.addEventListener('keydown',event=>{if(event.key==='Escape'&&(group.open||running.has(group))){event.preventDefault();summary.focus();setOpen(group,false);}});
  }
  const selectedObserver=new MutationObserver(sync);
  for(const button of buttons)selectedObserver.observe(button,{attributes:true,attributeFilter:['class']});
  const source=document.getElementById('alerts-nav-count'),badge=document.getElementById('nav-workspace-alerts');
  function syncAlerts(){if(!source||!badge)return;const n=Number(source.textContent),count=Number.isFinite(n)&&n>0?Math.floor(n):0;badge.textContent=String(count);badge.hidden=count===0;badge.setAttribute('aria-label',count+' triggered price alerts');}
  if(source)new MutationObserver(syncAlerts).observe(source,{childList:true,characterData:true,subtree:true});
  function settle(){if(!motion())for(const [group,state] of [...running])setOpen(group,state.want,true);}
  if(document.body)new MutationObserver(settle).observe(document.body,{attributes:true,attributeFilter:['data-motion']});
  media?.addEventListener?.('change',settle);
  sync();syncAlerts();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
})();
