(function(){'use strict';
const $=selector=>document.querySelector(selector);
const id=new URLSearchParams(location.search).get('id');
const saved=new Set(readLocal('ai-writing-saved'));
const completed=new Set(readLocal('ai-writing-completed'));
let resource=null;
function readLocal(key){try{return JSON.parse(localStorage.getItem(key)||'[]')}catch{return[]}}
function persist(){localStorage.setItem('ai-writing-saved',JSON.stringify([...saved]));localStorage.setItem('ai-writing-completed',JSON.stringify([...completed]));}
function esc(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));}
function videoCard(video){const art=video.thumbnail?'<img src="'+esc(video.thumbnail)+'" alt="" loading="lazy">':'';return '<a class="resource-video" href="'+esc(video.url)+'" target="_blank" rel="noopener noreferrer">'+art+'<div><span>WATCH ON '+esc(video.provider).toUpperCase()+'</span><b aria-hidden="true">▶</b></div></a>';}
function syncButtons(){if(!resource)return;const done=completed.has(resource.id),isSaved=saved.has(resource.id);const complete=$('[data-resource-complete]'),save=$('[data-resource-save]');complete.setAttribute('aria-pressed',String(done));complete.textContent=done?'✓ EXPLORED':'MARK AS EXPLORED';save.setAttribute('aria-pressed',String(isSaved));save.textContent=isSaved?'★ SAVED':'☆ SAVE RESOURCE';}
function render(item){resource=item;document.title=item.title+' | AI Writing';$('[data-resource-meta]').textContent=item.course+' · '+item.collection+' · '+item.kind;$('[data-resource-title]').textContent=item.title;$('[data-resource-description]').textContent=item.description||'A resource from the AI Writing library.';$('[data-resource-body]').innerHTML=item.content||'<p>This archived page does not include a readable text block. Use the original source link to view it.</p>';const videos=$('[data-resource-videos]');videos.innerHTML=(item.videos||[]).map(videoCard).join('');videos.hidden=!(item.videos||[]).length;const source=$('[data-resource-source]');source.hidden=!item.source;source.href=item.source||'#';completed.add(item.id);persist();syncButtons();}
$('[data-resource-complete]').addEventListener('click',()=>{if(!resource)return;completed.has(resource.id)?completed.delete(resource.id):completed.add(resource.id);persist();syncButtons();});
$('[data-resource-save]').addEventListener('click',()=>{if(!resource)return;saved.has(resource.id)?saved.delete(resource.id):saved.add(resource.id);persist();syncButtons();});
if(!id){$('[data-resource-title]').textContent='Resource not found';$('[data-resource-description]').textContent='Return to the library and choose a resource to open.';return;}
fetch('data/library.json').then(response=>{if(!response.ok)throw new Error('Library unavailable');return response.json();}).then(data=>{const item=data.records.find(record=>record.id===id);if(!item)throw new Error('Resource not found');render(item);}).catch(error=>{$('[data-resource-title]').textContent='Resource unavailable';$('[data-resource-description]').textContent=error.message;$('[data-resource-body]').innerHTML='<p>Please return to the library and try opening the resource again.</p>';});
})();
