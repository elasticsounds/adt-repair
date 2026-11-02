# ADT Studio integration contracts

Treat these as patterns to verify in the actual bundle, not a guarantee about every Studio release.

For the final import-compatible deliverable, follow [Studio reimport preparation](studio-reimport.md). The standalone repair may use a scoped CSS layer; PR #803's import copy must carry supported section-level presentation instead. Do not weaken the accepted reader or confuse its contract with the stricter import representation.

## Identity and content

`content/pages.json` is the navigation spine. `meta[name=title-id]` identifies a section; `page-section-id` often stores its one-based position in the spine, **not** the printed page number. Do not renumber sections for a visual refresh.

`data-id` can point to visible text, an image description, an activity area or a quiz. Text may be populated from `content/i18n/<lang>/texts.json`; fallback HTML is not necessarily authoritative. If text is intentionally corrected, align fallback and dictionary wording. Narration can have separate `speech_texts.json`, `audios.json` and actual audio files. Styling does not authorize fabricating new audio.

Some generated nodes with empty text IDs are placeholders for answer lines. Preserve their bindings even when cleaning empty layout wrappers. Snapshot **leaf text nodes** to avoid confusing a reordered wrapper with lost text.

## Offline cache

`assets/offline-preloader.js` may contain a serialized `INLINE` map of JSON and navigation HTML. Its fetch wrapper can serve cached values even over HTTP. Updating only `texts.json`, configuration or page manifests may therefore have no effect.

Prefer regenerating the cache with the bundle's own packager. If none exists and a source-backed change requires it, parse and update only the data payload, retain the loader logic, and compare cached values with the files. Never change the compiled runtime just to bypass the cache. Test both HTTP and direct-file loading after a change.

## Activities and saved state

Keep `data-activity-item`, control `id`, `name`, `type` and `value`. Existing answer keys may appear in several forms: section attributes, inline JSON scripts, option explanations and `window.correctAnswers`. Changing only one representation can make grading inconsistent.

Persisted responses may depend on page identity and browser origin. Test edit → blur → reload on the same origin. A new localhost port does not share the old origin's storage; this is not by itself a regression. For a true migration check, load the original and replacement at the same test origin or transfer the runtime's actual persisted state into the test context.

Quiz runtimes sometimes assign `role=radio` and `tabindex` to a label that already contains a native radio input. Diagnose this on the running page; avoid introducing two focusable controls for one option. Any compatibility adapter should preserve the runtime's event hooks and checked state, be narrowly scoped and be tested for mouse and keyboard behavior.

## Styling boundary

Keep the reader's compiled CSS and runtime intact unless the task specifically requires a supported rebuild. Add a locally compiled, scoped brand layer without global preflight. Existing CSS may assign fonts to every `span` or `div`; inspect computed styles, particularly children of cover headings, rather than assuming inheritance.

Retain geometries with meaning: diagrams, map leaders, rating grids and table relationships. Use normal-flow responsive galleries instead of fixed-height overlapping containers when they clip content. Generated decorative icons may be replaced by the corresponding original PDF icon; decorative CSS can be removed only when no text, activity binding or image meaning depends on it.

Do not hide scrollbars, clip overflow or shrink text merely to make a viewport check pass. Fix the layout and verify all content remains reachable.

An icon can share a wrapper with all the questions in a panel. Hiding its parent can preserve every ID while hiding the actual lesson. Hide only the decorative node unless the whole wrapper is demonstrably decorative; check required text visibility separately from DOM preservation. Speech overlays may use large negative margins rather than `position:absolute`. Review both when moving captions into normal flow. Match unprefixed `flex-col` separately from responsive classes such as `max-sm:flex-col` when adapting desktop media rows.
