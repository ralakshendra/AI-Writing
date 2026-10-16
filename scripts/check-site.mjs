import fs from 'node:fs';
const required=['index.html','resource.html','styles.css','app.js','resource.js','data/library.json','.nojekyll'];
const missing=required.filter(file=>!fs.existsSync(file));
const html=fs.readFileSync('index.html','utf8');
const data=JSON.parse(fs.readFileSync('data/library.json','utf8'));
const errors=[...missing.map(file=>`Missing ${file}`)];
for(const token of ['AI WRITING','Ship 30','Skip to main content','id="main-content"','data-pillars'])if(!html.includes(token))errors.push(`Missing site text: ${token}`);
const resourceHtml=fs.readFileSync('resource.html','utf8');
for(const token of ['data-resource-document','data-resource-body','data-resource-source','Back to library'])if(!resourceHtml.includes(token))errors.push(`Missing resource page element: ${token}`);
for(const banned of ['BUILD MY AI MOVIE STUDIO','Alexx Roy','AI FilmCraft','build-my-ai-movie-mark.svg','alexx-portrait.webp'])if(html.includes(banned))errors.push(`Old branding remains: ${banned}`);
if(data.count!==data.records.length)errors.push('Library count does not match records');
if(new Set(data.records.map(item=>item.id)).size!==data.records.length)errors.push('Duplicate resource IDs');
if(!data.pillars?.some(item=>item.name==='Ship 30 for 30'))errors.push('Ship 30 for 30 pillar is missing');
for(const item of data.records){if(!item.title||!item.course||!item.collection||!item.kind)errors.push(`Incomplete resource ${item.id}`);for(const image of item.images||[]){if(image.src.startsWith('assets/')&&!fs.existsSync(image.src))errors.push(`Missing image ${image.src}`)}for(const video of item.videos||[]){if(!video.url)errors.push(`Missing video URL in ${item.id}`)}}
console.log(JSON.stringify({pages:1,resources:data.records.length,pillars:data.pillars?.length||0,readable:data.records.filter(item=>item.hasContent).length,withImages:data.records.filter(item=>item.images?.length).length,withVideos:data.records.filter(item=>item.videos?.length).length,errors},null,2));
if(errors.length)process.exit(1);
