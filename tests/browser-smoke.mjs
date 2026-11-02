// Exercise the shipped capture helper in a clean synthetic book in both languages.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'adt-browser-smoke-'));
try {
  const book = path.join(temporary, 'book'), out = path.join(temporary, 'evidence');
  await fs.mkdir(path.join(book, 'content'), {recursive: true});
  await fs.mkdir(path.join(book, 'assets'), {recursive: true});
  await fs.writeFile(path.join(book, 'assets/config.json'), JSON.stringify({languages: {available: ['en', 'sq'], default: 'en'}}));
  await fs.writeFile(path.join(book, 'content/pages.json'), JSON.stringify([{section_id: 'lesson', href: 'lesson.html'}]));
  for (const language of ['en', 'sq']) {
    await fs.mkdir(path.join(book, 'content/i18n', language), {recursive: true});
    await fs.writeFile(path.join(book, 'content/i18n', language, 'texts.json'), JSON.stringify({greeting: language === 'sq' ? 'Përshëndetje' : 'Hello'}));
  }
  await fs.writeFile(path.join(book, 'lesson.html'), `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fixture</title></head><body>
    <main id="content"><h1>Test lesson</h1><p id="greeting" data-id="greeting">Hello</p></main>
    <script>var language=JSON.parse(localStorage.getItem('currentLanguage'));document.documentElement.lang=language;document.getElementById('greeting').textContent=language==='sq'?'Përshëndetje':'Hello';</script>
    </body></html>`);
  for (const file of [false, true]) {
    const destination = out + (file ? '-file' : '-http');
    const code = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [path.join(root, 'plugins/adt-repair/skills/adt-pdf-restyle/scripts/browser-audit.mjs'),
        '--adt', book, '--out', destination, '--widths', '375,320', ...(file ? ['--file'] : [])], {stdio: 'inherit'});
      child.on('error', reject); child.on('exit', resolve);
    });
    assert.equal(code, 0);
    const rows = JSON.parse(await fs.readFile(path.join(destination, 'browser-results.json'), 'utf8'));
    const journal = (await fs.readFile(path.join(destination, 'browser-results.jsonl'), 'utf8'))
      .trim().split('\n').map(line => JSON.parse(line));
    assert.deepEqual(journal, rows);
    assert.equal(rows.length, 4);
    assert.ok(rows.filter(r => r.requestedLanguage === 'sq').every(r => r.text.includes('Përshëndetje')));
    assert.ok(rows.every(r => r.screenshot && !r.failure));
    assert.ok(rows.every(r => r.languageSelectionVerified === true));
  }
  console.log('HTTP/offline captures and both requested language preferences passed on the synthetic fixture.');
} finally { await fs.rm(temporary, {recursive: true, force: true}); }
