/* Optional demo, notebook notes and tester feedback. Nothing here is written to the price database. */
(function(){
  const DEMO={
    label:'DEMONSTRATION DATA · not a real company · not your saved records',
    company:'Demo Co', symbol:'DEMO',
    prices:[{date:'2026-01-05',price:100},{date:'2026-01-06',price:101},{date:'2026-01-07',price:100},{date:'2026-01-08',price:103},{date:'2026-01-09',price:102}],
    event:{title:'Demo Co published a sample notice', source:'Bundled example', published:'2026-01-08', retrieved:'2026-01-09'},
    compare:[{symbol:'DEMO',change:2},{symbol:'DEMO-B',change:-1}],
    forecast:{status:'withheld', notice:'On this sample the unchanged price was closer. No purple path is drawn.'},
    investigation:'Demo investigation · saved inside this walkthrough only. It is not in your journal.'
  };
  const ENTRIES=[
    {date:'2026-11-14', status:'completed', text:'The purple line is kept only when it beats an unchanged price on later dates. Those later dates are not used to fit the line. The band reports how many of those closes it covered. A failed result is saved and is not drawn.'},
    {date:'2026-11-14', status:'completed', text:'A saved scan card used to open the wrong page. It now opens the company chart and keeps the scanned dates.'},
    {date:'2026-11-14', status:'completed', text:'V2.7 checked full-screen layout at 1280 by 720 and a phone width of 390. That note records measurements, not an open defect. V2.4.1 grouped the sidebar into six entries.'},
    {date:'2026-11-15', status:'completed', text:'Public portfolio host: Overview chart, heatmap tiles and this guided walkthrough run from a labelled snapshot without API keys.'}
  ];
  const TASKS=[
    'Open Overview, then Take-Two, and say whether a purple forecast line is shown.',
    'Open Stock Browser, pick one company event, and name its source.',
    'Compare two companies for the same dates.',
    'Open Forecast Lab and read whether the learned path was withheld.',
    'Start the guided demo, then leave it. Your own companies should still be selected.'
  ];
  const DEMO_TASK_RESULTS=[
    null,
    null,
    null,
    'Withheld on bundled sample — unchanged price beat the learned path.',
    'Pass — five steps complete; workspace symbol unchanged after Leave demo.'
  ];
  const FIRST_RUN_KEY='md-guided-demo-seen';
  let startGuidedDemo=null;

  function notes(){try{return JSON.parse(localStorage.getItem('md-notebook-notes')||'[]');}catch(e){return [];}}
  function feedback(){try{return JSON.parse(localStorage.getItem('md-tester-feedback')||'[]');}catch(e){return [];}}
  function cloudDemo(){return typeof MarketDeskHost!=='undefined'&&MarketDeskHost.demoMode;}
  function markGuidedSeen(){
    try{localStorage.setItem(FIRST_RUN_KEY,'1');}catch(e){}
    document.getElementById('demo-first-run-cta')?.remove();
  }

  function mount(){
    if(document.getElementById('showcase61')||!document.getElementById('view-settings'))return;
    const intro=cloudDemo()
      ?'Sixth-form portfolio demo — DEMO DATA · sample figures only. Path: Overview → Heatmap → Stock Browser → Forecast Lab → this walkthrough. Your Mac workspace is unchanged.'
      :'The demo uses bundled sample figures. Your saved prices and notes stay where they are.';
    const panel=document.createElement('section');
    panel.className='surface desk61'; panel.id='showcase61';
    panel.innerHTML='<h2>Admissions walkthrough</h2><p id="showcase61-intro">'+intro+'</p><div class="desk61-row"><button type="button" class="primary-btn" id="showcase61-demo">Start guided demo</button><button type="button" class="ghost-btn" id="showcase61-exit">Leave demo</button></div><p class="showcase61-progress" id="showcase61-progress" hidden aria-hidden="true"><i id="showcase61-progress-bar" style="width:0%"></i></p><div id="showcase61-stage"></div><h2>Engineering notebook</h2><div id="showcase61-log"></div><label>Your explanation<textarea id="showcase61-own" rows="3" placeholder="Add what you want to say in your own words"></textarea></label><button type="button" class="ghost-btn" id="showcase61-add">Save my note</button><h2>Tester tasks</h2><ol id="showcase61-tasks"></ol><label>What a tester reported<textarea id="showcase61-feed" rows="3"></textarea></label><button type="button" class="ghost-btn" id="showcase61-save-feed">Save feedback</button><p id="showcase61-feed-list" class="desk61-note"></p>';
    document.getElementById('view-settings').insertBefore(panel, document.getElementById('view-settings').firstChild);
    const log=document.getElementById('showcase61-log');
    ENTRIES.concat(notes().map(item=>({date:item.date,status:'your note',text:item.text}))).forEach(item=>{
      const row=document.createElement('p'); row.className='desk61-note';
      row.textContent=item.date+' · '+item.status+' · '+item.text; log.append(row);
    });
    const list=document.getElementById('showcase61-tasks');
    const useDemoResults=cloudDemo();
    TASKS.forEach((task,i)=>{
      const item=document.createElement('li');
      const seeded=useDemoResults&&DEMO_TASK_RESULTS[i];
      item.textContent=task+' Result: '+(seeded||'pending.');
      list.append(item);
    });
    document.getElementById('showcase61-feed-list').textContent=feedback().length?feedback().map(item=>item.text).join(' '):'No tester feedback yet. Results stay pending.';
    const steps=[
      ()=>'Start. DEMO DATA — labelled sample only. Admissions path stays on Overview, Heatmap, Stock Browser, Forecast Lab, then Settings. Hidden Mac views are not required.',
      ()=>{const canvas=document.createElement('canvas'); canvas.width=640; canvas.height=160; const ctx=canvas.getContext('2d'); ctx.fillStyle='#0b1220'; ctx.fillRect(0,0,640,160); ctx.strokeStyle='#7aafff'; ctx.lineWidth=2; ctx.beginPath(); DEMO.prices.forEach((row,i)=>{const x=40+i*140, y=110-(row.price-99)*22; i?ctx.lineTo(x,y):ctx.moveTo(x,y);}); ctx.stroke(); ctx.fillStyle='#d5e2f2'; ctx.font='13px sans-serif'; DEMO.prices.forEach((row,i)=>ctx.fillText(row.price, 30+i*140, 28)); return canvas;},
      ()=>'Event. '+DEMO.event.title+'. Source: '+DEMO.event.source+'. Published '+DEMO.event.published+'. Retrieved '+DEMO.event.retrieved+'.',
      ()=>'Comparison. '+DEMO.compare.map(row=>row.symbol+' '+(row.change>0?'+':'')+row.change+'%').join(' and ')+'. Both figures are sample changes.',
      ()=>'Forecast Lab. '+DEMO.forecast.notice+' Withholding is honesty, not a live prediction feed.',
      ()=>DEMO.investigation+' This is the end. Leaving the demo does not change the company on your chart.'
    ];
    let step=0;
    const finishCopy=cloudDemo()
      ?'Walkthrough complete. Bundled snapshot unchanged · open Overview or Heatmap to explore.'
      :'Demo finished. Your saved records were not changed.';
    const exitCopy=cloudDemo()
      ?'Walkthrough closed. Your chart symbol and bundled data are unchanged.'
      :'Demo closed. Your saved records were not changed.';
    function showStep(){
      const stage=document.getElementById('showcase61-stage');
      const progress=document.getElementById('showcase61-progress');
      const bar=document.getElementById('showcase61-progress-bar');
      stage.innerHTML='';
      if(progress&&bar){
        progress.hidden=false;
        bar.style.width=Math.round(((step+1)/steps.length)*100)+'%';
      }
      const banner=document.createElement('p'); banner.className='desk61-note'; banner.textContent=DEMO.label+' · Step '+(step+1)+' of '+steps.length;
      const body=steps[step]();
      const nav=document.createElement('div'); nav.className='desk61-row';
      const next=document.createElement('button'); next.type='button'; next.className='primary-btn'; next.textContent=step===steps.length-1?'Finish walkthrough':'Next step';
      next.onclick=()=>{ if(step===steps.length-1){ if(progress)progress.hidden=true; stage.innerHTML='<p class="desk61-note">'+finishCopy+'</p>'; return;} step+=1; showStep(); };
      stage.append(banner);
      if(body instanceof HTMLCanvasElement) stage.append(body); else { const text=document.createElement('p'); text.textContent=body; stage.append(text); }
      nav.append(next); stage.append(nav);
    }
    startGuidedDemo=function(){
      markGuidedSeen();
      step=0;
      showStep();
      document.getElementById('showcase61-stage')?.scrollIntoView({block:'nearest',behavior:'smooth'});
    };
    document.getElementById('showcase61-demo').onclick=()=>startGuidedDemo();
    document.getElementById('showcase61-exit').onclick=()=>{
      const progress=document.getElementById('showcase61-progress');
      if(progress)progress.hidden=true;
      document.getElementById('showcase61-stage').innerHTML='<p class="desk61-note">'+exitCopy+'</p>';
    };
    document.getElementById('showcase61-add').onclick=()=>{
      const text=document.getElementById('showcase61-own').value.trim(); if(!text)return;
      const saved=notes(); saved.push({date:new Date().toISOString().slice(0,10), text});
      localStorage.setItem('md-notebook-notes', JSON.stringify(saved));
      const row=document.createElement('p'); row.className='desk61-note'; row.textContent=saved.at(-1).date+' · your note · '+text;
      document.getElementById('showcase61-log').append(row);
      document.getElementById('showcase61-own').value='';
    };
    document.getElementById('showcase61-save-feed').onclick=()=>{
      const text=document.getElementById('showcase61-feed').value.trim(); if(!text)return;
      const saved=feedback(); saved.push({text, status:'recorded'});
      localStorage.setItem('md-tester-feedback', JSON.stringify(saved));
      document.getElementById('showcase61-feed-list').textContent=saved.map(item=>item.text).join(' ');
      document.getElementById('showcase61-feed').value='';
    };
  }

  function beginGuidedDemo(){
    if(!document.getElementById('showcase61')) mount();
    if(typeof startGuidedDemo==='function'){
      startGuidedDemo();
      return true;
    }
    return false;
  }

  window.MarketDeskShowcase={
    beginGuidedDemo,
    markGuidedSeen,
    FIRST_RUN_KEY
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded', mount); else mount();
})();
