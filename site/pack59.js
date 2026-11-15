/* Company research packs. A saved edition stays as it was stored. */
const Pack59=(()=>{
  const sections=['prices','move','events','financials','comparison','scenario','forecast','journal'];
  const labels={prices:'Price history',move:'Move Review',events:'Company events',financials:'Financials',comparison:'Comparison',scenario:'Simulator',forecast:'Forecast scorecard',journal:'Journal'};
  let seq=0,current=null;
  function host(){
    const view=document.getElementById('view-reports');
    if(!view||document.getElementById('pack59'))return;
    view.insertAdjacentHTML('afterbegin','<article class="surface crypto57-panel" id="pack59"><h2>Company research pack</h2><p class="crypto38-foot" id="pack59-note">Only sections with saved evidence are included.</p><div class="crypto38-tools"><label>Company <input id="pack59-symbol" value="TTWO" aria-label="Company"></label><div id="pack59-sections"></div></div><label>Overview wording<textarea id="pack59-wording" rows="3"></textarea></label><div class="crypto38-tools"><button type="button" class="ghost-btn" id="pack59-preview">Build preview</button><button type="button" class="ghost-btn" id="pack59-save">Save edition</button><button type="button" class="ghost-btn" id="pack59-edition">New edition</button><button type="button" class="ghost-btn" id="pack59-export">Export HTML</button><button type="button" class="ghost-btn" id="pack59-explain">Explain in Intelligence</button></div><p class="crypto38-foot">Compare <input id="pack59-older" aria-label="Older edition"> with <input id="pack59-newer" aria-label="Newer edition"> <button type="button" class="ghost-btn" id="pack59-compare">Show what changed</button></p><div id="pack59-results"></div></article>');
    document.getElementById('pack59-sections').innerHTML=sections.map(id=>`<label><input type="checkbox" data-pack-section="${id}" checked> ${labels[id]}</label>`).join('');
  }
  function selected(){return [...document.querySelectorAll('[data-pack-section]:checked')].map(box=>box.dataset.packSection);}
  function render(body){
    current=body;
    const box=document.getElementById('pack59-results');
    if(!box)return;
    const blocks=(body.sections||[]).map(section=>`<details open><summary><strong>${section.title}</strong> · ${section.kind}</summary><p>${section.finding}</p><p class="crypto38-foot">${section.coverage||''}</p><ul>${(section.figures||[]).map(row=>`<li>${row.label}: ${row.value} · ${row.source}</li>`).join('')}</ul></details>`).join('');
    const omitted=(body.omitted||[]).map(row=>`<li>${row.title}: ${row.reason}</li>`).join('');
    box.innerHTML=`<p><strong>Edition ${body.edition||''}</strong> · ${body.name||''} · ${body.symbol||''}</p><p>${body.wordingEdited?body.wording:body.overview||''}</p>${blocks}<h3>Not included</h3><ul>${omitted||'<li>None</li>'}</ul><p class="crypto38-foot">${body.notice||''}</p>`;
  }
  async function post(body){
    const id=++seq;
    const response=await fetch('/api/v3/pack59',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)});
    const data=await response.json();
    if(id!==seq)return null;
    if(!response.ok||data.error)throw Error(data.error||'The pack could not be built.');
    return data;
  }
  function setup(){
    host();
    const symbol=()=>document.getElementById('pack59-symbol').value.trim().toUpperCase();
    const wording=()=>document.getElementById('pack59-wording').value;
    document.getElementById('pack59-preview').addEventListener('click',async()=>{
      const data=await post({action:'preview',symbol:symbol(),selected:selected(),wording:wording()});
      if(data)render(data);
    });
    document.getElementById('pack59-save').addEventListener('click',async()=>{
      const data=await post({action:'save',symbol:symbol(),selected:selected(),wording:wording()});
      if(!data)return;
      sessionStorage.setItem('md-pack59',data.id);
      document.getElementById('pack59-older').value=document.getElementById('pack59-older').value||data.id;
      render(data);
    });
    document.getElementById('pack59-edition').addEventListener('click',async()=>{
      const previous=sessionStorage.getItem('md-pack59')||document.getElementById('pack59-older').value;
      const data=await post({action:'edition',id:previous,wording:wording()});
      if(!data)return;
      document.getElementById('pack59-newer').value=data.id;
      sessionStorage.setItem('md-pack59',data.id);
      render(data);
    });
    document.getElementById('pack59-compare').addEventListener('click',async()=>{
      const data=await post({action:'compare',older:document.getElementById('pack59-older').value.trim(),newer:document.getElementById('pack59-newer').value.trim()});
      if(!data)return;
      document.getElementById('pack59-results').innerHTML=`<p>${data.notice||''}</p><p>New announcements: ${(data.newAnnouncements||[]).map(row=>row.title).join(', ')||'none'}</p><p>Financial changes: ${(data.changedFinancials||[]).map(row=>row.name+' '+row.from+' → '+row.to).join(', ')||'none'}</p><p>Assumption changes: ${(data.changedAssumptions||[]).map(row=>row.name+' '+row.from+' → '+row.to).join(', ')||'none'}</p><p>Forecasts graded since the older edition: ${(data.newlyGraded||[]).map(row=>row.name).join(', ')||'none'}</p>`;
    });
    document.getElementById('pack59-export').addEventListener('click',async()=>{
      const ident=sessionStorage.getItem('md-pack59');
      const response=await fetch('/api/v3/pack59?id='+encodeURIComponent(ident)+'&export=1');
      const data=await response.json();
      const blob=new Blob([data.html||''],{type:'text/html'});
      const link=document.createElement('a');
      link.href=URL.createObjectURL(blob);
      link.download='MarketDesk-research-pack.html';
      link.click();
    });
    document.getElementById('pack59-explain').addEventListener('click',()=>{
      if(!window.Ask48)return;
      Ask48.openFrom({symbol:symbol(),packId:sessionStorage.getItem('md-pack59')||''});
      Ask48.ask('What does this research pack say?');
    });
  }
  document.addEventListener('DOMContentLoaded',setup);
  return {render};
})();
