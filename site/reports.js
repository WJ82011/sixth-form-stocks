/* Market Desk 1.7 — sourced, private research report authoring. */
'use strict';
const REPORT_KEY='md-reborn-reports';
const REPORT_FIELDS=['summary','business','financial','valuation','catalysts','risks','sources'];
const REPORT_LABELS={summary:'Executive summary',business:'What the company does & its competitors',financial:'Financial results & dates',valuation:'Valuation & assumptions',catalysts:'Upside drivers & catalysts',risks:'Bear case & disconfirming evidence',sources:'References & source dates'};
let reportEditingId=null;
function normaliseLocalReports(items){if(!Array.isArray(items))return [];return items.slice(0,120).filter(o=>o&&typeof o==='object'&&safeSymbol(String(o.symbol||'')) ).map(o=>({
 id:String(o.id||'').slice(0,80),symbol:String(o.symbol).slice(0,24),title:String(o.title||'').slice(0,150),status:['Draft','In review','Completed'].includes(o.status)?o.status:'Draft',
 ...Object.fromEntries(REPORT_FIELDS.map(k=>[k,String(o[k]||'').slice(0,k==='summary'?5000:k==='catalysts'?5000:6000)])),
 checks:Object.fromEntries(['primary','counter','periods'].map(k=>[k,Boolean(o.checks?.[k])])),deleted:o.deleted===true,created:String(o.created||'').slice(0,50),updated:String(o.updated||'').slice(0,50)
}))}
function mergeReportArchives(local,remote){
 const map=new Map();
 // Deletion tombstones win over stale server copies; on identical timestamps a deletion wins.
 for(const r of [...normaliseLocalReports(remote),...normaliseLocalReports(local)])if(r.id){
  const old=map.get(r.id);
  if(!old||String(r.updated)>String(old.updated)||(String(r.updated)===String(old.updated)&&r.deleted&&!old.deleted))map.set(r.id,r);
 }
 const ordered=[...map.values()].sort((a,b)=>String(b.updated).localeCompare(String(a.updated)));
 return [...ordered.filter(r=>!r.deleted).slice(0,40),...ordered.filter(r=>r.deleted).slice(0,80)];
}
function readReports(){return normaliseLocalReports(savedJSON(REPORT_KEY,[])).filter(r=>!r.deleted)}
function reportGetEditor(){return {symbol:$('report-symbol').value,title:$('report-title').value.trim(),status:$('report-status').value,
 ...Object.fromEntries(REPORT_FIELDS.map(k=>[k,$('report-'+k).value.trim()])),
 checks:Object.fromEntries(['primary','counter','periods'].map(k=>[k,$('report-'+k).checked]))}}
function reportFillEditor(r){
 $('report-symbol').value=r.symbol||E.selected;$('report-title').value=r.title||'';$('report-status').value=r.status||'Draft';
 for(const k of REPORT_FIELDS)$('report-'+k).value=r[k]||'';
 for(const k of ['primary','counter','periods'])$('report-'+k).checked=Boolean(r.checks?.[k]);
}
function reportReset(){reportEditingId=null;reportFillEditor({symbol:E.selected,status:'Draft'});$('report-feedback').textContent='New draft. Add your own views and link to your sources.';renderReportLibrary();}
function reportSave(){const data=reportGetEditor();if(!safeSymbol(data.symbol)){toast('Choose a valid company ticker.');return}if(data.title.length<4){toast('Please add a descriptive report title.');$('report-title').focus();return}
 const list=readReports(),now=new Date().toISOString(),existing=list.find(r=>r.id===reportEditingId);
 const record={...data,id:existing?.id||(globalThis.crypto?.randomUUID?.()||'md-'+Date.now()+'-'+Math.random().toString(36).slice(2)),created:existing?.created||now,updated:now};
 if(existing){const idx=list.findIndex(r=>r.id===existing.id);list[idx]=record}else{list.unshift(record);if(list.length>40){toast('Maximum 40 reports. Delete an older report before saving another.');return}}
 saveJSON(REPORT_KEY,mergeReportArchives(list,savedJSON(REPORT_KEY,[])));reportEditingId=record.id;renderReportLibrary();reportPreview(record);$('report-feedback').textContent='Saved privately on this Mac · '+new Date().toLocaleString('en-GB');toast('Research report saved and included in your private workspace backup.');
}
function reportLoad(id){const record=readReports().find(r=>r.id===id);if(!record)return;reportEditingId=record.id;reportFillEditor(record);reportPreview(record);renderReportLibrary();$('report-feedback').textContent='Editing report last saved '+(record.updated||'date unavailable');}
function reportDelete(id){const record=readReports().find(r=>r.id===id);if(!record)return;if(!window.confirm('Delete the saved report "'+record.title+'"? This cannot be undone unless you have an earlier backup.'))return;
 const tombstone={...record,deleted:true,updated:new Date().toISOString()};
 saveJSON(REPORT_KEY,mergeReportArchives([tombstone,...readReports().filter(r=>r.id!==id)],savedJSON(REPORT_KEY,[])));
 // Store the deletion synchronously in browser storage BEFORE allowing reload.
 if(reportEditingId===id)reportReset();renderReportLibrary();toast('Report deleted; deletion saved locally and queued for private server backup.');}
function renderReportLibrary(){const list=readReports();$('report-count').textContent=list.length;
 $('report-library').innerHTML=list.length?list.map(r=>'<article class="report-library-item '+(reportEditingId===r.id?'selected':'')+'"><span class="report-library-status">'+escapeHtml(r.status)+'</span><strong>'+escapeHtml(r.title||r.symbol)+'</strong><small>'+escapeHtml(r.symbol)+' · '+escapeHtml(r.updated?new Date(r.updated).toLocaleDateString('en-GB'):'Date unavailable')+'</small><div class="report-library-actions"><button type="button" data-report-open="'+escapeHtml(r.id)+'">Edit / view</button><button type="button" data-report-delete="'+escapeHtml(r.id)+'" class="text-danger">Delete</button></div></article>').join(''):'<p class="compare-disclosure">No reports saved yet. Write a draft and select Save report.</p>'}
function reportDocumentHtml(r){const sections=REPORT_FIELDS.map(k=>'<section class="report-doc-section"><h3>'+escapeHtml(REPORT_LABELS[k])+'</h3><p>'+escapeHtml(r[k]||'Not yet completed.').replace(/\n/g,'<br>')+'</p></section>').join('');
 const checklist=[['primary','Primary financial sources checked'],['counter','Contrary evidence considered'],['periods','Dates and currency included']];
 return '<div class="report-doc-head"><div class="report-doc-mark">M / DESK</div><span>INDEPENDENT EQUITY RESEARCH · '+escapeHtml(r.status||'Draft')+'</span><h2>'+escapeHtml(r.title||'Untitled research report')+'</h2><div>'+escapeHtml(r.symbol||'—')+' · '+escapeHtml(r.updated?new Date(r.updated).toLocaleDateString('en-GB'):'Unsaved draft')+'</div></div>'+sections+'<div class="report-doc-checklist"><h3>Research integrity checklist</h3>'+checklist.map(([k,label])=>'<p>'+(r.checks?.[k]?'☑':'☐')+' '+label+'</p>').join('')+'</div><div class="report-doc-footer">Market Desk independent research · Opinions and scenarios are the author’s, not financial advice · Verify figures against cited sources.</div>';
}
function reportPreview(r=reportGetEditor()){const pane=$('report-preview-content');pane.innerHTML=reportDocumentHtml(r)}
function reportMarkdown(r){
 const cleaned=s=>String(s||'Not yet completed.').replace(/\r/g,'');
 const lines=['# '+cleaned(r.title||'Untitled research report'),'','**Company:** '+cleaned(r.symbol),'**Status:** '+cleaned(r.status),'**Updated:** '+cleaned(r.updated||new Date().toISOString().slice(0,10)),''];
 for(const k of REPORT_FIELDS)lines.push('## '+REPORT_LABELS[k],'',cleaned(r[k]),'');
 lines.push('## Research integrity checks','',...['primary','counter','periods'].map(k=>'- ['+(r.checks?.[k]?'x':' ')+'] '+({primary:'Primary sources checked',counter:'Contrary evidence considered',periods:'Dates and currency included'}[k])),'','---','Prepared using Market Desk. Independently verify source data. Not investment advice.');return lines.join('\n')}
function reportDownload(){const r=reportGetEditor();if(!r.title){toast('Add a report title before exporting.');return}const blob=new Blob([reportMarkdown({...r,updated:new Date().toISOString()})],{type:'text/markdown;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='MarketDesk-'+(r.symbol||'Research')+'-'+new Date().toISOString().slice(0,10)+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500)}
function reportPrint(){const r=reportGetEditor();if(!r.title){toast('Add a report title before printing.');return}reportPreview({...r,updated:new Date().toISOString()});document.body.classList.add('report-print-mode');window.print()}
function reportsOnView(){researchUpdatePickers();renderReportLibrary()}
function setupResearchV17(){
 $('compare-run').addEventListener('click',runComparison);$('compare-to-report').addEventListener('click',comparisonToReport);
 $('report-from-comparison').addEventListener('click',()=>changeView('comparison'));
 $('report-new').addEventListener('click',reportReset);$('report-clear').addEventListener('click',reportReset);
 $('report-save').addEventListener('click',reportSave);$('report-preview').addEventListener('click',()=>reportPreview());
 $('report-export-md').addEventListener('click',reportDownload);$('report-print').addEventListener('click',reportPrint);
 window.addEventListener('afterprint',()=>document.body.classList.remove('report-print-mode'));
 document.addEventListener('click',e=>{
  const edit=e.target.closest('[data-report-open]');if(edit){reportLoad(edit.dataset.reportOpen);return}
  const del=e.target.closest('[data-report-delete]');if(del){reportDelete(del.dataset.reportDelete);return}
 });
 window.addEventListener('marketdesk:workspace-restored',()=>{if($('report-library'))renderReportLibrary()});
}
