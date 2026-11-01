# ADT Web Bundle: Architecture Reference for Cleanup Agents

This file explains how a packaged **ADT (Accessible Digital Textbook)** web folder is built and
how it behaves at runtime. It is written for an agent that gets an exported `adt/` folder plus the
original PDF and has to fix the ADT so it matches the PDF.

It covers the files on disk, the ID system, how the reader runtime changes the page after load,
the exact HTML contract that turns a section into an interactive activity, and the traps that make
an edit silently not show up.

Everything here was checked against the ADT Studio source (`packages/pipeline/src/packaging/web.ts`,
`apps/adt-runtime/src/**`, `prompts/activity_*.liquid`) and against real exported bundles.

Treat this reference as observed Studio integration patterns, not a promise about every export version. Read the actual bundle and its instructions. When an older generated description disagrees with observed runtime behavior, document the discrepancy and verify the relevant contract before changing it.

---

## 0. The rules that matter most

1. **`texts.json` wins over the HTML.** At boot the runtime takes every key in
   `content/i18n/<lang>/texts.json` and **replaces the content of every element with a matching
   `data-id`** with that string, as **plain text**. A fix made only in the HTML is overwritten the
   moment the page loads. Fix the catalog, then mirror the same text into the HTML.
2. **Refresh embedded offline data after changes to embedded HTML or JSON.** At export time this file inlines a
   snapshot of **every page HTML and every JSON catalog**, and it patches `window.fetch` to serve
   those snapshots. The patch applies on `file://` **and** on `http(s)://`. Until you regenerate it,
   your edits stay invisible to the runtime (stale text, stale answers, stale pages during in-app
   navigation). Use the bundled loader-preserving helper or the bundle’s own packager.
3. **An activity is a markup contract, not a script include.** A page becomes interactive because
   it contains `<section data-section-type="activity_<type>" …>` plus the classes and attributes that
   type requires, plus an answer key. All activity code already lives in `assets/base.bundle.local.js`.
   Every initializer runs on every page and looks for its own selector. Nothing needs to be added to
   `<head>`. The one exception is custom activities (§6.4).
4. **Never rename, renumber, or reuse an ID.** `data-id`s key the text, translations, audio,
   timings, and glossary. Section IDs key the file names and the reading order. Any new ID must be
   unique within the book.
5. **Put `data-id` on the leaf element that holds the text,** never on a wrapper that also holds
   icons, badges, or nested markup. Anything inside a `data-id` element is wiped and replaced with
   plain text. Two narrow exceptions exist: underline-activity word spans and TOC row spans (§5.2).
6. **DOM order inside `#content` is the reading order.** Read-aloud plays `[data-id]` elements in
   document order, and screen readers follow the same order. Fix reading order by reordering the DOM,
   not with CSS `order` or absolute positioning.
7. **A Tailwind class only works if it is already compiled** into `content/tailwind_output.css`
   (§9). A new utility class that is not in that file has no effect.
8. **The PDF is the reference for the source language only.** Some PDF content is **left out on
   purpose**: running headers, footers, page numbers, watermarks, and the back cover, credits, and
   inside-cover sections. Quizzes (`qzNNN.html`), glossary entries, and Easy Read text are
   **generated additions** that do not exist in the PDF. Their absence from the PDF alone is not a defect; review omissions against the job scope.
9. **Do not edit compiled or vendored files** (§14).
10. **A re-export from ADT Studio deletes `adt/`.** Packaging runs `rm -rf adt/` and rebuilds it from
    the book database. Keep a change log of every fix (file, ID, before, after, reason) so the fixes
    can be carried back into Studio.

---

## 1. What an ADT bundle is

An ADT is a **static, offline-capable, multi-page website**:

- **One HTML file per section.** A PDF page can split into several sections, and quizzes get their
  own file. Each file is a complete document that can be opened on its own.
- **Content = HTML structure + per-language JSON catalogs.** The HTML carries layout and stable
  `data-id` hooks. The catalogs carry the strings, audio file names, word timings, image variants,
  and glossary for each language.
- **One shared React runtime** (`assets/base.bundle.local.js`) runs on every page. It mounts the
  reader chrome (dock, navigation, TOC, settings, read-aloud, glossary, language switcher) into two
  empty `<div>`s. It applies the catalog for the current language to the DOM, and it starts every
  activity it finds.
- **No server logic.** It works from `file://` (double-clicking `index.html`), from any static HTTP
  server, and inside SCORM 1.2 LMSs (`imsmanifest.xml` + `assets/scorm.js`).

---

## 2. Directory layout

```
adt/
├── index.html                    # Redirect stub to the first page of the reading order (not content)
├── pg001_sec001.html             # One file per section, named by its stable section id
├── pg003_sec002.html             # A second section from PDF page 3
├── pg004005_sec001.html          # A two-page spread (PDF pages 4+5 merged)
├── qz001.html                    # Generated comprehension quiz (not in the PDF)
├── cover.png                     # Cover image (when a cover page was detected)
├── imsmanifest.xml               # SCORM 1.2 manifest; lists every page file
├── AGENTS.md                     # Generated per-book notes (partly stale, see the top of this file)
├── images/                       # Every image referenced by page HTML (plus translated variants)
│   ├── pg013_im011.jpg
│   └── pg013_im011_tr_fr.png     # Image variant for language fr (see images.json)
├── content/
│   ├── pages.json                # READING ORDER: the navigation spine
│   ├── toc.json                  # Table of contents (hierarchical, with levels)
│   ├── tailwind_output.css       # Compiled CSS (Tailwind + book typography). Classes must exist here
│   ├── navigation/nav.html       # Legacy nav fragment (static)
│   └── i18n/<lang>/              # One directory per output language
│       ├── texts.json            # id → display string (THE text source of truth)
│       ├── speech_texts.json     # id → exact wording sent to TTS (may differ from texts.json)
│       ├── audios.json           # id → mp3 filename (read-aloud), primary voice
│       ├── audio_voices.json     # optional: primary/secondary narrator voices
│       ├── audio/                # mp3 files
│       ├── timecode/timecode_output.json   # word timings for word-by-word highlighting
│       ├── timecode/timecode_voices.json   # optional, per-voice timings
│       ├── images.json           # imageId → localized image filename (translated images)
│       ├── videos.json           # sectionId → sign-language video filename
│       ├── video/                # sign-language videos (sl_<sectionId>.mp4)
│       ├── glossary.json         # word → {word, definition, variations, emoji, id, image?, video?}
│       └── freshness.json        # export disclosure for Studio; NOT read by the reader runtime
└── assets/
    ├── config.json               # Title, languages, feature flags, default settings
    ├── base.bundle.local.js      # The reader runtime (IIFE). DO NOT EDIT
    ├── base.bundle.min.js(.map)  # ESM build of the same runtime. DO NOT EDIT
    ├── activities.bundle.local.js# Activities-only runtime used by WebPub/EPUB exports. DO NOT EDIT
    ├── offline-preloader.js      # GENERATED snapshot of all pages + JSON. REGENERATE after edits
    ├── scorm.js                  # GENERATED SCORM adapter (embeds the list of activity ids)
    ├── auto-fit.js               # Fixed-layout text auto-fit helper
    ├── fonts.css, fonts/         # Bundled fonts
    ├── tailwind_css.css          # Tailwind INPUT file (only for rebuilding CSS)
    ├── libs/fontawesome/         # Icon font (classes like "fas fa-pen-to-square")
    ├── sounds/                   # UI feedback sounds (correct/incorrect)
    ├── symbols/, favicon_io/
    └── interface_translations/<lang>/interface_translations.json   # Reader chrome strings
```

If you receive the whole book directory (the parent of `adt/`), `images/pgNNN_page.png` holds
full-page renders of each PDF page. Those are useful as a visual reference, but they are a pipeline
artifact and not part of the reader.

---

## 3. The ID system

Every piece of content has a stable ID. The same ID connects the HTML (`data-id`), `texts.json`,
`speech_texts.json`, `audios.json`, the timecodes, the glossary, and every translation.

| Pattern | Meaning | Example |
|---|---|---|
| `pgNNN` | Page id = **1-based PDF page index** of the imported PDF | `pg013` = PDF page 13 |
| `pgNNNMMM` | Two PDF pages merged as a spread | `pg004005` |
| `pgNNN_secNNN` | Section id = file name = `pages.json` `section_id` = `<meta name="title-id">` | `pg013_sec002` |
| `pgNNN_sN` | **Legacy** section id (older/agent-made custom sections) | `pg008_s2` |
| `pgNNN_nNNNN` | A text leaf (heading, paragraph, label, option…) | `pg013_n0031` |
| `pgNNN_imNNN` | An image; its `texts.json` value is the **alt text / image description** | `pg013_im011` |
| `<sectionId>_ans_<key>` | Translatable activity answer (fill-in-the-blank text answers) | `pg013_sec002_ans_item-3` |
| `activity_gen_<slug>` | Visible text the generator **invented** for an activity (e.g. sorting category names) | `activity_gen_cat_naturales` |
| `qzNNN` | Generated quiz page (file `qzNNN.html`) | `qz004` |
| `qzNNN_que` / `qzNNN_oN` / `qzNNN_oN_exp` | Quiz question / option N / option explanation | `qz004_o2_exp` |
| `glNNN` / `glNNN_def` / `gl_manual_*` | Glossary term / definition / manually added term | `gl007_def` |
| `<id>_easy_read` | Easy Read (simplified) variant of a text id | `pg013_n0031_easy_read` |
| `item-N` | `data-activity-item` value for one answerable control, unique **within its section** | `item-4` |
| `text-N`, `text-pgNNN-N`, `img-N` | Legacy/agent-made ids found in older or custom sections. Treat them as opaque | `text-pg008-30` |

Rules:

- Treat IDs as **opaque and immutable**. Do not parse meaning out of the numbers (they are not
  positions), and do not "tidy" gaps.
- `page_number` in `pages.json` is the **printed** page number detected on the page. It is often
  different from the PDF index and is sometimes missing. Map files to the PDF through the `pgNNN`
  prefix of the section id.
- `<meta name="page-section-id">` is **not** an ID. Despite its name, it is the page's 1-based
  **position** in `pages.json` and drives the "N of M" counter.
- If you must add text that has no ID (a missing heading, for example), mint a new unique ID that
  cannot collide with any existing key in any language's `texts.json`. A clear suffix such as
  `pg013_n9001` or `pg013_fix_001` works, provided it is not already used anywhere. Add it to every
  language (§13.3).

---

## 4. Anatomy of a page file

This is what packaging (`renderPageHtml`) writes for a reflowable content or activity page.
Comments are added here for explanation:

```html
<!DOCTYPE html>
<html lang="es">                                    <!-- source language of the book -->
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Book title</title>                         <!-- runtime replaces with texts[title-id] if present -->
  <meta name="title-id" content="pg013_sec002" />  <!-- IDENTITY: must equal pages.json section_id -->
  <meta name="page-section-id" content="21" />      <!-- 1-based POSITION in pages.json -->
  <link href="./content/tailwind_output.css" rel="stylesheet">
  <link href="./assets/libs/fontawesome/css/all.min.css" rel="stylesheet">
  <link href="./assets/fonts.css" rel="stylesheet">
  <!-- optional: Google Fonts <link>s, a reflowable body-font <style> -->
  <!-- ONLY on custom-activity pages: the adtRegisterCustomActivity buffering stub (§6.4) -->
</head>
<body class="min-h-screen flex items-center justify-center">   <!-- may carry style="background-color:…" -->
  <main class="w-full">
    <h1 class="sr-only" id="page-heading">…</h1>   <!-- only added when the content has no <h1> -->
    <div id="content" class="container … opacity-0">                      <!-- EXACTLY ONE #content -->
      <section data-section-type="activity_fill_in_the_blank"           <!-- drives page behaviour -->
               data-section-id="pg013_sec002" role="group">
        <span data-id="pg013_n0031" class="adt-body block">Completa la guía…</span>
        <img data-id="pg013_im011" src="images/pg013_im011.jpg" alt="…">
        <input id="fitb-1" data-activity-item="item-1" type="text" aria-label="…">
      </section>
    </div>
  </main>

  <!-- Activity answer data (always present; correctAnswers only when the section has answers) -->
  <script type="text/javascript">
    window.activityAnswerTextIds = JSON.parse('{"item-1":"pg013_sec002_ans_item-1"}');
  </script>
  <script type="text/javascript">
    window.correctAnswers = JSON.parse('{"item-1":"Aflojá"}');
  </script>

  <div class="relative z-50" id="interface-container"></div>  <!-- runtime mounts chrome here -->
  <div class="relative z-50" id="nav-container"></div>        <!-- runtime mounts dock + Submit here -->
  <script src="./assets/offline-preloader.js"></script>
  <script src="./assets/scorm.js"></script>
  <script src="./assets/base.bundle.local.js"></script>
</body>
</html>
```

Invariants:

- **Everything the reader should see or hear goes inside the single `<div id="content">`.**
  Read-aloud only scans `#content`, so content outside it is skipped.
- `#content` starts at `opacity-0`. The runtime reveals it after boot, and a fallback timer reveals
  it if boot fails. Do not remove the class just to make screenshots work; wait for the runtime
  instead (§15).
- `<main>` is the unit that in-app navigation swaps, so keep all page content inside `<main>`.
- One `<section data-section-type=… data-section-id=…>` per file is normal. Templated activity types
  expect exactly one activity section per page.
- The inline JSON is wrapped in `JSON.parse('…')`, so single quotes and backslashes inside it are
  escaped. Edit it carefully (read the value, change it, re-serialize it), or move the key to a
  `data-correct-answers` attribute on the section where that type supports one (§6.3).
- Quiz pages (`qzNNN.html`) have their own template: `#content` comes from the quiz markup and
  `section#simple-main[data-section-type="activity_quiz"]` (§6.3).

---

## 5. What the runtime does to the page after load

### 5.1 Boot sequence (`apps/adt-runtime/src/app/lifecycle.ts`)

1. Mount React into `#interface-container` and `#nav-container`.
2. Load `assets/config.json`. Pick the language: the saved preference (`currentLanguage` in
   localStorage or a cookie) if it is in `languages.available`, otherwise `languages.default`.
   `<html lang>` is only used when the config has no default.
3. Load `interface_translations.json` + `texts.json` + `speech_texts.json` + `audios.json` +
   `audio_voices.json` + `videos.json` + `images.json` for that language, plus `pages.json`,
   `toc.json`, `glossary.json`, and the timecodes. **All of these come through `fetch`, which the
   offline preloader intercepts (§7).**
4. `initializePageContent()`:
   - read `<meta title-id>` / `<meta page-section-id>`;
   - mark the page as an **activity page** when `document.querySelector('section[data-section-type^="activity_"]')` matches. That turns on the dock's Submit/Skip controls;
   - **apply the catalog to the DOM** (§5.2), localized images, and glossary highlights;
   - reveal `#content`;
   - run **every** activity initializer in order: stepper, quiz/multiple-choice, multi-select,
     underline, fill-in-the-blank/table, open-ended, true/false, sorting, ordering, matching,
     custom, word-bank.
5. Language switches and Easy Read toggles re-run the catalog application in place, without a reload.

### 5.2 Catalog application: `applyTranslationsToDOM`

For each `key → text` in the merged dictionary (interface strings first, then `texts.json`, with
content keys taking priority):

- for every element with `data-id="key"` inside the document:
  - `<img>` → `alt` is set to `text`, so **alt text lives in `texts.json` under the image id**;
  - inside a stepper root (`[data-stepper-root]`) → skipped;
  - a TOC row (inside `section[data-section-type="table_of_contents"]` with child spans marked
    `data-toc-title` / `data-toc-leader` / `data-toc-page-number`) → those child spans are updated in place;
  - an element whose children are `.activity-underline-option[data-activity-item]` spans → each
    word is rewritten **only if the word count matches**, otherwise the DOM is left alone;
  - fixed-layout paragraphs with `data-segments='[…]'` → the styled runs are rebuilt from that JSON;
  - **anything else → `element.replaceChildren(plain text)`**: `\n` becomes `<br>`, Temml
    `<math>` blocks are kept, and **all other child elements are removed**.
- elements with `data-placeholder-id="key"` that are `<input>`/`<textarea>` get `placeholder=text`.
- `document.title` = `texts[title-id]` when present.
- Then `adt:translations-applied` fires, and fill-in-the-blank turns its `[[blank:item-N]]` markers into `<input>`s.

What follows from this:

- **Catalog values are plain text.** `<b>`, `<br>`, `&nbsp;`, and other markup in `texts.json` shows
  up literally. Use `\n` for a forced line break. Inline emphasis cannot be stored in a catalog
  string; put it on the element (for example `font-bold`) or split the text into separate leaves.
- **A `data-id` element must contain only its text.** `<h1 data-id="x"><i class="fas fa-leaf"></i><span>Title</span></h1>`
  loses its icon at runtime. Move the `data-id` onto the inner `<span>` and leave the icon outside it.
- A `data-id` that is **not** a key in `texts.json` is ignored by this pass. Template group wrappers
  (`<div data-id="…">` around leaves) rely on that. Read-aloud also skips any id with no `audios.json` entry.
- **Duplicate `data-id`s** on one page all get the same text **and are all read aloud.** Each id
  should appear once per page.
- The runtime leaves inline text that differs from the catalog in place until boot, then overwrites
  it. Keep the HTML text identical to the source-language catalog. Crawlers, EPUB/WebPub exporters,
  and no-JS readers see the HTML.

### 5.3 Read-aloud, image descriptions, and highlighting

- The queue is every `[data-id]` element in `#content`, **in DOM order**, that has an `audios.json`
  entry. Images are included only when "describe images" is on.
- Word highlighting uses `timecode_output.json` (per id, word start and end times) and is enabled by
  `config.features.highlight`.
- **Changing a text makes its mp3 and word timings stale.** The cleanup agent normally cannot
  regenerate TTS. Record every id whose display text changed so the audio can be regenerated in
  Studio. Do not point `audios.json` at a different id's audio.
- Excluding something from read-aloud means removing its key from `audios.json` (and its timecode)
  in that language. Removing the `data-id` instead also breaks translation.

### 5.4 Soft navigation

Over HTTP the runtime turns pages **in place**. It `fetch`es the next page file, swaps `<main>`,
the page-scoped `<head>` nodes (title, metas, page `<style>`s and fonts), and the `<body>`
class/style, re-runs the inline scripts (custom-activity scripts, `window.correctAnswers`), and then
runs `initializePageContent()` again. Consequences:

- Page-specific CSS belongs in a `<style>` element in that page's `<head>`, which is swapped
  correctly, or inline in `<main>`.
- The fetched page HTML is served from the **offline preloader snapshot**. A stale snapshot shows
  the old version of a page whenever the reader arrives there by Next/Back or the TOC, even though
  opening the file directly shows the new version.
- `file://` and `?embed=1` use plain full-page navigation.

---

## 6. Activities: how a page becomes interactive

### 6.1 The trigger

A page becomes an activity because it contains:

```html
<section data-section-type="activity_<type>" data-section-id="<sectionId>"> … </section>
```

That one attribute does all of the following:

- **Dock mode.** `isActivityPage` turns on, so the dock shows **Submit** (which becomes **Next**
  after a correct answer) and **Skip**/**Reset** controls. The runtime renders these buttons; the
  page HTML must **not** include its own Submit button.
- **Behaviour.** Each initializer in `base.bundle.local.js` queries its own selector (table below)
  and wires up clicks, drag-and-drop, keyboard support, validation, feedback marks, sounds,
  confetti, and localStorage persistence of typed answers.
- **Feature flag.** `config.features.activities` is `true` when the book has any activity section
  or quiz. If you add the first activity to a book where it is `false`, set it to `true`.
- **SCORM scoring.** `assets/scorm.js` contains an `ALL_ACTIVITY_IDS` list that was collected at
  export time from quiz ids and any `data-area-id` attributes.

No per-page `<script src>` is needed. The only per-page scripts are the **answer-key globals** that
packaging writes after `</main>`:

- `window.correctAnswers`: `{ "<data-activity-item>": <value> }`. What the value means depends on the type (§6.3).
- `window.activityAnswerTextIds`: `{ "<item>": "<sectionId>_ans_<item>" }`. For **text** answers,
  this sends grading to the translated answer in the current language's `texts.json`, so a learner
  reading in French is graded against the French answer. If that translation is missing or blank,
  grading falls back to `window.correctAnswers`.

Classic initializers skip sections marked `data-activity-variant="stepper"` (§6.4). A section whose
type starts with `activity_` but matches no initializer (for example `activity_other`) still turns
on dock mode but has no working controls. That is a defect to fix (§13).

### 6.2 Rules shared by all templated types

- One `<section>` per activity page, carrying both `data-section-type` and `data-section-id`.
- **Every visible string sits in an element with a `data-id`** that exists in `texts.json`. Do not
  leave bare text nodes. Decorative separators you add get `aria-hidden="true"`.
- **Controls never carry `data-id`.** `<input>`, `<textarea>`, and `<select>` are interactive
  additions, not content. They sit **outside** the text's `data-id` element.
- Every answerable control has a **unique, sequential** `data-activity-item="item-N"` (one counter
  per section). True/false is the exception: both radios of one statement share an id.
- Every control has an accessible name (`<label for>` or a specific `aria-label`) and a touch
  target of at least 44px (`min-h-11`).
- Images carry `data-id` = their image id (for alt text and description audio) and `src="images/<file>"`.
- Option markers use digits (`1`, `2`, `3`), not letters, so they stay language-neutral.
- Page container: in a packaged page the section's `#content` div sits directly inside `<main>`
  (for example `<div class="container mx-auto max-w-5xl bg-white rounded-lg px-24 max-lg:px-12 max-sm:px-6 pt-12 pb-12 opacity-0" id="content">`).
  The generator's outer flex wrapper is removed during validation. When you rewrite a section, keep
  the existing `#content` div and its classes, and replace only what is inside it. Never add a second `#content`.

### 6.3 The templated activity types

| `data-section-type` | Required markup (runtime selectors) | Answer key (`window.correctAnswers` unless noted) |
|---|---|---|
| `activity_multiple_choice` | Each option is `label.activity-option` containing `input[type=radio][data-activity-item][name][class=sr-only]`. **One `name` per question** (`question-group-1`, `question-group-2`…). Optional `.option-letter` (digit), `.feedback-container.hidden > .feedback-icon + .feedback-text` | `{"item-1": true, "item-2": false, …}`, with **exactly one `true` per radio group**. Also accepts `data-correct-answers='{…}'` on the section |
| `activity_quiz` (`qzNNN.html` only) | Generated by packaging: `section#simple-main[data-section-type=activity_quiz][data-id=qzNNN][data-correct-answers][data-option-explanations]`, `label.activity-option[data-activity-item=qzNNN_oN][data-explanation][data-explanation-id]`, question `p[data-id=qzNNN_que]`, option text `span[data-id=qzNNN_oN]` | `data-correct-answers` attribute, the `<script type="application/json" id="quiz-correct-answers">` block, **and** `window.correctAnswers`. Keep all three in sync |
| `activity_multi_select` | Same as multiple choice but with `input[type=checkbox]`, and `.option-letter` is usually square | Booleans. A group is correct when the set of checked items equals the set of `true` items |
| `activity_true_false` | One `<fieldset>` per statement. **Two radios that share one `data-activity-item` and one `name`**, with `value="true"` and `value="false"`. A `span.validation-mark.hidden` inside each radio's label. The accessible name comes from the wrapping `<label>` (no `aria-label` on the radios) | `{"item-1": "true", "item-2": "false"}` (**strings**) |
| `activity_fill_in_the_blank` | **Inline blanks:** the text inside a `data-id` element contains `[[blank:item-N]]` or `[[blank:item-N:hint]]`, **in `texts.json` too**, and that element or an ancestor has class **`fitb-sentence`**. The runtime swaps each marker for an `<input>`. **Separate fields:** `<input>`/`<textarea data-activity-item="item-N" data-aria-id="…">` placed next to the label, outside any `data-id`. One counter covers both styles | `{"item-1": "correct text"}`. **`\|` separates accepted alternatives** (`"5\|five"`). `""` means accept any non-empty answer. Translated answers go in `texts.json` as `<sectionId>_ans_item-N` |
| `activity_fill_in_a_table` | A real `<table>` with `<th scope="col">` / `<th scope="row">` (blank corner = `<td aria-hidden="true">`). Every `<input>` has `data-activity-item="item-N"` and a label or `aria-label` | Same as fill-in-the-blank |
| `activity_open_ended_answer` | `<input type="text">` for short answers, `<textarea class="resize-none">` for longer ones, each with a unique `data-aria-id`, **no `data-id`**, no placeholder text. One field per printed answer line or box | **None.** Accepts any non-empty answer that passes the gibberish and profanity filters |
| `activity_underline_text` | Inside the sentence's own `data-id` element, wrap **every** candidate word (or phrase/sentence, matching the answer unit) as `span.activity-underline-option[data-activity-item="item-N"][data-question-group="question-group-N"]`. Punctuation and number markers stay outside the spans. Each span needs visible text, and all spans for one question share one ancestor | Booleans: `true` = should be underlined |
| `activity_matching` | Draggable `.activity-item[data-activity-item][draggable=true][tabindex=0][role=button][aria-label]`, with the text in a `data-id` element. Drop zones are `.dropzone[tabindex=0][role=button][aria-label]`, each containing its `img[data-id]` and **`div.dropzone-slot#dropzone-N[aria-live=polite]`** (no landmark role). One-to-one matching | `{"item-1": "dropzone-3", …}` |
| `activity_sorting` | Cards are `.word-card[data-activity-item][draggable=true][tabindex=0]` (**not** `.activity-item`). The `data-id` goes on the **inner** `span`/`img`, and a card's picture sits **inside** its card. Categories are `.category[data-activity-category="<catId>"]` with a label (`<p>`/`<span>`, not `<hN>`) and an **empty `<ul class="word-list"></ul>`**. Generated category names use `data-id="activity_gen_<slug>"` | `{"<item>": "<catId>", …}` |
| `activity_ordering` | `<ol data-activity-order-list>` whose **direct children** are the cards `[data-activity-item][tabindex=0][draggable=true]`. The runtime adds the up/down controls. Start the list in a shuffled order | `data-correct-order="item-2,item-1,…"` on the section. A `window.correctAnswers` of `{item: rank 1..n}` **takes precedence** when present |

Notes:

- Multiple-choice/multi-select and underline sections can contain **several questions** (one radio
  `name` or one `data-question-group` per question). Each group is graded on its own.
- Fill-in-the-blank and open-ended inputs that have a `data-aria-id` keep their typed values in
  localStorage under `<page-file-name>_<data-aria-id>`. After changing inputs, clear site storage
  before testing.
- `[[blank:…]]` markers must be **inside** the text of a `data-id` element. A marker outside any
  `data-id`, or one with no `.fitb-sentence` ancestor, renders as the literal text `[[blank:item-1]]`.
- Matching has an older form that uses `div[role="region"]` slots instead of `.dropzone-slot`. The
  runtime accepts both; prefer `.dropzone-slot` when rewriting.

### 6.4 Special activity variants

**Custom activities: `activity_custom_<suffix>`** (crossword, word search, drag-drop game…). The
runtime does not know their structure. The section ships **its own inline `<script>`**, inside the
section, which must call:

```js
window.adtRegisterCustomActivity(section, {
  validate() { /* mark items, write a result into an aria-live region, return true|false (or a Promise) */ },
  reset()    { /* restore the initial unanswered state */ },
})
```

- Pages with an `activity_custom*` section get a **buffering stub** in `<head>`:
  `<script>(function(){if(window.adtRegisterCustomActivity)return;var q=(window.__adtPendingCustomActivities=window.__adtPendingCustomActivities||[]);window.adtRegisterCustomActivity=function(section,handlers){q.push({section:section,handlers:handlers})}})();</script>`.
  The section script runs during parsing, before the runtime bundle loads. If the stub is missing,
  the call throws and **Submit stays disabled forever**. Add the stub if you create a custom activity by hand.
- Submit is enabled as soon as the activity registers. `validate()` must return `false` until the
  learner has done something, and must write feedback text into an `aria-live="polite"` element in the section.
- Use `document.currentScript.closest('section')` to find the section, and guard against running twice
  (`if (section.dataset.adtInitialized === 'true') return; section.dataset.adtInitialized = 'true'`),
  because soft navigation re-executes scripts.
- Answers are usually encoded in the markup (`data-correct-items="item-1,item-4"` on targets,
  `data-answer`, …) and read by `validate()`. `window.correctAnswers` may hold a copy.
- The runtime adds `role`/`tabindex` to `[data-activity-target]` and `[data-activity-item]` elements as an accessibility backstop.
- Do not put `$…$` or `\(` inside `<script>` expecting math conversion. Packaging leaves script bodies untouched.

**Step-by-step activities: `data-activity-variant="stepper"`.** These sections hold **no HTML
content**: just
`<script type="application/json" data-editable-activity>{"activity":…,"palette":…}</script><div data-stepper-root></div>`.
The runtime renders the whole activity in React from that JSON. **Do not hand-edit stepper markup.**
If one is wrong, fix the JSON payload carefully (it is an `EditableActivity`: `kind` is
`fill-in-the-blank` | `multiple-choice` | `open-ended` | `underline-text`), or report it for repair in Studio.

**Word bank** (can appear in any section, including mixed content). Chips are
`[data-word-bank-chip="<value>"]` (buttons). Targets are `[data-word-bank-target]` on
`<input>`/`<textarea>`/`<select>`. An optional `[data-word-bank-status]` element receives live
announcements. Clicking or dragging a chip fills the target's value and fires `input`/`change`.
**Grading belongs to the activity that owns the target** (normally fill-in-the-blank), so the targets
still need `data-activity-item` values and answers. Typing directly must keep working.

### 6.5 Recipe: make a static exercise interactive, or repair one

1. Look at the PDF page and decide the **learning mechanic**: pick one answer → multiple choice;
   pick several → multi-select; write a word in a gap → fill-in-the-blank; write freely →
   open-ended; true/false; underline in text; one-to-one match; group into categories → sorting;
   put in sequence → ordering. Classify by the cognitive task, not the physical action ("circle the
   correct word" is multiple choice or underline).
2. Set `data-section-type` on the section. Keep the existing `data-section-id` and the `title-id` meta.
3. Keep **every** existing text `data-id` and its exact text. Restructure around them. Do not drop,
   merge, or duplicate any.
4. Add the controls and attributes the type needs (§6.3), with sequential `item-N` values and no
   `data-id` on controls.
5. Write the **answer key** in the format for that type, derived from the PDF (answer pages, worked
   examples) or the subject matter. Cover every `data-activity-item`. For text answers, add
   `<sectionId>_ans_item-N` entries to each language's `texts.json` and to
   `window.activityAnswerTextIds`.
6. If you introduced new visible text (category names, for example), give it a new unique id
   (`activity_gen_<slug>`) and add it to every language's `texts.json`.
7. Set `config.features.activities = true` if needed. Regenerate the preloader, run the checker
   (Appendix B), then test it in a browser: answer wrong, answer right, Reset.

---

## 7. The offline preloader (why edits seem to do nothing)

`assets/offline-preloader.js` is generated at the end of packaging. It contains one big `INLINE`
object holding the parsed contents of:

`assets/config.json`, `content/pages.json`, `content/toc.json`, `content/navigation/nav.html`, **every
`*.html` in the `adt/` root**, and for each language `interface_translations.json`, `texts.json`,
`speech_texts.json`, `audios.json`, `audio_voices.json`, `videos.json`, `images.json`,
`glossary.json`, `timecode/timecode_output.json`, and `timecode/timecode_voices.json`.

It replaces `window.fetch`. Any request whose path matches an inlined file returns the **snapshot**,
whatever the protocol. Audio, images, and video are not inlined; they always load from disk.

**After editing any of the files listed above, run Appendix A** (`node regen-preloader.mjs adt/`).
It rebuilds the file exactly as packaging would (byte-for-byte identical on an untouched bundle).
The checker (Appendix B) reports a stale snapshot as an ERROR.

---

## 8. Content pages and fixed-layout pages

### 8.1 Reflowable content pages (most books)

- Section types: `front_cover`, `table_of_contents`, `separator`, `foreword`, `boxed_text`,
  `text_only`, `text_and_single_image`, `text_and_images`, `images_only`, `other` (plus `activity_*`).
  `back_cover`, `credits`, and `inside_cover` are **pruned by default** and never exported.
- These pages are produced either by a **template** (`two_column_render`: text column and image
  column side by side on desktop, stacked on mobile) or by an **LLM** prompt (`web_generation_html`).
  Expect varied Tailwind markup.
- Conventions the generator follows, which your fixes should also follow:
  - Headings: `chapter_title` → `<h1 class="adt-h1">`, `section_heading` → `<h2 class="adt-h2">`,
    `subheading` → `<h3 class="adt-h3">`, other headings → `<hN class="adt-hN">`. Packaging promotes
    the first heading on a page to `<h1>`. **Do not put `text-*` size utilities or inline font sizes
    on headings.** Sizing comes from the `adt-*` type scale.
  - Body text uses `adt-body`, captions `adt-caption`, and leaves are mostly `<span>` (block-level only
    for real paragraphs, headings, and list items).
  - Responsive prefixes are **desktop-first**: base classes are the desktop design, `max-lg:` covers
    tablet and down, `max-sm:` covers mobile. Other prefixes (`sm:`, `md:`, `lg:`) may not be compiled.
  - Text that is already legible inside an image is not shown twice. The text leaf is kept as
    `sr-only` so screen readers and read-aloud still get it.
  - Math leaves hold **LaTeX**, which packaging turns into MathML (Temml). In a packaged bundle the
    HTML and `texts.json` already contain `<math>` markup. Keep it; do not retype math as text.
  - TOC rows: `<div data-id="…" class="flex items-baseline w-full"><span data-toc-title>…</span><span data-toc-leader aria-hidden="true" class="flex-1 border-b-2 border-dotted"></span><span data-toc-page-number>…</span></div>`.
- Decorative images: `alt=""`, `role="presentation"`, `aria-hidden="true"`. Because the runtime sets
  `alt` from `texts.json`, also **remove the image id from every `texts.json` and `audios.json`**.
  Otherwise the description comes back at runtime.

### 8.2 Fixed-layout books (`config.fixedLayout: true`)

These are illustrated books where every page reproduces the PDF geometry:

- `<meta name="viewport" content="width=W, height=H">`, `<body style="margin:0;overflow:hidden;…">`,
  and `#content` with `style="position:relative;width:Wpx;height:Hpx;…"` (page coordinates at 2× the
  PDF render scale), optionally `data-fl-reference-width`.
- Each text block is `<p data-id="…" data-segments='[{"text":…,"style":{…}}]' data-adt-fit="1" style="position:absolute;top:…px;left:…px;…">`
  with styled runs inside. **`data-segments` is what the runtime uses to rebuild the runs after a
  text swap.** If you change a text, update `data-segments` so the joined `text` values equal the new
  string, or the runtime falls back to a single run in the first run's style.
- A small inline fit script scales `#content` to the window. Positions are in page pixels, so do
  not convert them to responsive classes.
- Read-aloud order is still DOM order, so reorder the `<p>` elements to match the reading order.

---

## 9. Styling and CSS

- `content/tailwind_output.css` is compiled **just in time** from the classes that were in the
  bundle at export time, with the book's typography (`.adt-h1` to `.adt-h6`, `.adt-body`,
  `.adt-caption`, and MathML resets) appended at the end. A utility that was not used anywhere at
  export time **does not exist** in it.
- When restyling, in order of preference:
  1. Reuse classes that already exist in `tailwind_output.css`. Search for the escaped selector,
     for example `.max-lg\:flex-col` or `.bg-amber-50`. The checker lists classes it cannot find.
  2. For one-off values, use an inline `style="…"`.
  3. For a rule needed on many pages, append a clearly marked block of plain CSS to the **end** of
     `content/tailwind_output.css`. Unlayered rules override Tailwind's layered utilities, so keep the
     selectors narrow. For a single page, a `<style>` in that page's `<head>` also works and is
     swapped correctly during soft navigation.
  4. Rebuilding Tailwind needs Node with `tailwindcss` v4, `@tailwindcss/postcss`/CLI, and
     `tw-animate-css`. The input is `assets/tailwind_css.css`; `@source` must point at `adt/**/*.html`
     and `adt/**/*.js`. Re-append the typography block that was at the end of the old file. Only do
     this if you have to.
- Icons: Font Awesome 6 (`<i class="fas fa-…" aria-hidden="true"></i>`). Keep icons **outside**
  `data-id` elements.
- The `<body>` background comes from a `data-background-color` attribute in the section content at
  export time. After export it is an inline `style` on `<body>`.

---

## 10. Languages, audio, glossary, Easy Read, and sign language

- **Languages.** `config.languages.available` lists one `content/i18n/<lang>/` folder per language.
  `<html lang>` on the pages is the **source language**, the one that should match the PDF. Other
  languages are translations of the source catalog under the same ids.
  - When you fix a source text, the translations of that id are now stale. Do not leave them silently
    mismatched: update them only if you can translate faithfully (and say so in the log), otherwise
    list the ids that need re-translation. Never delete keys from non-source languages.
  - When you add an id, add it to **every** language's `texts.json`. A language that lacks it keeps
    whatever text is in the HTML (the source language) when the reader switches.
- **Localized images.** `images.json` maps `imageId → images/<variant file>` per language. The
  runtime swaps `<img data-id>` `src` accordingly.
- **Audio.** See §5.3. `speech_texts.json` holds the exact wording that was synthesized (math read
  as words, for example). It does not change what is displayed.
- **Glossary.** `glossary.json` is keyed by the displayed word:
  `{ "word": { word, definition, variations[], emoji, id: "glNNN", image?, video? } }`. Its text is
  also in `texts.json` (`glNNN`, `glNNN_def`). At runtime, terms are highlighted in body text except
  inside headings, `.activity-text`, and `[data-activity-item]`. No markup is needed in the HTML.
- **Easy Read.** `<id>_easy_read` keys in `texts.json`. When the reader turns Easy Read on, these
  replace paragraph text, except headings, word cards, activity items, `.activity-text`, and nav.
- **Sign language.** `videos.json` maps `sectionId → video/sl_<sectionId>.mp4` and is shown
  picture-in-picture for that page. `config.features.signLanguage` turns it on.

---

## 11. Manifest reference

| File | Shape | Edit when |
|---|---|---|
| `content/pages.json` | `[{section_id, href, page_number?}]` in reading order. Quizzes sit after their anchor page | Adding, removing, or reordering pages. Then renumber `<meta page-section-id>` (1-based position) in **every** affected page file, and update `imsmanifest.xml` |
| `content/toc.json` | `[{section_id, href, title, chapter_id, level}]`. `chapter_id` is the heading's text id | Headings or chapter titles change. Keep `title` equal to the heading's text |
| `assets/config.json` | `{title, bundleVersion, languages{available, default}, features{…}, analytics, defaultSettings?, lockedSettings?, fixedLayout?}` | Turning features on or off to match the content (`activities`, `glossary`, `readAloud`, `highlight`, `easyRead`, `signLanguage`) |
| `index.html` | Redirect stub to `pages[0].href` | The first page changes. Older bundles had a real page called `index.html` listed in `pages.json`; leave that as it is |
| `imsmanifest.xml` | SCORM file list | Pages are added or removed |
| `assets/scorm.js` | Generated, embeds `ALL_ACTIVITY_IDS` | Activities are added or removed and SCORM completion matters. Update the array, nothing else |
| `assets/offline-preloader.js` | Generated snapshot | **Every time any page or JSON changes** (Appendix A) |

`bundleVersion` is used as a `?v=` cache-buster on fetches. Changing it is optional; regenerating
the preloader is not.

---

## 12. Mapping the bundle back to the PDF

- `pgNNN` in a section id = PDF page NNN (1-based) of the imported PDF. `pgNNNMMM` = a spread of
  pages NNN and MMM. If the PDF you were given is a different cut, confirm the offset on one page first.
- One PDF page can become **several** section files (`pg003_sec001`, `pg003_sec002`). A section can
  also include content carried over from the **next** PDF page (an exercise that continues across a
  page break).
- Render PDF pages for visual comparison with whatever is available, for example
  `pdftoppm -r 110 -png -f 13 -l 13 book.pdf out/pg`, PyMuPDF (`page.get_pixmap(dpi=110)`), or
  `mutool draw`. Extract text with `pdftotext -f 13 -l 13 -layout book.pdf -`.
- Intentionally absent from the ADT: running headers and footers, page numbers, watermarks or
  stamps, and the back cover, credits, and inside-cover sections (§0 rule 8). Present in the ADT but
  not in the PDF: quizzes, glossary, Easy Read text, image descriptions (alt text), and
  `activity_gen_*` labels.
- `page_number` (the printed number) is useful for checking that the TOC matches what is printed.

---

## 13. Cleanup playbook

### 13.1 Typical defects and fixes

| Defect seen against the PDF | Fix |
|---|---|
| **Wrong text** (OCR error, missing accent, merged words like `centroun hueco`, truncated sentence) | Edit the value in the **source language** `texts.json`, mirror it in the HTML element, and log the id for re-translation and TTS |
| **Text missing** (a whole paragraph or label is absent) | Find out whether it was intentionally pruned (header, footer, page number?). If it is real content, add an element in the right DOM position with a **new unique id**, add it to every language's `texts.json`, and log it for TTS |
| **Text duplicated** (visible in an image and again as text) | Keep the image and give the text leaf `class="sr-only"` (do not delete it) |
| **Wrong reading order** | Reorder the elements inside `#content` (moving whole blocks). Check the desktop and mobile layouts still look right |
| **Wrong heading level / hierarchy** | Change the tag and the matching `adt-hN` class together. Keep one `<h1>` per page. Update `toc.json` `title`/`level` if the entry is listed there |
| **Missing, wrong, or hallucinated alt text** | Edit `texts.json[<imageId>]` in every language. To make an image decorative, see §8.1 |
| **Wrong or missing image** (wrong crop, image from another page) | Point `src` at the correct file in `images/` and keep the `data-id`. Do not invent image ids; if the right image is not in `images/`, report it |
| **Exercise rendered as static text or a screenshot** | Convert it to the right activity type (§6.5) |
| **Activity does nothing / Submit stays disabled** | Run the checker. Usual causes: missing `.activity-option`, inputs without `data-activity-item`, an answer key missing items, a `[[blank]]` marker outside a `data-id` or `.fitb-sentence`, a custom script not registering, the head stub missing, or a stale preloader |
| **Wrong answer key** | Fix `window.correctAnswers` (and `data-correct-answers` / `data-correct-order`, plus the quiz JSON block if it is a quiz) and the translated `_ans_` texts |
| **Wrong activity type** (multiple choice where several answers are correct; sorting where it is really one-to-one matching) | Rebuild the section as the correct type (§6.3), keeping every text id |
| **Fields in the wrong place** (inputs collected at the bottom, not at each blank) | Move each control next to its prompt, matching the PDF |
| **Icons or badges vanish after load** | A `data-id` is on a wrapper. Move it onto the text leaf (§5.2) |
| **Layout broken on mobile** (overflow, clipping at 375px) | Use existing `max-lg:`/`max-sm:` classes, `flex-wrap`, `min-w-0`, `w-full`, or inline styles (§9) |
| **TOC titles or page numbers do not match the printed TOC** | Fix the TOC page texts in `texts.json` and the `toc.json` titles |

### 13.2 Things to leave alone unless explicitly asked

Quiz content and the existence of quizzes, glossary selection, Easy Read text, the translations' wording
beyond fixing obvious drift, audio files, IDs, file names, `bundleVersion`, and fonts.

### 13.3 Editing checklist for one text id

1. Source `texts.json` value, then the HTML element text.
2. If the element is an `<img>`, the change is alt text; no HTML text change is needed.
3. Each other language: update the translation or log it as stale.
4. If `audios.json` has the id: log it as needing TTS (`speech_texts.json` + mp3 + timecode).
5. If the id is a heading listed in `toc.json`: update `title`.
6. If it is a glossary or quiz id: also update `glossary.json` / the quiz markup.
7. Regenerate the preloader.

---

## 14. Do not edit

- `assets/base.bundle.local.js`, `assets/base.bundle.min.js(.map)`, `assets/activities.bundle.local.js`: the compiled runtime.
- `assets/libs/**`, `assets/fonts/**`, `assets/sounds/**`, `assets/favicon_io/**`, `assets/symbols/**`: vendored assets.
- `assets/interface_translations/**`: reader UI strings (not book content).
- `content/i18n/*/audio/**`, `video/**`, `timecode/**`: generated media and timings (log for regeneration instead).
- `content/i18n/*/freshness.json`: Studio disclosure data.
- Stepper JSON payloads, unless you really are fixing their content (§6.4).
- `assets/offline-preloader.js` by hand: regenerate it instead.

---

## 15. Verification workflow

1. **Static checks:** `node check-bundle.mjs adt/` (Appendix B). It checks JSON validity, that
   pages, metas and the reading order agree, duplicate or flattened `data-id`s, missing translations,
   missing images and audio, the activity contract, answer-key coverage, uncompiled Tailwind classes,
   and a stale preloader. Fix every ERROR. Fix the WARNs or explain them.
2. **Regenerate the preloader** (Appendix A) last, after all edits, then re-run the checker.
3. **Render and compare:** serve over HTTP (`python3 -m http.server 8000 -d adt`) and open
   `http://localhost:8000/<page>.html`. For clean screenshots, append `?embed=1`, which hides the
   reader chrome and disables soft navigation. Wait until `#content` is visible (its `opacity-0`
   class is removed) and fonts have loaded. Check at **1280, 768, and 375 px** wide and compare with
   the rendered PDF page.
4. **Activities:** for each changed activity, check that Submit enables, a wrong answer shows
   incorrect marks, a right answer shows correct marks and Submit turns into Next, Reset clears it,
   and the keyboard alone (Tab / Enter / Space) works. Clear localStorage between runs.
5. **Language switch:** switch to each language in the reader and confirm no source-language text
   remains on changed pages, unless you logged it as pending translation.
6. **Report:** a change log grouped by page. For each change give the file, id, before, after, the
   PDF evidence (page number), and follow-ups (re-translate, regenerate TTS, items that need Studio).

---
