#!/usr/bin/env node
// Preserve a scoped component stylesheet inside canonical Studio sections.
// Writes only the supplied working copy and an evidence directory outside it.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
const require=createRequire(import.meta.url);
const postcss=require('postcss'),selectorParser=require('postcss-selector-parser'),tailwind=require('tailwindcss');
const {chromium}=require('playwright');
const {values}=parseArgs({options:{adt:{type:'string'},stylesheet:{type:'string'},out:{type:'string'}}});
if(!values.adt||!values.stylesheet||!values.out)throw new Error('Use --adt ADT --stylesheet COMPONENT_CSS --out EVIDENCE_FOLDER');
const root=fs.realpathSync(values.adt),out=path.resolve(values.out),cssFile=path.resolve(values.stylesheet);
if(out===root||out.startsWith(root+path.sep))throw new Error('Evidence must be outside the reader.');
fs.mkdirSync(out,{recursive:true});
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const sourceCSS=fs.readFileSync(cssFile,'utf8'),sourceHash=hash(sourceCSS);
const recordPath=path.join(out,'style-conversion.json');
const prior=fs.existsSync(recordPath)?JSON.parse(fs.readFileSync(recordPath,'utf8')):null;
if(prior&&prior.stylesheet_sha256!==sourceHash)throw new Error('Component stylesheet changed; rebuild from the accepted source before converting again.');
function specificity(selector){
 const total=[0,0,0];
 function visit(n,s){
  if(n.type==='id')s[0]++;
  else if(n.type==='class'||n.type==='attribute')s[1]++;
  else if(n.type==='tag')s[2]++;
  else if(n.type==='pseudo'){
   if(n.value.startsWith('::'))s[2]++;
   else if(n.value===':where')return;
   else if([':is',':not',':has'].includes(n.value)){
    const nested=(n.nodes||[]).map(c=>{const t=[0,0,0];for(const v of c.nodes||[])visit(v,t);return t});
    nested.sort((a,b)=>b[0]-a[0]||b[1]-a[1]||b[2]-a[2]);
    for(let i=0;i<3;i++)s[i]+=nested[0]?.[i]||0;
   }else s[1]++;
  }
 }
 for(const n of selectorParser().astSync(selector).nodes[0].nodes)visit(n,total);
 return total;
}
const compare=(a,b)=>a.specificity[0]-b.specificity[0]||a.specificity[1]-b.specificity[1]||a.specificity[2]-b.specificity[2]||a.order-b.order;
const staticRules=[],dynamicRules=[];let order=0;
postcss.parse(sourceCSS).walkRules(rule=>{
 const declarations=rule.nodes.filter(n=>n.type==='decl').map(n=>({property:n.prop,value:n.value,important:!!n.important,text:n.toString()}));
 let parent=rule.parent;const media=[];
 while(parent&&parent.type!=='root'){
  if(parent.type!=='atrule'||parent.name!=='media')throw new Error('Unsupported CSS grouping; preserve/implement it explicitly: '+parent.name);
  media.unshift(parent.params);parent=parent.parent;
 }
 for(const n of selectorParser().astSync(rule.selector).nodes){
  const selector=n.toString().trim();
  if(!selector.startsWith('#content.pdf-document'))throw new Error('Expected #content.pdf-document scope; adapt the actual component scope explicitly.');
  const record={selector,declarations,media,specificity:specificity(selector),order:order++};
  if(media.length||/::|:(?:hover|focus|active|checked|disabled|enabled)|\[aria-pressed|\.(?:pdf-word-found|pdf-word-start|pdf-found|selected-option)\b/.test(selector))dynamicRules.push(record);
  else staticRules.push({...record,selector:selector.replaceAll('#content.pdf-document','section.pdf-document')});
 }
});
staticRules.sort(compare);dynamicRules.sort(compare);
// Atomic utility ordering is not CSS source ordering. Increasing root
// specificity preserves the sorted component rule priority for state/media
// conflicts (e.g. found-word green must win over pressed-cell purple).
const utilities=[];
for(const [rank,r] of dynamicRules.entries()){
 const variant=r.selector.replaceAll('#content.pdf-document','&'.repeat(rank+1)).replace(/\s+/g,'_');
 for(const d of r.declarations){
  const value=d.value.replaceAll('_','\\_').replace(/\s+/g,'_');
  const cls=r.media.map(m=>'[@media'+m.replace(/\s+/g,'_')+']:').join('')+'['+variant+']:!['+d.property+':'+value+']';
  utilities.push(cls);
 }
}
const pages=JSON.parse(fs.readFileSync(path.join(root,'content/pages.json'),'utf8'));
const browser=await chromium.launch({headless:true,...(process.env.ADT_CHROME?{executablePath:process.env.ADT_CHROME}:{})});
const pageRecords={};
try{
 const page=await browser.newPage();
 for(const item of pages){
  const file=path.join(root,item.href);if(path.dirname(file)!==root)throw new Error('Unsafe page path');
  const source=fs.readFileSync(file,'utf8'),old=prior?.pages?.[item.href];
  if(old&&hash(source)!==old.output_sha256&&hash(source)!==old.input_sha256)throw new Error('Page changed since conversion; rebuild or reconcile authored styles first: '+item.href);
  const converted=await page.evaluate(({source,rules,utilities,originalStyles})=>{
   const doc=new DOMParser().parseFromString(source.trimEnd(),'text/html');
   const root=doc.querySelector('section.pdf-document');if(!root)throw new Error('Missing canonical presentation section');
   const nodes=[root,...root.querySelectorAll('*')];
   const authored=originalStyles||nodes.map(n=>n.getAttribute('style'));
   if(authored.length!==nodes.length)throw new Error('DOM structure changed during conversion');
   const declarations=new Map(nodes.map(n=>[n,[]]));
   for(const r of rules)for(const n of doc.querySelectorAll(r.selector)){
    if(!declarations.has(n))throw new Error('Rule escapes section');
    declarations.get(n).push(...r.declarations.map(d=>d.text));
   }
   nodes.forEach((n,index)=>{
    // Keep authored CSS as declaration TEXT. CSSOM longhand enumeration loses
    // pending var() substitutions and can delete border/background shorthands.
    const parts=declarations.get(n);if(authored[index])parts.push(authored[index]);
    if(parts.length)n.setAttribute('style',parts.join(';')+';');else n.removeAttribute('style');
   });
   root.className='pdf-document';root.classList.add(...utilities);
   for(const n of [...root.childNodes].filter(n=>n.nodeType===8&&n.textContent.startsWith(' Studio Tailwind candidates:')))n.remove();
   root.prepend(doc.createComment(' Studio Tailwind candidates: '+utilities.join(' ')+' '));
   return{html:'<!DOCTYPE html>\n'+doc.documentElement.outerHTML+'\n',authored};
  },{source,rules:staticRules,utilities,originalStyles:old?.authored_inline_styles});
  fs.writeFileSync(file,converted.html);
  pageRecords[item.href]={input_sha256:old?.input_sha256||hash(source),output_sha256:hash(converted.html),authored_inline_styles:converted.authored};
 }
}finally{await browser.close()}
const compiled=await postcss([tailwind({content:[{raw:utilities.join(' '),extension:'html'}],corePlugins:{preflight:false}})]).process('@tailwind utilities;',{from:undefined});
const runtimeCSS=path.join(root,'content/tailwind_output.css');
const marker='/* ADT Studio handoff utilities: supported additive build */';
const original=fs.readFileSync(runtimeCSS,'utf8').split(marker)[0].trimEnd();
fs.writeFileSync(runtimeCSS,original+'\n'+marker+'\n'+compiled.css+'\n');
fs.writeFileSync(path.join(out,'studio-utilities.css'),compiled.css+'\n');
fs.writeFileSync(recordPath,JSON.stringify({stylesheet_sha256:sourceHash,static_rules:staticRules.length,dynamic_rules:dynamicRules.length,utilities,compiled_utilities_sha256:hash(compiled.css),base_reader_css_sha256:hash(original),pages:pageRecords},null,2)+'\n');
console.log(JSON.stringify({pages:pages.length,staticRules:staticRules.length,dynamicRules:dynamicRules.length,utilities:utilities.length,compiledBytes:compiled.css.length}));
