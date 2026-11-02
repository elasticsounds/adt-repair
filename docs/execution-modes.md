# ADT Repair v1.1.0: standard evaluation and economy design

**Current decision:** retain the Sol standard workflow. The mixed economy and Terra-only 5B trials passed many technical checks but were rejected by the user for visual quality relative to standard. Economy is experimental and on hold for release. Read the [findings and release decision](economy-evaluation.md). The routing below describes the original proposal, not a validated production alternative.

## Baseline and limits

Standard names the existing thorough PDF-guided workflow. The original 20-page pilot covered 39 digital sections in Albanian and English. Its recorded evidence included 117 desktop/tablet/phone renders, 39 content accessibility scans with zero violations but retained incomplete findings, 30 activity/catalog checks and six reader checks. All 39 sections also received 320px and large-text checks. Original text/image bindings and URLs were conserved. Screen-reader sessions, full translation review, audio listening and LMS acceptance were not established. This is one successful book, not proof across arbitrary exports.

There is no reliable per-phase token/billing receipt from that pilot. A retrospective dollar total or savings percentage would be invented. Two subsequent economy trials now have usage estimates and user feedback, recorded in the findings. Neither was accepted as equivalent to standard; there is no validated saving for acceptable book-level quality.

## What changes

| Work | Standard | Economy |
| --- | --- | --- |
| Mechanical inventory, extraction, rendering, checks, packaging | Local scripts | Same local scripts |
| Source/section classification and note intake | Sol | Luna, bounded evidence packets |
| Brand and reusable component design | Sol | Sol once per book; Terra implements the approved contract |
| Bounded layout, image and behavior repairs | Sol | Terra; high-risk tasks go directly to Sol |
| Ambiguous content, outline/state/grading decisions | Sol | Sol |
| Report draft | Sol or structured renderer | Luna summary plus structured renderer |
| Final quality decision | Sol | Sol |
| Source, responsive, language, activity and accessibility scope | Full | Full |

Exact targets: GPT-6.1 Sol (`gpt-6.1-sol`), GPT-6.1 Terra (`gpt-6.1-terra`), GPT-6 Luna (`gpt-6-luna`). Availability must be checked in the executing account. Models and tier are real session settings, not something a manifest can enforce by itself. The helper returns routing instructions; Codex's model-aware worker tools perform the actual handoff. Unsupported routing is reported, not silently replaced with Sol.

## Duplications addressed in this release

- One shared source map, issue register and component contract spans all languages. Base content and translated rendering remain separately verified, with shared extraction/design reused.
- Shared template defects are grouped into one repair plus per-instance verification. Duplicate reviewer comments retain provenance while pointing to the same issue.
- Source evidence and completed checks can be reused only when their explicitly registered dependencies, scope, tool version and outputs still match. The cache never turns an unperformed or inconclusive check into a pass.
- Workers receive bounded evidence and ownership; they do not inherit the full book/chat by default. The coordinator serializes shared-file and ledger updates.
- One attempt per model/task and a bounded Luna → Terra → Sol ladder limit repetitive cheap-model failures. High-risk tasks start at Sol. No model is needed to rerun a deterministic check.
- Inventory hashes each HTML read once and streams other file hashes. ZIP preparation moves the disposable extraction into the baseline instead of making a third full copy.
- Browser capture appends one JSONL record per capture and writes the final JSON once, replacing quadratic repeated full-result writes. Full per-width text remains available because widths can reveal different hidden/visible content.
- Reader checks and activity checks share already-recorded evidence instead of repeating the same state twice. Global changes still trigger global validation.

The existing two isolated durable ADT copies remain intentional, including audit jobs, to protect supplied inputs and preserve current job semantics. Browser capture still visits every requested section/language/width. Selective capture scheduling, automatic dependency discovery, cross-job caches and a hosted/API execution service are not part of this release.

## How to judge the economy version

Use the same immutable original ADT/PDF/notes, page range, languages, model service tier and acceptance criteria in two separate jobs. Run one as standard and one as economy. The repaired output from the first run must not be the second run's input. Keep job-local caches separate for the initial comparison; benchmark repeated edits separately.

Compare source omissions, severe/unresolved defects, template consistency, preserved bindings/routes/state, actual language application, every activity's behavior, browser/accessibility evidence and report completeness. Review the two outputs without relying on which mode produced them. A lower bill with more unresolved work is not an equivalent completion.

Record wall time, model/effort/tier, handoff and escalation counts, cache reuse, actual provider token categories and charged cost where available. Distinguish API dollars from subscription credits and do not add cached-input tokens twice. Include coordinator and failed attempts, not just successful workers. If provider usage is unavailable, report unknown. Calculate savings only from comparable complete runs with measured costs.

Before claiming economy is validated for books, run a full two-language pilot on the existing source inputs and at least one materially different book. The release helper/tests validate routing, cache invalidation and output reporting, not pedagogical or visual equivalence of an economy-remediated book.

## Version and distribution

The prepared v1.1.0 economy release is on hold, alongside the immutable v1.0.1 standard release. Use `standard` for new jobs. The v1.2.1 CLI retains the experimental preparation option and accepts an explicit `standard` or experimental `economy`; this documentation decision does not remove routing code. `audit` versus `repair` is an independent operation. The Python API and old jobs retain standard as their compatibility default.

The UNICEF directory draft remains v1.0.1, not submitted or published. The portal's skills-only admission restriction is independent of these execution modes. Building v1.1.0 does not upload a new directory draft, accept publisher agreements or change runtime API billing.

See the [execution policy](../plugins/adt-repair/skills/adt-pdf-restyle/references/execution-modes.md) for routing, handoffs, commands and invalidation rules. Official model handoff behavior: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents). API billing follows [authentication](https://learn.chatgpt.com/docs/auth#sign-in-with-an-api-key), not the plugin's publisher identity.
