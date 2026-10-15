import fs from 'node:fs';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const dist=path.join(root,'dist');
fs.rmSync(dist,{recursive:true,force:true});
fs.mkdirSync(dist,{recursive:true});
for(const file of ['index.html','styles.css','app.js','.nojekyll'])fs.copyFileSync(path.join(root,file),path.join(dist,file));
for(const directory of ['assets','data'])fs.cpSync(path.join(root,directory),path.join(dist,directory),{recursive:true});
console.log('Built static site in dist.');
