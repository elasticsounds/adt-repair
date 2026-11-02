# v1.2.1 fidelity correction

Version 1.2.1 corrects the v1.2 conversion failures: CSSOM longhand replay lost variable borders, custom activity startup registration was removed, newly generated state classes were absent from standalone CSS, and 22 accepted reset controls were removed. The new helper preserves authored declarations and compiles responsive/state utilities with explicit priority. Checks must cover visible selected states as well as initial screenshots.

The 5B importer/runtime fixes are a separate Studio experiment, not included in the MIT distribution. Stock issue-705 still requires those changes for map grading and faithful quiz export. Read the current [workflow and limitations](../plugins/adt-repair/skills/adt-pdf-restyle/references/studio-reimport.md). The v1.2.0 results below remain historical evidence, not v1.2.1 acceptance.

The final local v1.2.1 pilot covered 39 sections in Albanian and English: 312 standalone captures, 312 patched-Studio export captures, 78 direct-file captures, 101 activity/navigation cases and 12 source/export quiz reload comparisons. The 60 representative Sol/import/export captures matched the measured component styles and alignment. Automated scans retained 52 standalone and 50 exported captures with inconclusive accessibility findings; human assessment and TTS remain pending. The original floating Submit control's phone overlap remains a recorded baseline usability issue.

The Studio experiment used base commit `774ede393ac9877dbcc929cdfb72495bb7bfe32b` plus local patch SHA-256 `983fdbcfa17905dd629eb815120f9ceefa99430a924878af3844d1285fcaef3e`. It is not merged into Studio and is not included in these MIT release ZIPs. Stock `issue-705` preview accepted the handoff, but the successful fidelity round trip required the local patch. These are pilot results for one book, not a guarantee for every textbook.


# Studio reimport preparation in v1.2.0

The final repair stage prepares a separate Studio-import copy and ZIP. The accepted Sol reader remains intact. This is a new-project recovery handoff for [ADT Studio PR #803](https://github.com/unicef/adt-studio/pull/803), branch [`issue-705`](https://github.com/unicef/adt-studio/tree/issue-705), reviewed at commit `774ede393ac9877dbcc929cdfb72495bb7bfe32b`. It does not merge edits into an existing project or automatically generate speech.

Read the [agent workflow](../plugins/adt-repair/skills/adt-pdf-restyle/references/studio-reimport.md) and [versioned import contract](../plugins/adt-repair/skills/adt-pdf-restyle/references/studio-import-contract.md). The checker originates from the user's Studio import material and is extended with machine-readable results and checks for index dependencies, inline style elements, unknown activity types, unsafe page paths and symlinks. The contract was supplied for this PR; it is not a promise about all Studio versions.

The helper prepares and hashes an isolated copy, checks it, requires warning explanations, creates a ZIP outside the bundle, and records Studio preview acceptance against the exact archive. It refuses stale packages. The agent still performs book-specific CSS/markup/catalog adaptations and visual/behavior review; the helper is not an automatic arbitrary-CSS converter.

Keep four outcomes separate: offline preflight, Studio preview, round-trip fidelity, and narration completion. Only Studio's preview can establish its compatibility acceptance. Only export comparison and behavioral review can establish what survived. A successful import does not establish fresh audio; both speech inputs and audio/timing follow-ups must be recorded. Runtime fixes that cannot be transported remain Studio issues, not silent removals.

Preparing this stage does not authorize paid TTS or account/voice changes. Deliver the per-language/ID regeneration plan, preserve valid recordings, and run selected generation/alignment only when requested. Re-export afterward and verify spoken wording, image descriptions, playback and highlighting.

Version 1.2.0 remains a prepared local release until explicitly published. Keep prior distribution ZIPs and the source snapshot for rollback. Standard is the recommended workflow; economy remains experimental and on hold after the [5B evaluation](economy-evaluation.md).

## 5B pilot outcome

The separate 39-section, sq/en import copy passed offline preflight and the live Studio preview on the pinned commit: HTTP 200, supported compatibility, no compatibility issues and zero activities needing classification. A new-project import and ordinary export also completed without packaging warnings. These successful gates did **not** establish round-trip acceptance.

Tests found missing native map answer globals after recovery, so incorrect map answers were accepted. The first adapter output did not expose its responsive classes correctly to Tailwind. Correcting media-variant syntax and preserving raw candidates in a section comment restored the cover's original desktop/phone measurements in both normal and fresh-CSS exports. The live checkout has no prebuilt CSS file; the earlier cached-CSS diagnosis was not supported by the final comparison. Generated quiz output still had phone overflow and native nested-radio accessibility issues, which the original standalone repair had addressed with its non-importable presentation/adapter.

The initial diagnostic export matrix covered 312 captures, with 16 captures containing failures and 52 inconclusive accessibility results. It preceded the adapter correction and is retained as superseded diagnostic evidence; the final exact export matrix recorded 312 captures, 12 failing captures (all three generated quizzes) and 48 inconclusive accessibility results. All requested language samples were verified. Actual language/catalog samples were checked. Activity evidence includes confirmed wrong-map-answer failures; concurrent startup timeouts left some behavioral coverage incomplete, which is recorded rather than passed. The agent now warns about out-of-section answer globals and requires actual post-export grading and responsive-CSS checks.

The prepared archive is suitable for import testing, **not an approved replacement for the Sol reader**. Retain the original output until Studio-side fixes and a new round-trip review establish acceptable results. Six corrected narration inputs were aligned in the import copy; TTS remains not-run. These local book assets and reports are not distributed in the plugin release.
