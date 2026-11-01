#!/usr/bin/env node
// Consistency check for a packaged ADT web folder. Read-only, no dependencies.
// Usage: node check-bundle.mjs <path-to-adt-folder> [--verbose]
// Exit code 1 when any ERROR is reported.
import fs from "node:fs"
import path from "node:path"

const adtDir = path.resolve(process.argv[2] ?? ".")
const verbose = process.argv.includes("--verbose")
const counts = { ERROR: 0, WARN: 0, INFO: 0 }
const report = (level, where, msg) => {
  counts[level]++
  if (level !== "INFO" || verbose) console.log(`${level.padEnd(5)} ${where}: ${msg}`)
}
const exists = (rel) => fs.existsSync(path.join(adtDir, rel))
const readText = (rel) => fs.readFileSync(path.join(adtDir, rel), "utf-8")
const readJson = (rel) => {
  if (!exists(rel)) return null
  try { return JSON.parse(readText(rel)) } catch (err) {
    report("ERROR", rel, `invalid JSON: ${err.message}`)
    return null
  }
}

// ---------------------------------------------------------------- tiny HTML tree
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"])
const decode = (s) => s
  .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
  .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
  .replace(/&nbsp;/g, "\u00a0").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
  .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&amp;/g, "&")
function parseAttrs(src) {
  const attrs = {}
  for (const m of src.matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)) {
    attrs[m[1].toLowerCase()] = decode(m[2] ?? m[3] ?? m[4] ?? "")
  }
  return attrs
}
function parseHtml(html) {
  const root = { tag: "#root", attrs: {}, children: [], parent: null }
  let cur = root
  const re = /<!--[\s\S]*?-->|<(script|style)\b([^>]*)>([\s\S]*?)<\/\1\s*>|<\/([a-zA-Z][\w:-]*)\s*>|<([a-zA-Z][\w:-]*)((?:"[^"]*"|'[^']*'|[^'">])*)>|([^<]+)/g
  for (const m of html.matchAll(re)) {
    if (m[1]) cur.children.push({ tag: m[1].toLowerCase(), attrs: parseAttrs(m[2]), raw: m[3], children: [], parent: cur })
    else if (m[4]) {
      const tag = m[4].toLowerCase()
      let n = cur
      while (n !== root && n.tag !== tag) n = n.parent
      if (n !== root) cur = n.parent
    } else if (m[5]) {
      const el = { tag: m[5].toLowerCase(), attrs: parseAttrs(m[6]), children: [], parent: cur }
      cur.children.push(el)
      if (!VOID.has(el.tag) && !/\/\s*$/.test(m[6])) cur = el
    } else if (m[7]) cur.children.push({ text: decode(m[7]), parent: cur })
  }
  return root
}
const walk = (node, fn) => { for (const c of node.children ?? []) { if (c.tag) { fn(c); walk(c, fn) } } }
const find = (node, pred) => { const out = []; walk(node, (el) => { if (pred(el)) out.push(el) }); return out }
const textOf = (node) => (node.text !== undefined ? node.text
  : node.tag === "script" || node.tag === "style" ? "" : (node.children ?? []).map(textOf).join(""))
const norm = (s) => s.replace(/\s+/g, " ").trim()
const hasClass = (el, c) => (el.attrs.class ?? "").split(/\s+/).includes(c)
const within = (el, pred) => { for (let n = el.parent; n; n = n.parent) if (n.tag && pred(n)) return true; return false }

// ---------------------------------------------------------------- manifests
const config = readJson("assets/config.json")
const rawPages = readJson("content/pages.json")
const rawToc = readJson("content/toc.json")
const pages = Array.isArray(rawPages) ? rawPages : []
const toc = Array.isArray(rawToc) ? rawToc : []
if (!pages.length) report("ERROR", "content/pages.json", "missing, invalid or empty navigation spine")
if (!Array.isArray(rawToc)) report("ERROR", "content/toc.json", "missing or invalid table of contents")
if (!config) report("ERROR", "assets/config.json", "missing or unreadable")
const languages = config?.languages?.available ?? []
const sourceLang = config?.languages?.default ?? languages[0]
const catalogs = {}
for (const lang of languages) {
  for (const f of ["texts.json", "speech_texts.json", "audios.json", "videos.json", "images.json", "glossary.json"]) {
    const rel = `content/i18n/${lang}/${f}`
    const data = readJson(rel)
    if (f === "texts.json") {
      if (!data) report("ERROR", rel, "missing")
      catalogs[lang] = data ?? {}
    }
    if (f === "audios.json" && data) {
      for (const [id, file] of Object.entries(data)) {
        if (!exists(`content/i18n/${lang}/audio/${file}`)) report("WARN", rel, `${id} -> missing audio file ${file}`)
      }
    }
  }
}
const tocIds = new Set(pages.map((p) => p.section_id))
for (const t of toc) if (!tocIds.has(t.section_id)) report("WARN", "content/toc.json", `entry ${t.section_id} not in pages.json`)

// ---------------------------------------------------------------- tailwind
const css = exists("content/tailwind_output.css") ? readText("content/tailwind_output.css") : ""
const TW_PREFIX = /^(-?(?:bg|text|font|p[xytrbl]?|m[xytrbl]?|w|h|min-w|min-h|max-w|max-h|gap(?:-[xy])?|space-[xy]|border(?:-[xytrbl])?|rounded(?:-[a-z]+)?|shadow|flex|grid|grid-cols|grid-rows|col-span|row-span|items-(?:start|end|center|baseline|stretch)|justify|self|place|leading|tracking|opacity|z|top|left|right|bottom|inset|translate-[xy]|scale|rotate|order|basis|grow|shrink|object|aspect|ring|outline|underline|decoration|whitespace|break|overflow|float|clear|list|divide|cursor|transition|duration|ease|sr-only|not-sr-only|hidden|block|inline|inline-block|inline-flex|table|absolute|relative|fixed|sticky|container|uppercase|lowercase|capitalize|italic|truncate|mx-auto|adt-(?:h[1-6]|body|caption)))(?:-|$)/
const cssEscape = (c) => c.replace(/([^a-zA-Z0-9_-])/g, "\\$1").replace(/^(-?)(\d)/, (_, d, n) => `${d}\\3${n} `)
const missingClasses = new Map()
const checkClass = (cls, where) => {
  const base = cls.split(":").pop().replace(/^!/, "")
  if (!TW_PREFIX.test(base)) return
  const esc = "." + cssEscape(cls)
  let i = css.indexOf(esc)
  while (i !== -1) {
    const next = css[i + esc.length]
    if (next === undefined || !/[a-zA-Z0-9_\\-]/.test(next)) return
    i = css.indexOf(esc, i + 1)
  }
  if (!missingClasses.has(cls)) missingClasses.set(cls, where)
}

// ---------------------------------------------------------------- pages
const ACTIVITY_NEEDS_KEY = new Set(["activity_multiple_choice", "activity_quiz", "activity_multi_select", "activity_true_false",
  "activity_underline_text", "activity_matching", "activity_sorting", "activity_fill_in_the_blank", "activity_fill_in_a_table", "activity_ordering"])
const parseInlineJson = (html, name) => {
  const m = html.match(new RegExp(`window\\.${name} = JSON\\.parse\\('((?:[^'\\\\]|\\\\.)*)'\\)`))
  if (!m) return null
  try { return JSON.parse(JSON.parse(`"${m[1].replace(/"/g, '\\"')}"`)) } catch { return "unparseable" }
}

pages.forEach((entry, idx) => {
  const rel = entry.href
  if (!exists(rel)) { report("ERROR", "content/pages.json", `${entry.section_id}: missing file ${rel}`); return }
  const html = readText(rel)
  const doc = parseHtml(html)
  const metas = Object.fromEntries(find(doc, (e) => e.tag === "meta" && e.attrs.name).map((e) => [e.attrs.name, e.attrs.content]))
  if (metas["title-id"] !== entry.section_id) report("ERROR", rel, `meta title-id "${metas["title-id"]}" != pages.json section_id "${entry.section_id}"`)
  if (metas["page-section-id"] !== String(idx + 1)) report("ERROR", rel, `meta page-section-id "${metas["page-section-id"]}" != reading position ${idx + 1}`)
  const contents = find(doc, (e) => e.attrs.id === "content")
  if (contents.length !== 1) report("ERROR", rel, `expected exactly one #content, found ${contents.length}`)
  const content = contents[0] ?? doc
  if (!/base\.bundle\.(local|min)\.js/.test(html)) report("ERROR", rel, "runtime bundle <script> missing")

  // data-id inventory
  const idEls = find(content, (e) => e.attrs["data-id"] !== undefined && !within(e, (n) => n.attrs["data-stepper-root"] !== undefined))
  const seen = new Map()
  for (const el of idEls) {
    const id = el.attrs["data-id"]
    if (!id.trim()) { report("ERROR", rel, `empty data-id on <${el.tag}>`); continue }
    seen.set(id, (seen.get(id) ?? 0) + 1)
    const inSource = Object.hasOwn(catalogs[sourceLang] ?? {}, id)
    if (el.tag === "img") {
      const src = el.attrs.src ?? ""
      if (src && !/^(https?:|data:)/.test(src) && !exists(src.split(/[?#]/)[0])) report("ERROR", rel, `img ${id}: missing file ${src}`)
      if (el.attrs.alt === undefined) report("WARN", rel, `img ${id}: no alt attribute`)
      continue
    }
    if (!inSource) { report("INFO", rel, `data-id ${id} has no ${sourceLang} texts.json entry (container or untranslated)`); continue }
    for (const lang of languages) if (!Object.hasOwn(catalogs[lang], id)) report("WARN", rel, `${id} missing from ${lang}/texts.json`)
    // texts.json is applied as plain text: element children get wiped (except the runtime-preserved shapes)
    const kids = el.children.filter((c) => c.tag && c.tag !== "br" && c.tag !== "math" && c.tag !== "script")
    const preserved = el.attrs["data-segments"] !== undefined ||
      kids.every((k) => hasClass(k, "activity-underline-option") || k.attrs["data-toc-title"] !== undefined ||
        k.attrs["data-toc-leader"] !== undefined || k.attrs["data-toc-page-number"] !== undefined)
    if (kids.length && !preserved) report("WARN", rel, `${id} (<${el.tag}>) has child elements (${kids.map((k) => k.tag).join(",")}) that the runtime will replace with plain catalog text`)
    else if (!kids.length) {
      const htmlText = norm(textOf(el)), cat = norm(catalogs[sourceLang][id])
      if (htmlText !== cat && !/\[\[blank:/.test(cat) && !/<math/.test(cat)) report("INFO", rel, `${id} inline HTML text differs from ${sourceLang}/texts.json (catalog wins at runtime): "${htmlText.slice(0, 60)}" vs "${cat.slice(0, 60)}"`)
    }
  }
  for (const [id, n] of seen) if (n > 1) report("WARN", rel, `data-id ${id} appears ${n} times (each copy is overwritten and read aloud)`)

  // classes
  walk(content, (el) => { for (const c of (el.attrs.class ?? "").split(/\s+/)) if (c) checkClass(c, rel) })

  // activities
  const sections = find(content, (e) => e.tag === "section" && (e.attrs["data-section-type"] ?? "").startsWith("activity_"))
  const correct = parseInlineJson(html, "correctAnswers")
  if (correct === "unparseable") report("ERROR", rel, "window.correctAnswers is not valid JSON")
  for (const sec of sections) {
    const type = sec.attrs["data-section-type"]
    const where = `${rel} [${type}]`
    if (sec.attrs["data-activity-variant"] === "stepper") {
      const payload = find(sec, (e) => e.tag === "script" && e.attrs["data-editable-activity"] !== undefined)[0]
      try { JSON.parse(payload?.raw ?? "") } catch { report("ERROR", where, "stepper JSON payload missing or invalid") }
      continue
    }
    if (type.startsWith("activity_custom")) {
      if (!/adtRegisterCustomActivity/.test(find(sec, (e) => e.tag === "script").map((s) => s.raw).join("")))
        report("ERROR", where, "custom activity has no inline script calling window.adtRegisterCustomActivity (Submit will do nothing)")
      if (!html.includes("__adtPendingCustomActivities")) report("ERROR", where, "custom-activity buffering stub missing from <head>")
      continue
    }
    const items = new Set(find(sec, (e) => e.attrs["data-activity-item"] !== undefined).map((e) => e.attrs["data-activity-item"]))
    if (type === "activity_fill_in_the_blank") {
      for (const el of find(sec, (e) => e.attrs["data-id"] !== undefined)) {
        const t = catalogs[sourceLang]?.[el.attrs["data-id"]] ?? textOf(el)
        for (const m of t.matchAll(/\[\[blank:(item-\d+)/g)) {
          items.add(m[1])
          if (!within(el, (n) => hasClass(n, "fitb-sentence")) && !hasClass(el, "fitb-sentence")) report("ERROR", where, `${m[1]} marker is not inside a .fitb-sentence element (will render as literal text)`)
        }
      }
    }
    if (type === "activity_open_ended_answer") {
      if (!find(sec, (e) => e.tag === "input" || e.tag === "textarea").length) report("ERROR", where, "no <input>/<textarea>")
      continue
    }
    if (!items.size) { report("ERROR", where, "no data-activity-item elements"); continue }
    if (type === "activity_multiple_choice" || type === "activity_multi_select" || type === "activity_quiz") {
      const kind = type === "activity_multi_select" ? "checkbox" : "radio"
      for (const input of find(sec, (e) => e.tag === "input" && e.attrs["data-activity-item"] !== undefined)) {
        if (input.attrs.type !== kind) report("ERROR", where, `${input.attrs["data-activity-item"]} input type="${input.attrs.type}" (expected ${kind})`)
        if (!within(input, (n) => hasClass(n, "activity-option"))) report("ERROR", where, `${input.attrs["data-activity-item"]} is not inside a .activity-option label (not clickable)`)
      }
    }
    let key = null
    if (sec.attrs["data-correct-answers"]) { try { key = JSON.parse(sec.attrs["data-correct-answers"]) } catch { report("ERROR", where, "data-correct-answers is not valid JSON") } }
    if (!key && correct && correct !== "unparseable") key = correct
    if (type === "activity_ordering" && !key && sec.attrs["data-correct-order"]) key = Object.fromEntries(sec.attrs["data-correct-order"].split(",").map((v, i) => [v.trim(), i + 1]))
    if (!key) { if (ACTIVITY_NEEDS_KEY.has(type)) report("ERROR", where, "no answer key (window.correctAnswers / data-correct-answers / data-correct-order)"); continue }
    for (const id of items) if (!Object.hasOwn(key, id)) report("ERROR", where, `${id} has no answer in the key`)
    for (const id of Object.keys(key)) if (sections.length === 1 && !items.has(id)) report("WARN", where, `answer key has ${id} but no element carries it`)
    if (type === "activity_matching") {
      const slots = new Set(find(sec, (e) => e.attrs.id?.startsWith("dropzone-")).map((e) => e.attrs.id))
      for (const [id, slot] of Object.entries(key)) if (items.has(id) && !slots.has(String(slot))) report("ERROR", where, `${id} -> ${slot} but no element id="${slot}"`)
    }
    if (type === "activity_sorting") {
      const cats = new Set(find(sec, (e) => e.attrs["data-activity-category"] !== undefined).map((e) => e.attrs["data-activity-category"]))
      for (const [id, cat] of Object.entries(key)) if (items.has(id) && !cats.has(String(cat))) report("ERROR", where, `${id} -> ${cat} but no data-activity-category="${cat}"`)
    }
    if (type === "activity_multiple_choice") {
      const groups = new Map()
      for (const input of find(sec, (e) => e.tag === "input" && e.attrs.type === "radio")) {
        const g = input.attrs.name ?? ""
        groups.set(g, (groups.get(g) ?? 0) + (key[input.attrs["data-activity-item"]] === true ? 1 : 0))
      }
      for (const [g, n] of groups) if (n !== 1) report("WARN", where, `radio group "${g}" has ${n} correct options`)
    }
  }
})

for (const [cls, where] of missingClasses) report("WARN", where, `class "${cls}" has no rule in content/tailwind_output.css (no effect unless CSS is rebuilt)`)

// ---------------------------------------------------------------- stale offline snapshot
if (exists("assets/offline-preloader.js")) {
  const js = readText("assets/offline-preloader.js")
  const m = js.match(/var INLINE = (\{[\s\S]*?\});\n {2}var BASE_DIR/)
  let inline = null
  try { inline = m ? JSON.parse(m[1]) : null } catch { /* reported below */ }
  if (!inline) report("ERROR", "assets/offline-preloader.js", "could not read the inline snapshot")
  else {
    const stale = []
    for (const [key, value] of Object.entries(inline)) {
      const rel = key.replace(/^\.\//, "")
      if (!exists(rel)) { stale.push(`${rel} (deleted)`); continue }
      const disk = readText(rel)
      if (rel.endsWith(".json")) { try { if (JSON.stringify(JSON.parse(disk)) !== JSON.stringify(value)) stale.push(rel) } catch { stale.push(rel) } }
      else if (disk !== value) stale.push(rel)
    }
    for (const name of fs.readdirSync(adtDir)) if (name.endsWith(".html") && !Object.hasOwn(inline, `./${name}`)) stale.push(`${name} (new)`)
    if (stale.length) report("ERROR", "assets/offline-preloader.js", `snapshot is stale for ${stale.length} file(s): ${stale.slice(0, 8).join(", ")}${stale.length > 8 ? ", …" : ""} — run regen-preloader.mjs`)
  }
}

console.log(`\n${counts.ERROR} error(s), ${counts.WARN} warning(s), ${counts.INFO} info${verbose ? "" : " (use --verbose to list info)"}`)
process.exitCode = counts.ERROR ? 1 : 0
