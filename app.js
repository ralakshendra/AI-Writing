(function(){'use strict';
const $=(selector,scope=document)=>scope.querySelector(selector);
const $$=(selector,scope=document)=>[...scope.querySelectorAll(selector)];
const els={search:$('[data-search]'),filters:$('[data-filter-panel]'),results:$('[data-results]'),count:$('[data-result-count]'),more:$('[data-load-more]'),savedButtons:$$('[data-saved-only]'),savedCount:$('[data-saved-count]'),progress:$('[data-progress]'),pillars:$('[data-pillars]')};
const state={records:[],query:'',course:'All',collection:'All',kind:'All',savedOnly:false,visible:12};
const saved=new Set(readLocal('ai-writing-saved'));
const completed=new Set(readLocal('ai-writing-completed'));
const pillarDescriptions={
 'Exclusive Mini-Courses':'Deep dives into publishing, copywriting, newsletters, Claude, and creator systems.',
 'Ship 30 for 30':'The complete daily writing system—ideas, atomic essays, feedback, and consistent shipping.',
 'Ship 30 for 30 - October 2026':'The current cohort journey, including onboarding, daily assignments, and live sessions.',
 'AIWS Asset Hub':'Reusable AI prompts, skills, cheat sheets, and practical writing assets.',
 'Digital Writing Fundamentals':'Core principles for clear, useful, and compelling online writing.',
 'Digital Mindset Fundamentals':'The habits and beliefs that make creative work sustainable.',
 'Digital Niche Fundamentals':'Choose your territory, clarify your audience, and build a focused content strategy.'
};
function readLocal(key){try{return JSON.parse(localStorage.getItem(key)||'[]')}catch{return[]}}
function persist(){localStorage.setItem('ai-writing-saved',JSON.stringify([...saved]));localStorage.setItem('ai-writing-completed',JSON.stringify([...completed]));}
function esc(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));}
function resourceUrl(id){return 'resource.html?id='+encodeURIComponent(id);}
function openResource(id){window.open(resourceUrl(id),'_blank','noopener');}
function collections(){return ['All',...new Set(state.records.filter(item=>state.course==='All'||item.course===state.course).map(item=>item.collection))];}
function filtered(){return state.records.filter(item=>{const haystack=(item.title+' '+item.description+' '+item.collection+' '+item.course).toLowerCase();return(!state.query||haystack.includes(state.query))&&(state.course==='All'||item.course===state.course)&&(state.collection==='All'||item.collection===state.collection)&&(state.kind==='All'||item.kind===state.kind)&&(!state.savedOnly||saved.has(item.id));});}
function mediaLabel(item){const images=(item.images||[]).length,videos=(item.videos||[]).length;if(!images&&!videos)return'';return '<span class="card-media">'+(images?'▧ '+images:'')+(images&&videos?' · ':'')+(videos?'▶ '+videos:'')+'</span>';}
function card(item){const isSaved=saved.has(item.id),isDone=completed.has(item.id);return '<article class="resource-card'+(isDone?' is-complete':'')+'"><a class="card-hit-area" href="'+resourceUrl(item.id)+'" target="_blank" rel="noopener" aria-label="Open '+esc(item.title)+' in a new tab"></a><div class="card-top"><span class="kind">'+esc(item.kind)+'</span><button class="save" type="button" data-save="'+esc(item.id)+'" aria-label="'+(isSaved?'Remove from saved':'Save resource')+'" aria-pressed="'+isSaved+'">'+(isSaved?'★':'☆')+'</button></div><p class="resource-path">'+esc(item.course)+' · '+esc(item.collection)+'</p><h3>'+esc(item.title)+'</h3><p>'+esc(item.description||'Open this imported resource in AI Writing.')+'</p>'+mediaLabel(item)+'<a class="open-resource" href="'+resourceUrl(item.id)+'" target="_blank" rel="noopener">'+(isDone?'REVISIT RESOURCE':'OPEN RESOURCE')+' <span aria-hidden="true">↗</span></a></article>';}
function syncStatus(){els.savedCount.textContent=saved.size;els.savedButtons.forEach(button=>button.setAttribute('aria-pressed',String(state.savedOnly)));const total=state.records.length||1,percent=Math.min(100,Math.round(completed.size/total*100));$('strong',els.progress).textContent=completed.size;$('span',els.progress).textContent='of '+state.records.length+' explored';$('b',els.progress).style.width=percent+'%';}
function render(){const list=filtered(),shown=list.slice(0,state.visible);els.count.textContent=list.length+' resource'+(list.length===1?'':'s');els.results.innerHTML=shown.length?shown.map(card).join(''):'<div class="empty-state"><strong>No resources match yet.</strong><span>Try another phrase or clear a filter.</span></div>';els.more.hidden=shown.length>=list.length;syncStatus();}
function filterRow(label,group,values){return '<div class="filter-row"><span>'+label+'</span>'+values.map(value=>'<button type="button" data-filter-group="'+group+'" data-filter="'+esc(value)+'" aria-pressed="'+(state[group]===value)+'">'+esc(value)+'</button>').join('')+'</div>';}
function makeFilters(){const courses=['All',...new Set(state.records.map(item=>item.course))],kinds=['All','Lesson','Prompt','Skill','Cheat sheet','Template','Replay','Bonus','Assignment'];const folderRow=state.course==='All'?'':filterRow('Folder','collection',collections());els.filters.innerHTML=filterRow('Core topic','course',courses)+folderRow+filterRow('Format','kind',kinds);}
function chooseFilter(group,value){state[group]=value;if(group==='course')state.collection='All';state.visible=12;makeFilters();render();}
function makePillars(pillars){const order=['Ship 30 for 30','Ship 30 for 30 - October 2026','Digital Writing Fundamentals','Digital Niche Fundamentals','Digital Mindset Fundamentals','Exclusive Mini-Courses','AIWS Asset Hub'];const sorted=[...pillars].sort((a,b)=>order.indexOf(a.name)-order.indexOf(b.name));els.pillars.innerHTML=sorted.map((pillar,index)=>'<button class="pillar-card" type="button" data-pillar="'+esc(pillar.name)+'"><span>0'+(index+1)+' · '+pillar.count+' RESOURCES</span><i aria-hidden="true">→</i><strong>'+esc(pillar.name)+'</strong><small>'+esc(pillarDescriptions[pillar.name]||pillar.collections+' collections from the supplied archive.')+'</small></button>').join('');}
els.search.addEventListener('input',()=>{state.query=els.search.value.trim().toLowerCase();state.visible=12;render();});
document.addEventListener('keydown',event=>{if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){event.preventDefault();els.search.focus();}});
els.filters.addEventListener('click',event=>{const button=event.target.closest('[data-filter]');if(button)chooseFilter(button.dataset.filterGroup,button.dataset.filter);});
els.pillars.addEventListener('click',event=>{const button=event.target.closest('[data-pillar]');if(button){chooseFilter('course',button.dataset.pillar);document.querySelector('#library').scrollIntoView();}});
els.results.addEventListener('click',event=>{const saveButton=event.target.closest('[data-save]');if(saveButton){event.preventDefault();event.stopPropagation();const id=saveButton.dataset.save;saved.has(id)?saved.delete(id):saved.add(id);persist();render();}});
els.savedButtons.forEach(button=>button.addEventListener('click',()=>{state.savedOnly=!state.savedOnly;state.visible=12;render();document.querySelector('#library').scrollIntoView();}));
els.more.addEventListener('click',()=>{state.visible+=12;render();});
$('[data-surprise]').addEventListener('click',()=>{if(!state.records.length)return;const item=state.records[Math.floor(Math.random()*state.records.length)];openResource(item.id);});
fetch('data/library.json').then(response=>{if(!response.ok)throw new Error('Library unavailable');return response.json();}).then(data=>{state.records=data.records;makePillars(data.pillars||[]);makeFilters();$('[data-total-count]').textContent=data.count;$('[data-pillar-count]').textContent=(data.pillars||[]).length;$('[data-media-count]').textContent=data.records.filter(item=>(item.images||[]).length||(item.videos||[]).length).length;render();}).catch(()=>{els.results.innerHTML='<div class="empty-state"><strong>AI Writing could not load.</strong><span>Refresh the page or restart the local preview.</span></div>';els.count.textContent='Library unavailable';});
})();
