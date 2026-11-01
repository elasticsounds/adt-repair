#!/usr/bin/env node
// Update only the existing INLINE data payload; preserve the bundle's loader code.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

export function regenerate(root) {
  const file = path.join(root, 'assets/offline-preloader.js');
  const original = fs.readFileSync(file, 'utf8');
  const marker = /\bvar INLINE\s*=\s*/g;
  const match = marker.exec(original);
  if (!match) throw new Error('Unsupported preloader: no var INLINE payload. Use this bundle’s packager.');
  const start = match.index + match[0].length;
  let depth = 0, quoted = false, escaped = false, end = -1;
  if (original[start] !== '{') throw new Error('Expected an object INLINE payload.');
  for (let i = start; i < original.length; i++) {
    const c = original[i];
    if (quoted) {
      if (escaped) escaped = false;
      else if (c === '\\') escaped = true;
      else if (c === '"') quoted = false;
    } else if (c === '"') quoted = true;
    else if (c === '{' || c === '[') depth++;
    else if (c === '}' || c === ']') { if (--depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error('Unterminated INLINE payload.');
  const inline = JSON.parse(original.slice(start, end));
  const relatives = new Set(Object.keys(inline).map(k => k.replace(/^\.\//, '')));
  for (const rel of ['assets/config.json', 'content/pages.json', 'content/toc.json', 'content/navigation/nav.html']) {
    if (fs.existsSync(path.join(root, rel))) relatives.add(rel);
  }
  const config = JSON.parse(fs.readFileSync(path.join(root, 'assets/config.json'), 'utf8'));
  for (const lang of config.languages?.available ?? []) {
    for (const file of ['texts.json', 'speech_texts.json', 'audios.json', 'audio_voices.json', 'videos.json', 'images.json', 'glossary.json', 'timecode/timecode_output.json', 'timecode/timecode_voices.json']) {
      const rel = `content/i18n/${lang}/${file}`;
      if (fs.existsSync(path.join(root, rel))) relatives.add(rel);
    }
    const rel = `assets/interface_translations/${lang}/interface_translations.json`;
    if (fs.existsSync(path.join(root, rel))) relatives.add(rel);
  }
  const spine = JSON.parse(fs.readFileSync(path.join(root, 'content/pages.json'), 'utf8'));
  for (const entry of spine) relatives.add(entry.href);
  for (const file of fs.readdirSync(root)) if (file.endsWith('.html')) relatives.add(file);
  const updated = {};
  for (const rel of [...relatives].sort()) {
    const resolved = path.resolve(root, rel);
    if (!resolved.startsWith(path.resolve(root) + path.sep)) throw new Error(`Payload path escapes book: ${rel}`);
    if (!fs.existsSync(resolved)) throw new Error(`Cached file missing: ${rel}. Review removal explicitly.`);
    const data = fs.readFileSync(resolved, 'utf8');
    updated[`./${rel}`] = rel.endsWith('.json') ? JSON.parse(data) : data;
  }
  const next = original.slice(0, start) + JSON.stringify(updated) + original.slice(end);
  fs.writeFileSync(file, next);
  return Object.keys(updated).length;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (!process.argv[2]) throw new Error('Usage: node regen-preloader.mjs ADT_FOLDER');
    console.log(`Updated ${regenerate(path.resolve(process.argv[2]))} embedded files; loader code preserved.`);
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
