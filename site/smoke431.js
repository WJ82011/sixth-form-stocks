/* Local smoke check. It runs only when the page is opened with ?smoke=431. */
(function(){
  const params=new URLSearchParams(location.search);
  if(params.get('smoke')!=='431')return;
  const lines=[];
  const pass=text=>lines.push('PASS '+text);
  const fail=text=>lines.push('FAIL '+text);
  function report(){
    let node=document.getElementById('smoke431-result');
    if(!node){node=document.createElement('pre');node.id='smoke431-result';document.body.append(node)}
    node.textContent=lines.join('\n');
  }
  function wait(ms){return new Promise(resolve=>setTimeout(resolve,ms))}
  async function until(read,label){
    for(let step=0;step<80;step++){
      const value=read();
      if(value)return value;
      await wait(50);
    }
    if(label)fail(label);
    return null;
  }
  async function run(){
    try{
      const rail=await until(()=>document.querySelectorAll('#look43-rail [data-view]').length>=5&&typeof E!=='undefined','homepage controls');
      if(!rail){report();return}
      pass('homepage controls are on the page');
      for(const button of document.querySelectorAll('#look43-rail [data-view]')){
        button.click();
        const expected='view-'+button.dataset.view;
        const opened=await until(()=>document.querySelector('.view.active')?.id===expected,'');
        if(opened)pass(button.getAttribute('aria-label')+' opens '+button.dataset.view);
        else fail(button.getAttribute('aria-label')+' active='+(document.querySelector('.view.active')?.id||'none')+' desk='+E.view+' change='+typeof changeView);
      }
      document.querySelector('#look43-rail [data-view="home"]')?.click();
      await wait(30);
      function gap(){
        const board=document.getElementById('look43-board');
        if(!board)return null;
        return Math.round(window.innerWidth-board.getBoundingClientRect().right);
      }
      document.querySelector('#look43-mode [data-v43-edition="standard"]')?.click();
      await wait(40);
      const standard=gap();
      if(standard!==null&&standard>=8&&standard<=40)pass('standard fills the window');
      else fail('standard right gap '+standard);
      document.querySelector('#look43-mode [data-v43-edition="professional"]')?.click();
      await wait(40);
      const professional=gap();
      if(professional!==null&&professional>=8&&professional<=40)pass('professional fills the window');
      else fail('professional right gap '+professional);
      document.querySelector('#look43-mode [data-v43-edition="standard"]')?.click();
      const original=window.api;
      const held=[];
      window.api=function(url){
        const result=original.apply(this,arguments);
        if(String(url).includes('/api/saved-news?symbol=TTWO'))return new Promise(resolve=>held.push(()=>result.then(resolve)));
        if(String(url).includes('/api/v3/events42?symbol=TTWO'))return new Promise(resolve=>held.push(()=>result.then(resolve)));
        return result;
      };
      if(typeof commitView==='function')commitView('news');
      setSelected('TTWO');
      const news=loadNews(false);
      const events=window.Events42?.open?.();
      setSelected('AMD');
      const replacement=loadNews(false);
      held.splice(0).forEach(release=>release());
      await Promise.all([news,replacement,events].filter(Boolean));
      await wait(40);
      const newsText=document.getElementById('news-content')?.textContent||'';
      const selected=E.selected;
      if(selected==='AMD'&&newsText.includes('AMD')&&!newsText.includes('TTWO'))pass('late Take-Two news does not replace AMD');
      else fail('selection '+selected+' news '+newsText.slice(0,140));
      commitView('company');
      window.Events42?.open?.();
      await wait(40);
      const eventText=document.getElementById('events42-status')?.textContent||'';
      if(selected==='AMD'&&!eventText.startsWith('TTWO'))pass('company events follow AMD');
      else fail('events status '+eventText.slice(0,140));
      const forecast=document.getElementById('forecast-content')?.textContent||'';
      if(forecast.includes('AMD')&&!forecast.includes('TTWO'))pass('research follows AMD');
      else fail('research text '+forecast.slice(0,140));
    }catch(error){fail(error.message)}
    report();
  }
  const marker=document.createElement('pre');
  marker.id='smoke431-result';
  marker.textContent='RUNNING';
  (document.body||document.documentElement).append(marker);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);
  else run();
})();
