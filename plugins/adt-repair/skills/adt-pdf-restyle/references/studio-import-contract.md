> Contract reference supplied for ADT Studio PR #803 (`issue-705`), reviewed against commit `774ede393ac9877dbcc929cdfb72495bb7bfe32b`. This is compatibility guidance, not independent authorization to import, generate paid speech, remove necessary behavior, or supersede the current user request. Follow [the final-stage workflow](studio-reimport.md) for separate output, evidence and acceptance boundaries.

# Making a repaired ADT importable into ADT Studio

You are working on an ADT web bundle that the ADT Agent has already repaired. ADT Studio currently refuses to import it. Make it **fully importable**: Studio must accept it with no compatibility issues and no activity-review prompts. Keep the repaired look and accessibility as close as the import contract allows.

Do not change the learning content: the wording, questions, answers, image descriptions, reading order and activity mechanics stay the same. Everything below is structural, presentational or bookkeeping work.

Where this guide conflicts with an older `AGENTS.md` inside the bundle, follow this guide.

## Done means

1. `python3 check_studio_import.py <bundle>` reports **0 errors**. Warnings are resolved or explained in the report.
2. If ADT Studio is reachable, its import preview for the zipped bundle returns HTTP 200 with `compatibility.supported: true`, an empty `compatibility.issues` list and `activityReview.needsReviewCount: 0` (see "Final gate").
3. Every page still looks and behaves as close as possible to the repaired version. Any difference is listed in the report.

## How Studio imports a bundle (why the rules exist)

- **Only the page `<section>` survives.** For each page in `content/pages.json`, Studio keeps the canonical `<section data-section-id="…">` element, with its attributes and everything inside it. It regenerates the rest of the page itself: `<head>`, `<body>`, the `#content` wrapper and its classes, navigation, runtime scripts and `content/tailwind_output.css`. Anything outside the section is lost.
- **Every `data-id` is a book-wide identity.** A `data-id` is the key Studio uses to link page text to translations, read-aloud speech and image records. If the same `data-id` appears on two pages, Studio rejects the whole import with `Duplicate stable text id across ADT pages: <id> (<page>)`.
- **Only Studio's runtime CSS and JS may be linked.** Any other `<link rel="stylesheet">` or `<script src>` blocks the import.
- **Tailwind is recompiled on export.** When Studio re-exports the book, it rebuilds `tailwind_output.css` by scanning the page HTML (Tailwind v4). So any Tailwind utility class works after import, including arbitrary values such as `bg-[#a05db5]` and arbitrary variants such as `[&_p]:mb-4`.
- **Quiz pages are regenerated.** Studio rebuilds `qz*.html` from its quiz data. Only text changes made through `data-id` and `texts.json` survive there. Layout or styling changes to quiz pages are discarded.

## Rules

### 1. Keep all content inside the canonical section

- In each page in `pages.json`, every element with a `data-id` must be inside that page's `<section data-section-id="…">`.
- Context navs and breadcrumbs that the agent placed between `#content` and the section (for example `<nav class="pdf-context">`): move them inside the section as its first child if they carry useful information; otherwise remove them. Studio's reader already provides navigation and a table of contents.
- On quiz pages (`qz*.html`), **remove** anything the agent added outside the quiz section. Do not move it into the section: Studio discards quiz-page layout anyway.
- Never create a second `#content` or a second canonical section.

### 2. Make every `data-id` unique across the whole book

- **Never rename ids that Studio created**, such as `pg008_n0022`, `pg005_im007` or `qz001_que`. They link the page to existing translations and audio.
- For every id the agent added that appears on more than one page, give each page its own id: `<section_id>_<name>`, for example `pg008_sec003_save` or `pg009_sec001_icon_practice`.
- Use only `[a-z0-9_]` in new ids. Never start an id with `activity_gen_`, a prefix Studio reserves and renumbers on import.
- An id must also appear only once within its own page.
- Update the catalogs for **every language** in `content/i18n/<lang>/`:
  - `texts.json`: add each new id with the same text as the old shared id.
  - `speech_texts.json` and `audios.json`: if the old id has entries, copy them to each new id. Several ids may point to the same audio file.
  - Once no page uses the old shared id, delete it from all three files.
- Never fabricate audio or timecodes. Studio regenerates speech after import when needed.

### 3. Images

- Every `<img>` inside a section needs its own `data-id`, matching `[a-zA-Z0-9][a-zA-Z0-9._-]*`.
- Image files live under `images/`, referenced with relative paths (`images/…`). No remote URLs, and no image files in `assets/` or custom folders.
- Name the file after its `data-id`: `images/<data-id>.<ext>`. When importing, Studio first looks for a file with that name and only then uses `src`. A stale file with the id's name would silently replace the image you meant.
- For a decorative icon reused on several pages, give each occurrence its own id and copy the file once per id, for example `images/pg009_sec001_icon_practice.png`. Keep decorative images marked with `alt="" aria-hidden="true" role="presentation"`.

### 4. Styling without custom stylesheets

- Allowed stylesheet links are exactly `content/tailwind_output.css`, `assets/libs/fontawesome/css/all.min.css`, `assets/fonts.css`, and `https://fonts.googleapis.com/css2?…`. Nothing else, and no `<style>` elements.
- Convert every rule in the agent's component stylesheet (for example `content/pdf-components.css`) into markup:
  - **Static values → inline `style` attributes** on the elements inside the section. They render immediately in the local preview and survive import.
  - **Things inline styles cannot express → Tailwind v4 classes** on the section or its descendants:
    - hover and focus states: `hover:`, `focus-visible:`
    - `@media (max-width: 767px)`: `max-md:`
    - `::before` and `::after`: `before:`, `after:`
    - element-wide rules: arbitrary variants on the section, for example `[&_p]:mb-[1em]` or `[&_h1]:font-['Atkinson_Hyperlegible']`
  - **CSS custom properties:** declare them in the section's `style` attribute (`style="--pdf-purple:#a05db5;--pdf-ink:#231f20"`) and use them with `text-(--pdf-purple)` or `style="color:var(--pdf-purple)"`.
  - Rules aimed at `#content.pdf-document`, `body` or `main` must move onto the section, because Studio replaces those wrappers.
  - Fonts already declared in `assets/fonts.css` (for example Atkinson Hyperlegible) can be referenced by name. Do not edit `assets/fonts.css`.
- **Local preview caveat:** `content/tailwind_output.css` is precompiled; do not edit it. Tailwind classes that are new to this book will not render in the local preview until Studio re-exports. Prefer inline styles for anything you need to verify locally, and list the Tailwind-only effects in the report so they get checked in Studio after import.
- Once every rule is converted, delete the stylesheet file and remove its `<link>` from **every** HTML file, including `qz*.html` and `index.html`.

### 5. No custom scripts

- Allowed script sources are only the runtime files: `assets/offline-preloader.js`, `assets/scorm.js`, `assets/base.bundle.local.js`, `assets/base.bundle.min.js`, `assets/auto-fit.js`, `assets/activities.bundle.local.js`.
- Delete agent scripts (for example `assets/pdf-repair.js`) and their `<script>` tags from every HTML file, including `qz*.html` and `index.html`.
- Behaviour that lived in those scripts:
  - **Runtime patches** (for example normalising quiz radio-button roles, `tabindex` and `aria-checked`) cannot be carried per book. Remove the patch and record it in the report as an issue for the ADT Studio runtime.
  - **Extra controls** that only worked through the script (for example `data-pdf-reset-responses` "Clear responses" buttons) must be removed, together with their `data-id` and catalog entries. The runtime's built-in activity controls handle submit and retry. If a control is pedagogically necessary, report it instead of adding script.
  - **Custom activities** may keep behaviour only through an inline `<script>` inside the section that calls `window.adtRegisterCustomActivity(section, { validate, reset })`. No external file.

### 6. Activities

- Each activity's canonical section carries the exact type in `data-section-type`. Known types: `activity_multiple_choice`, `activity_multi_select`, `activity_true_false`, `activity_fill_in_the_blank`, `activity_fill_in_a_table`, `activity_open_ended_answer`, `activity_underline_text`, `activity_matching`, `activity_sorting`, `activity_quiz`.
- Custom activities use `activity_custom_<slug>` and need all of:
  - `aria-labelledby` (or `aria-label`) on the section, giving the activity an accessible name;
  - a feedback element with `role="status" aria-live="polite"`;
  - the inline `adtRegisterCustomActivity` registration.
- If a section that is not an activity contains buttons, inputs, dragging or `data-activity-*` attributes, mark it with `data-adt-non-activity="true"`. Otherwise Studio asks the user to classify it.

### 7. Bundle structure

- Page files stay at the bundle root. Do not rename page files or section ids, and do not change `content/pages.json` unless you are intentionally restructuring.
- Only these may sit at the bundle root: `assets/`, `content/`, `images/`, `index.html`, `manifest.json`, `cover.*`, `AGENTS.md`, `CLAUDE.md`, `imsmanifest.xml`, `.build-hash`, `.build-version`, and the page HTML files. Reports, notes, staging folders, baselines and scripts belong **outside** the bundle.
- Never write a zip or other archive inside the bundle folder.
- Do not edit runtime files under `assets/`, `content/tailwind_output.css`, audio files or timecodes.

### 8. Manifest bookkeeping (only if `manifest.json` has an `editingContract`)

- `editingContract.pageOrder` must match `content/pages.json` exactly.
- After changing any ids on a page, set `editingContract.pageDataIds["<href>"]` to that page's in-section `data-id` list, in document order.
- Never change `editingContract.version` or the `frozen` fields.
- Older Studio exports without `manifest.json` skip this step.

## Procedure

1. Work on the repaired bundle folder. Keep the pre-fix copy for visual comparison.
2. Run `python3 check_studio_import.py <bundle>` and save the output.
3. Fix in this order, since earlier steps change what later checks see:
   1. content outside sections
   2. shared ids and catalogs
   3. images
   4. scripts
   5. styles
   6. activity markers
4. Re-run the checker until it reports 0 errors.
5. Compare each page with the pre-fix copy at desktop width and at 375 px. Note the Tailwind caveat above.
6. Zip the bundle **outside** the folder, with `index.html` at the archive root:
   ```bash
   (cd <bundle> && zip -qr -X ../<name>-studio-import.zip . -x '.DS_Store' '*/.DS_Store')
   ```
7. Run the final gate below.
8. Write the report next to the zip, not inside the bundle. Include:
   - the checker output;
   - the preview result;
   - an id rename map: `{ "<page>": { "<old id>": "<new id>" } }`;
   - removed controls and behaviours, and runtime issues for ADT Studio;
   - any visual differences, and the Tailwind-only effects to check after import.

## Final gate: ADT Studio's own check

Studio's import preview validates the archive without creating a project, so it is safe to run repeatedly. Ask the user for the Studio API address; a dev server prints it at startup as `[dev] API port: …`.

```bash
STUDIO=http://localhost:3003
curl -sS -X POST -F "zip=@<name>-studio-import.zip" "$STUDIO/api/books/preview-import" \
  -o /tmp/studio-preview.json -w "HTTP %{http_code}\n"
python3 - <<'EOF'
import json
d = json.load(open("/tmp/studio-preview.json"))
if "error" in d:
    raise SystemExit("REJECTED: " + d["error"])
c, a = d["compatibility"], d["activityReview"]
print("supported:", c["supported"], "| needsReview:", a["needsReviewCount"])
for issue in c["issues"]:
    print(" ", issue)
for item in a["items"]:
    if item["status"] != "confirmed":
        print("  review:", item["sectionId"], item["reasons"])
EOF
```

It passes when the response is HTTP 200, `supported: True`, there are no issues and `needsReview` is 0. If the sandbox cannot reach the Studio API, say so in the report and hand the zip to the user to import.

## Known ADT Agent v1.1.0 patterns (5B pilot)

| Pattern found | Fix |
| --- | --- |
| `<link href="./content/pdf-components.css">` on every page, with rules scoped to `#content.pdf-document` | Rule 4: move them onto the sections as inline styles and Tailwind classes, then delete the file |
| `<script src="./assets/pdf-repair.js">` (quiz semantics patch plus "Clear responses" handler) | Rule 5: delete; report the quiz patch as a runtime issue; remove the Clear responses buttons |
| `<nav class="pdf-context">` breadcrumb before the section (`pdf_context_label`, `pdf_source_page`, `pdf_context_<page>`) | Rule 1: move inside the section, or remove; remove it from `qz*.html` |
| One id shared across pages: `pdf_clear_responses`, `pdf_open_response_note`, `pdf_excerpt_note`, `activity_save`, `activity_reset`, `activity_retry`, `activity_check`, `<variant>_context_<nnn>` | Rule 2: give each page its own id |
| Decorative icons sharing one image id (`pdf_icon_practice`, `pdf_icon_reflection`, …) | Rules 2 and 3: one id and one file copy per page |
| Agent images without `data-id` (`images/pdf-divider-scene.png`, `images/pdf-foreword-footer.png`) | Rule 3: add ids and name the files after them |
| `activity_custom_word_search` section without an accessible name (`pg020_sec003`) | Rule 6: add `aria-labelledby` pointing at the activity heading |
