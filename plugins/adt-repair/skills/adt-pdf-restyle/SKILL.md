---
name: adt-pdf-restyle
description: Audit and repair an existing ADT Studio textbook using its source PDF and optional teacher or reviewer notes. Fix layouts, assets and activity issues while preserving the reader, content bindings and saved responses. Use for PDF-guided cleanup of generated ADTs, not new reader creation.
---

# PDF-guided ADT repair

Audit and repair the supplied ADT using the source PDF and optional teacher/reviewer notes. Keep the reader the user supplied: navigation, page routes, localization, activities and saved-answer behavior are integration contracts, not scaffolding to replace. This is an agent workflow with deterministic helpers, not an automatic converter or a fixed repair for a particular book.

## Inputs and job setup

Required: an ADT folder or ZIP and its original PDF. Use **standard** (Sol-led) unless the user explicitly requests an experimental **economy** trial. Economy is on hold for release after the user preferred standard over both 5B trials; do not present it as an equivalent production route. Never infer economy from book size, account balance or a request to work quickly. Keep the selected mode in `job.json`; resume it without asking again. Legacy jobs without a mode retain standard behavior. Audit versus repair is a separate operation, not another execution mode.

Standard retains the thorough Sol-led workflow below. Economy explicitly delegates bounded work to Luna and Terra, retaining Sol for design decisions, escalations and final review. Read [execution policy](references/execution-modes.md) before dispatching economy work or changing models. Verify model availability and model-selection controls first. A prompt cannot change the primary model or prove a handoff occurred; do not silently substitute Sol when budget routing is unavailable.

Optional: note files, pasted teacher/reviewer comments or exported annotations; a physical PDF page range; output folder; audit or repair operation. Default to all physical pages and all existing book languages unless the user limits scope. Notes are never required to proceed. Audit produces findings and proposals without changing the working ADT.

Read [setup](references/setup.md) for portable prerequisites and commands. Use the bundled `scripts/prepare_job.py` to create a new job containing an untouched baseline, a separate working copy, copied note files and a source/hash manifest. Never prepare inside the supplied ADT or overwrite an existing job. Resume existing jobs from recorded stages. Do not copy a previous book's repair adapter or brand into a new one.

Read [reporting](references/reporting.md) for issue, note, validation and delivery formats. Read supplied feedback before the audit, map each actionable note to its affected page/section/language and scope, and preserve its provenance. Combine it with independently found issues. A reviewer claim is evidence to investigate, not a verified defect. Explicit user-requested departures from the PDF are intentional adaptations. Clarify material conflicts only for affected work and continue independent repairs. Track every actionable note's disposition in the final report.

In both modes, use one source map, one issue register and one component contract across languages. Extract/render source evidence once per matching fingerprint; deduplicate repair patterns while retaining every affected section and note's provenance. Use `scripts/workflow.py` to record dispatched tasks and check reusable evidence. Reuse requires matching inputs, context, scope, helper version and output hashes; it is not permission to skip unperformed review. Apply shared changes once, validate affected scope, and avoid re-reading full catalogs or the whole chat in each handoff.

## Inventory before styling

Identify the exact PDF and the ADT root containing `content/pages.json`. Read the bundle's `AGENTS.md` and inspect representative HTML, runtime configuration, localization and offline-loading files. Work in a separate copy unless the user explicitly prefers in-place edits.

Run the portable baseline helper:

```sh
python scripts/inventory.py --adt /path/to/adt --pdf /path/to/reference.pdf --out /path/to/baseline.json
```

The PDF option requires `pypdf`; image dimensions use Pillow when available. Discover installed runtimes rather than hardcoding another machine's paths. Filename-derived source-page numbers are hints until checked against the PDF. The helper records sections, leaf text bindings, images, controls, metadata, scripts and file hashes; it does not judge content or visual fidelity.

Inventory **every in-scope physical PDF page and every ADT reading-order entry**, including cover, contents, notes, dividers, unusual layouts and quizzes. Distinguish physical PDF page numbers, printed folios and ADT section indices. Multiple sections may represent one source page. A page with little extractable text is not permission to omit it. Record a verified many-to-many source map. If the user limits the page range, leave unrelated content intact; validate shared changes wherever they apply.

Before repairs, write the audit, issue register and proposed restructure plan. Categorize content, missing content, functionality, design, consistency, accessibility, missing/incorrect assets, lost heading/breadcrumb context, and sections that need splitting or merging. Record evidence and confidence. Classify every source page and ADT section by template; create a variant only where a distinct composition needs it. Do not execute route/state migrations merely because the audit recommends them.

If the ADT extends beyond the supplied PDF, state the mismatch early. Continue with shared styling where appropriate, but label those pages as lacking source verification. Do not manufacture missing source content or claim whole-book fidelity. Account explicitly for pages Studio omitted; restore them within the authorized scope, or report the omission without silently treating it as complete.

## Inspect and repair assets

Render the supplied PDF and review every page, using contact sheets for orientation and full-page views for actual content checks. Inventory every referenced ADT image and compare source-backed images with the PDF.

Prefer correctly extracted original image objects. Raw PDF objects may omit masks, include material hidden by clipping, or miss vector composition. In those cases, crop the rendered source and record the PDF hash, physical page, render dimensions, crop coordinates and reason. Never replace diagrams with invented illustrations or flatten readable lesson text into a page screenshot.

Keep existing image IDs and paths where feasible, replacing their bytes only when the replacement is verified. Preserve meaningful alternative descriptions, avoid revealing exercise answers, and check the runtime does not overwrite a repaired description from a dictionary or cache. Retain acceptable assets; do not re-extract everything merely because the workflow can.

## Derive and apply the component system

Distill the actual PDF's colors, typography, spacing, heading hierarchy, panels, image treatments and unusual page compositions. Build a small fixed library of semantic components and variants. Derive the brand anew for each book; do not copy the previous book's purple palette or content-specific selectors as universal defaults.

Use a pinned local Tailwind build. For an existing Studio bundle, an additional **scoped component stylesheet without preflight** usually avoids disrupting the shell's compiled utilities. Scope content styles to an opt-in root such as `#content.pdf-document`. If new Tailwind utility classes are used, compile them; do not assume the old stylesheet contains them. Keep the component source, compiled CSS and a live example guide together.

Adapt the existing HTML or data layer to those components. Reuse text and control nodes rather than copying their visible text into a separate reader. Avoid runtime DOM rebuilding and mutations of compiled vendor bundles. Do not globally erase positioning, ARIA attributes, color legends or image geometry without understanding their role.

Read [Studio integration details](references/studio-integration.md) when working with localization, quizzes, offline caches or saved answers.

For deeper runtime diagnosis, consult the relevant sections of the [verified bundle architecture](references/adt-bundle-architecture.md), especially section 5 (catalog application), section 6 (activity contracts), section 7 (offline data), and section 10 (language/audio). Load only the parts needed. Its observed patterns must be checked against the supplied export version.

Preserve these unless a source-backed correction is specifically needed and documented:

- Reading order, routes, section identity and navigation metadata.
- Text/image `data-id`, translation keys and narration mappings.
- Activity IDs, control type/name/value, answer keys, feedback and persistence hooks.
- Runtime bundles, reader controls, configuration, fonts used by the shell and SCORM wiring.

Keep open-response activities open. Do not change grading or invent new answers as a styling shortcut. If a faulty extraction produced an extra field, retain existing saved-answer compatibility where possible and document the adaptation.

## Validate the actual result

Run the baseline helper against the repaired copy with `--compare baseline.json`. It fails on lost text bindings, controls, image IDs, altered navigation/script identities or changes to protected runtime/localization files. Review intentionally changed paths explicitly with `--allow-change relative/path`; this records the exception and does not waive browser or source review.

Then validate **all ADT sections** in a real browser at desktop, tablet, phone and 320px reflow widths. Check visible text, missing images, horizontal overflow, content hidden behind fixed controls, image cropping, large text/text spacing and keyboard focus. The bundled `scripts/browser-audit.mjs` captures every section, configured language and viewport and records content accessibility findings, incomplete results and JS errors. It is not a substitute for visual source comparison or behavioral tests. Run accessibility checks on the changed content and investigate inconclusive results; separate inherited shell issues from regressions.

Exercise reader behaviors once per distinct runtime/configuration and repeat them when their dependencies change: previous/next navigation, contents menu, reading options, glossary and image descriptions. Test `file://` or the bundle's actual offline mode as well as local HTTP. Exercise every activity and quiz using the state coverage below; a recorded check can satisfy both requirements without rerunning it. Do not claim saving or quiz behavior merely because IDs are unchanged. Check existing saved state survives the restyle where the runtime supports it.

Review final screenshots across every page family and every exceptional page; inspect all source-backed pages against the PDF. Keep a page inventory, asset repair record, unresolved findings and validation reports tied to the delivered files. Packaging must use the checked output, not an earlier build.

Exercise every activity and quiz, including applicable wrong/correct/empty, feedback, retry and save/reload states. Check both base and Easy Read variants where present. Regenerate changed offline payloads using the bundle's packager or `scripts/regen-preloader.mjs`, which preserves supported loader code and fails on unknown payload formats. The static `scripts/check-bundle.mjs` catches Studio contract and stale-cache issues; a clean static check does not prove activities work.

## Final stage: Studio reimport preparation

After accepting the repaired reader, follow [Studio reimport preparation](references/studio-reimport.md) to produce a separate import-compatible copy/ZIP for Studio PR #803 (`issue-705`). Preserve the accepted repair. Resolve section boundaries, added ID/catalog migrations, image identity, supported styling/scripts and activity declarations; record required behavior or visual differences rather than hiding them to pass import. Run the offline preflight and, when reachable, Studio's actual preview. Verify a new-project import/re-export when available, with independent visual and behavioral acceptance. Do not claim round-trip fidelity from checker success. Preserve authored CSS shorthand text containing variables, compile new utilities in the copy, retain the custom-activity startup queue and reset controls, and verify border geometry plus selected/found/feedback states against the accepted reader. A needed Studio runtime/importer fix must be tested separately and identified by commit/patch fingerprint; never imply it is already in the target branch. Audit-only jobs report import risks without converting the ADT. Prepare the per-language narration regeneration plan; actual paid TTS remains a separate explicitly requested action.

Deliver the repaired ADT, separate Studio-import ZIP, editable components, inventory and supporting evidence plus **one standalone PDF review and repair report alongside the ADT**, following [reporting](references/reporting.md). List every issue and note disposition, completed fixes, accessibility/behavior evidence, inconclusive/unperformed checks and media follow-ups. Include the import gate results, Studio version, ID migration/differences and narration handoff, plus execution mode, actual model handoffs, escalations, reused evidence and measured usage when available; otherwise mark usage and cost unmeasured. Never label an unperformed check passed. Record the exact delivered version/hashes. A reusable workflow is not a promise that arbitrary generated layouts can be repaired without inspection.
