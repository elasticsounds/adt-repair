// Real CSS variable shorthands, overlapping states, phone styles and repeatability.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(repo,'plugins/adt-repair/package.json'));
const {chromium}=require('playwright');
const tmp=await fs.mkdtemp(path.join(os.tmpdir(),'adt-styles-'));
let browser;
try{
 const book=path.join(tmp,'book'),out=path.join(tmp,'evidence'),css=path.join(tmp,'components.css');
 await fs.mkdir(path.join(book,'content'),{recursive:true});
 await fs.writeFile(path.join(book,'content/pages.json'),JSON.stringify([{href:'lesson.html'}]));
 await fs.writeFile(path.join(book,'content/tailwind_output.css'),'/* original reader */\n');
 await fs.writeFile(path.join(book,'lesson.html'),`<!doctype html><html><head><link rel="stylesheet" href="content/tailwind_output.css"></head><body><section class="pdf-document"><div class="panel"><button class="cell" aria-pressed="false">A</button></div></section></body></html>`);
 await fs.writeFile(css,`#content.pdf-document {--line:rgb(125,57,160)}
#content.pdf-document .panel {border:2px solid var(--line);background:var(--surface,white)}
#content.pdf-document .cell[aria-pressed="true"] {background:purple}
#content.pdf-document .cell.pdf-word-found {background:rgb(200,232,181)}
@media (max-width:600px) {#content.pdf-document .panel {padding:10px}}`);
 const run=()=>{const r=spawnSync(process.execPath,[path.join(repo,'plugins/adt-repair/skills/adt-pdf-restyle/scripts/studio_styles.mjs'),'--adt',book,'--stylesheet',css,'--out',out],{encoding:'utf8'});assert.equal(r.status,0,r.stderr)};
 run();const first=await fs.readFile(path.join(book,'lesson.html'));run();assert.deepEqual(await fs.readFile(path.join(book,'lesson.html')),first);
 browser=await chromium.launch({headless:true,...(process.env.ADT_CHROME?{executablePath:process.env.ADT_CHROME}:{})});
 const p=await browser.newPage({viewport:{width:375,height:600}});await p.goto(pathToFileURL(path.join(book,'lesson.html')).href);
 assert.equal(await p.locator('.panel').evaluate(e=>getComputedStyle(e).borderTop),'2px solid rgb(125, 57, 160)');
 assert.equal(await p.locator('.panel').evaluate(e=>getComputedStyle(e).padding),'10px');
 await p.locator('.cell').evaluate(e=>{e.setAttribute('aria-pressed','true');e.classList.add('pdf-word-found')});
 assert.equal(await p.locator('.cell').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(200, 232, 181)');
 console.log('Style fidelity passed: variable border, overlapping selection, phone media and repeatability.');
}finally{await browser?.close();await fs.rm(tmp,{recursive:true,force:true})}
