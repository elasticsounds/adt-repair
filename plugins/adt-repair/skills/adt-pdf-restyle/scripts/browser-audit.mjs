#!/usr/bin/env node
// Capture all section/language/viewport combinations; this is not activity testing.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import {pathToFileURL} from 'node:url';

const require = createRequire(import.meta.url);
const {chromium} = require('playwright');
const axePath = require.resolve('axe-core/axe.min.js');
const {values} = parseArgs({options: {
  adt: {type: 'string'}, out: {type: 'string'}, file: {type: 'boolean', default: false},
  widths: {type: 'string', default: '1280,768,375,320'}, languages: {type: 'string'},
  'language-storage': {type: 'string', default: 'json'},
}});
if (!values.adt || !values.out) {
  console.error('Usage: node browser-audit.mjs --adt ADT_FOLDER --out EVIDENCE_FOLDER [--file]');
  process.exit(1);
}
const root = await fs.realpath(values.adt), out = path.resolve(values.out);
if (out === root || out.startsWith(root + path.sep)) throw new Error('Write evidence outside the ADT.');
const spine = JSON.parse(await fs.readFile(path.join(root, 'content/pages.json'), 'utf8'));
const config = JSON.parse(await fs.readFile(path.join(root, 'assets/config.json'), 'utf8'));
const languages = values.languages?.split(',') ?? config.languages?.available ?? [];
const widths = values.widths.split(',').map(Number);
const narrowest = Math.min(...widths);
if (!languages.length || widths.some(n => !Number.isInteger(n) || n < 200)) throw new Error('Check configured languages and widths.');
if (languages.some(l => !config.languages.available.includes(l))) throw new Error('Requested language is not configured in this book.');
if (!['json', 'plain'].includes(values['language-storage'])) throw new Error('--language-storage must be json or plain.');
await fs.mkdir(out, {recursive: true});
// Append each capture for crash recovery instead of rewriting every earlier row.
const journal = path.join(out, 'browser-results.jsonl');
await fs.writeFile(journal, '');
// A failed new run must not leave an old final result looking current.
await fs.rm(path.join(out, 'browser-results.json'), {force: true});
const mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.mp3': 'audio/mpeg'};
let server, browser;
const results = [];
try {
  if (!values.file) {
    server = http.createServer(async (req, res) => {
      try {
        const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
        const file = await fs.realpath(path.resolve(root, '.' + pathname));
        if (!file.startsWith(root + path.sep) || !(await fs.stat(file)).isFile()) {
          res.writeHead(403); res.end(); return;
        }
        res.writeHead(200, {'Content-Type': mime[path.extname(file)] ?? 'application/octet-stream'});
        res.end(await fs.readFile(file));
      } catch { res.writeHead(404); res.end(); }
    });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  }
  const base = values.file ? null : `http://127.0.0.1:${server.address().port}/`;
  browser = await chromium.launch({headless: true, ...(process.env.ADT_CHROME ? {executablePath: process.env.ADT_CHROME} : {})});
  for (let languageIndex = 0; languageIndex < languages.length; languageIndex++) {
    const language = languages[languageIndex];
    const catalog = JSON.parse(await fs.readFile(path.join(root, 'content/i18n', language, 'texts.json'), 'utf8'));
    const context = await browser.newContext();
    await context.addInitScript(({language, storage}) => {
      const value = storage === 'json' ? JSON.stringify(language) : language;
      localStorage.setItem('currentLanguage', value);
      if (location.protocol !== 'file:') document.cookie = 'currentLanguage=' + encodeURIComponent(value) + '; path=/';
    }, {language, storage: values['language-storage']});
    const page = await context.newPage();
    for (const width of widths) {
      await page.setViewportSize({width, height: 1000});
      for (let index = 0; index < spine.length; index++) {
        const entry = spine[index], errors = [];
        const row = {section: entry.section_id, href: entry.href, requestedLanguage: language,
          languageSelectionVerified: false, width, protocol: values.file ? 'file' : 'http'};
        const onError = e => errors.push(e.message);
        page.on('pageerror', onError);
        try {
          const target = await fs.realpath(path.resolve(root, entry.href));
          if (!target.startsWith(root + path.sep)) throw new Error('Section path escapes ADT.');
          const url = values.file ? pathToFileURL(target).href : new URL(entry.href, base).href;
          await page.goto(url, {waitUntil: 'load', timeout: 30000});
          await page.locator('#content').waitFor({state: 'visible', timeout: 15000});
          await page.evaluate(() => document.fonts.ready);
          await page.waitForFunction(() => [...document.querySelectorAll('#content img')].every(i => i.complete), null, {timeout: 5000}).catch(() => {});
          // Allow runtime-localized image/catalog updates after document load.
          await page.waitForTimeout(200);
          Object.assign(row, await page.evaluate(() => {
            const root = document.querySelector('#content');
            return {documentLanguage: document.documentElement.lang,
              overflow: document.documentElement.scrollWidth > innerWidth + 2,
              missingImages: [...root.querySelectorAll('img')].filter(i => !i.complete || !i.naturalWidth).map(i => i.getAttribute('src')),
              headings: [...root.querySelectorAll('h1,h2,h3')].map(e => ({tag: e.tagName, text: e.innerText})),
              text: root.innerText};
          }));
          const languageEvidence = await page.evaluate(({language, catalog}) => {
            const clean = value => {
              const fragment = new DOMParser().parseFromString(String(value), 'text/html');
              return fragment.body.textContent.replace(/\s+/g, ' ').trim();
            };
            const samples = [...document.querySelectorAll('#content [data-id]')]
              .filter(el => el.tagName !== 'IMG' && !el.querySelector('[data-id]') &&
                typeof catalog[el.dataset.id] === 'string' && clean(catalog[el.dataset.id]))
              .slice(0, 5).map(el => ({id: el.dataset.id, matches: clean(el.textContent) === clean(catalog[el.dataset.id])}));
            return {languageSelectionVerified: document.documentElement.lang.replaceAll('_', '-').toLowerCase() === language.replaceAll('_', '-').toLowerCase() &&
              samples.length > 0 && samples.every(s => s.matches), languageSelectionSamples: samples};
          }, {language, catalog});
          Object.assign(row, languageEvidence);
          if (width === narrowest) {
            await page.addScriptTag({path: axePath});
            row.accessibility = await page.evaluate(async () => {
              const result = await window.axe.run(document.querySelector('#content'), {
                runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']},
              });
              const compact = items => items.map(v => ({id: v.id, impact: v.impact, help: v.help,
                nodes: v.nodes.map(n => ({target: n.target, summary: n.failureSummary}))}));
              return {violations: compact(result.violations), incomplete: compact(result.incomplete), passes: result.passes.length};
            });
          }
          row.screenshot = `${String(index + 1).padStart(4, '0')}-lang${languageIndex + 1}-${width}.png`;
          await page.screenshot({path: path.join(out, row.screenshot), fullPage: true});
        } catch (error) { row.failure = error.message; }
        finally { row.errors = errors; page.off('pageerror', onError); }
        results.push(row);
        await fs.appendFile(journal, JSON.stringify(row) + '\n');
      }
      console.log(`Captured ${spine.length} sections, ${language}, ${width}px.`);
    }
    await context.close();
  }
  const failed = results.filter(r => r.failure || !r.languageSelectionVerified || r.overflow || r.missingImages?.length || r.errors.length || r.accessibility?.violations.length);
  const incomplete = results.filter(r => r.accessibility?.incomplete.length);
  console.log(JSON.stringify({captures: results.length, capturesWithFailures: failed.length,
    capturesWithInconclusiveAccessibility: incomplete.length,
    limitations: 'Language verification samples up to five catalog bindings per capture; full language correctness, activity behavior, source fidelity and manual accessibility remain separate checks.'}));
  if (failed.length) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  await fs.writeFile(path.join(out, 'browser-results.json'), JSON.stringify(results, null, 2) + '\n');
}
