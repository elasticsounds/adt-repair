# Standard and economy execution

There are exactly two execution modes. Select one at startup, persist it in `job.json`, and load this reference only for routing, economy execution or model availability questions. `audit` and `repair` remain operations within either mode.

| Mode | Model work | Quality and delivery |
| --- | --- | --- |
| standard | Sol leads source interpretation, design, repairs and review; deterministic helpers do mechanical work. | Full workflow in SKILL.md. |
| economy | Sol coordinates decisions and delegates bounded analysis to Luna and bounded implementation to Terra. | Same page/section/language coverage, integration contracts, activities, accessibility evidence and standalone report. |

Economy changes assignment and reuse, not the definition of complete. Do not advertise a measured savings percentage or quality equivalence without a controlled book-level comparison.

## Startup and model controls

1. Accept an explicit `standard` or `economy` selection. If absent, present those two choices before costly analysis. Existing jobs retain their recorded choice; old jobs without `execution_mode` use standard. Do not silently change a running job's choice.
2. Check the actual parent model, available worker models and model-selection tools. Target `gpt-6.1-sol`, `gpt-6.1-terra`, and `gpt-6-luna`. Luna's identifier is GPT-6 Luna, not an assumed GPT-6.1 Luna. Use the actual account's available model identifiers; never invent an alias. If these identifiers are unavailable, explain which task is blocked and ask for standard or a separately confirmed available model mapping. Do not conceal full-price fallback as economy.
3. A skill cannot switch its parent model by declaring a preference. For the intended baseline, start the coordinator with GPT-6.1 Sol. If the current coordinator differs, report that fact and have the user select Sol before model work; deterministic preparation can continue. Custom agents or explicit model-aware spawning can select worker models. Verify actual dispatch results; the local helper only plans and records.
4. Use the normal service tier for cost comparisons. Workers inherit the parent's tier; do not enable Fast as an economy optimization. Honor the user's existing tier and record it if it differs. Do not change global Codex settings, API authentication, permissions or providers as part of selecting a repair mode.

Codex supports explicit per-subagent models; without one, workers may inherit the parent. See [official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents). If the client cannot select worker models, do not claim routing occurred or start nested Codex processes to work around it.

## Task routes

`workflow.py route` is the single executable routing table. `--risk high` sends any kind directly to Sol with high reasoning. Otherwise:

| Task kind | Economy model | Assignment boundary |
| --- | --- | --- |
| `triage`, `classify` | Luna, low | Compare supplied page/section evidence, propose template IDs and issue leads. Every assigned page must actually be inspected. Ambiguity is a finding, not a guessed match. |
| `notes` | Luna, low | Map and deduplicate readable comments while retaining each comment's provenance and disposition. |
| `report-draft` | Luna, low | Summarize structured registers; never turn incomplete or unrun checks into passes. |
| `component-implementation`, `repair` | Terra, medium | Implement the agreed design contract in explicitly owned files or one template batch. Preserve all bindings and existing activity contracts. |
| `asset-repair` | Terra, medium | Extract a source-backed replacement or verified crop for listed assets only; record provenance. |
| `behavior-diagnosis` | Terra, medium | Investigate failing activity/browser evidence and propose or implement a bounded fix. Grading or saved-state semantics are high-risk. |
| `design-contract` | Sol, medium | Derive and sign off book-specific brand tokens, components and variants once, using all page families and exceptions. |
| `outline`, `answer-key` | Sol, medium | Decide source interpretation or structure; use high risk for any route/state migration, grading change or ambiguous missing content. |
| `final-review` | Sol, medium | Check coverage, template representatives, exceptions, high-severity resolutions, preserved contracts and honest report limitations. |

Standard routes every model task to Sol. The helper is optional for legacy standard jobs, but use it for new dispatch records in either mode. Deterministic extraction, hashes, checks, browser capture, PDF rendering, component compilation and report rendering do not need a model task.

## Economy sequence

1. **Prepare and inspect once.** Run preparation, inventory and required source rendering. Keep reusable renders/text/assets under the job, separate from the learner bundle. Build one verified source map and issue register across languages. Supplied notes are ingested once.
2. **Classify in bounded batches.** Delegate Luna batches by page family, initially up to eight related sections plus their source pages and relevant language records. Use more than one batch when evidence would be crowded; do not force unreadable contact sheets. Supply only needed full-resolution images/crops and linked source text. All source pages and ADT entries still need recorded review. Sol resolves unmatched/ambiguous pages and defines the design contract before implementation.
3. **Repair one pattern at a time.** Terra implements shared components and scoped repair batches against that contract. Reuse a fix across matching sections, then check all affected instances and languages. Keep exceptional layouts explicit. Do not rebuild acceptable assets or translations. Only one writer owns a shared stylesheet, catalog or runtime adapter at a time.
4. **Run checks as scripts.** Batch deterministic checks locally. Inspect failure summaries first, then open the exact screenshots, section markup and catalog fragments required to diagnose them. Retain all evidence; do not send all 1,600 captures to every worker for a 200-section, two-language, four-width book.
5. **Escalate instead of retrying indefinitely.** A model gets one bounded attempt per task. Missing evidence, uncertain page mapping, incomplete source comparison, failed checks or out-of-contract changes result in `needs-escalation` or `blocked`. Luna → Terra → Sol is the maximum ladder; high-risk work starts at Sol. Infrastructure/tool failures are not a reason to pay for successive stronger models. Stop on missing dependencies/access and report them. After an unresolved Sol attempt, record the blocker rather than spawning another equivalent task to evade the limit.
6. **Review and deliver.** Luna may draft the evidence summary; the deterministic report renderer builds the PDF and Sol reviews the final evidence and limitations. The same source, responsive, language, activity, accessibility and offline gates apply to both modes. No step can certify a check it did not perform.

## Handoffs and dispatch ledger

The coordinator owns `reports/execution.json` and serializes all ledger/cache writes. Workers return files and short results; they do not concurrently edit the ledger. Model records are session-reported evidence, not API billing authentication.

Before dispatch, run `start` with a unique task ID, kind, input files and context dependencies. Then actually spawn a worker with the returned model and effort through the client's model-aware tool. Where full-history inheritance prevents explicit model selection, start a fresh worker with only the bounded packet. Include:

- Task ID, kind, page/section/language coverage and acceptance checks.
- The relevant source renders/text, section files and catalog fragments.
- The approved component contract, runtime constraints and issue IDs.
- An explicit set of owned output files; prohibit edits outside that set.
- A requirement to return evidence paths, changed paths, checks and unresolved items. No further delegation unless the coordinator assigns it.

After the worker returns, inspect its artifacts and tests. Call `finish` with the model actually reported by the session, a status and evidence outputs. A model mismatch is recorded as blocked. If dispatch fails before a worker runs, use `block --job JOB --task-id ID --reason TEXT`; actual model and usage remain null. A passed task requires an output file. Pass provider usage JSON only when available; missing usage stays null, not zero. Do not fabricate an actual-model or usage receipt from the requested settings.

Example commands, run from the plugin directory after the job's referenced files exist:

```sh
.venv/bin/python skills/adt-pdf-restyle/scripts/workflow.py start \
  --job /path/to/job --task-id classify-001 --kind classify \
  --input reports/source-map.json --context reports/baseline.json
# The coordinator now dispatches the returned model using Codex tools.
.venv/bin/python skills/adt-pdf-restyle/scripts/workflow.py finish \
  --job /path/to/job --task-id classify-001 --actual-model gpt-6-luna \
  --status passed --summary 'Assigned pages inspected; mappings documented.' \
  --output reports/classify-001.json
```

For a recorded `needs-escalation` result, use `escalate --job JOB --task-id ID --reason TEXT`, inspect the returned refreshed evidence and dispatch the returned model. Prior attempts remain in the ledger. Task IDs identify work, not individual tries; do not create new IDs merely to retry the same unresolved work.

## Evidence reuse and invalidation

`workflow.py cache-put` records a **completed, passed evidence artifact** with input/context hashes. It does not perform extraction, source review or browser testing. `cache-check` returns `reusable: true` only for the exact recorded dependency set and unchanged outputs. It rehashes the current PDF, page/language scope, execution mode and supplied tool-version string too. Cache check results are not automatically counted as reuse in the report; record actual reuse and the evidence key in `report-summary.md`.

Register every dependency, not just the edited HTML: shared CSS, component contract, runtime bundles, configuration, catalog files, images/fonts and test script/version when they affect the evidence. Build a compact dependency list per task. For an unknown dependency graph, invalidate broadly rather than infer independence. Include `operation` and any changed user directions/notes in a job-local scope/context file. Use a new cache key for a refreshed evidence revision; old entries are immutable. Failed, inconclusive or partial tests are not passed cache entries.

```sh
.venv/bin/python skills/adt-pdf-restyle/scripts/workflow.py cache-put \
  --job /path/to/job --key lesson-check-v1 --status passed \
  --input repaired-adt/pg001_sec001.html \
  --context repaired-adt/assets/config.json \
  --context reports/lesson-dependencies.json \
  --artifact reports/lesson-checked.json --tool-version 1.1.0-lesson-check-v1
# Reuse is conditional on the same complete dependency list:
.venv/bin/python skills/adt-pdf-restyle/scripts/workflow.py cache-check \
  --job /path/to/job --key lesson-check-v1 \
  --input repaired-adt/pg001_sec001.html \
  --context repaired-adt/assets/config.json \
  --context reports/lesson-dependencies.json \
  --artifact reports/lesson-checked.json --tool-version 1.1.0-lesson-check-v1
```

A file naming another dependency is not a substitute for hashing that dependency itself; pass its actual file using `--context`. Cache entries are job-local. Do not reuse a previous book's design, source map or adapter merely because pages look similar.

For a global CSS edit, recheck every affected section at every required viewport and language; invalidate the relevant old evidence. For one image replacement, recheck each referencing section and its language/viewport variants plus source provenance. Reuse unaffected evidence only with a complete dependency fingerprint and clearly report prior evidence versus new checks. The browser capture helper still runs a full matrix; selective capture scheduling is not implemented by this version.
