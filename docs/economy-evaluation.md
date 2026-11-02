# 5B model evaluation and release decision

Decision recorded after the user's visual review of the standard, mixed economy and Terra-only outputs. Scope: the first 20 physical PDF pages of 5B, 39 ADT sections, Albanian and English.

## Decision

**Keep the original Sol standard output as the accepted book and recommended workflow. Economy is not working well enough for this use case and is on hold for release.** The user found the mixed economy output messy and preferred the Sol output again after reviewing the Terra-only retry. Technical test results do not override that visual acceptance decision.

The accepted output is `5B pg1-20/repaired-adt/` in this workspace. The two economy jobs remain experimental evidence, not approved alternatives. Do not replace the standard output with either job or describe economy as quality-equivalent or production-ready. This note does not publish a release, modify the installed plugin, remove experimental routing code, or change the accepted book.

## What the trials showed

| Run | Outcome | Evidence and limits |
| --- | --- | --- |
| Standard, Sol-led | Accepted; preferred visual result | The user's original review and final comparison selected this output. Acceptance is specific to this book, not universal accessibility certification. |
| Mixed economy, Luna/Terra with Sol coordination and escalation | Rejected for visual quality | Recorded defects included a competing oversized cover panel, clipped icon-key heading and overlapping labels, inconsistent type and spacing, repeated borders/icons/controls, uneven or cropped images, and misplaced page 18 content. |
| Terra-only substantive work, with separate Sol launch/status relay | Rejected relative to standard | Terra performed a new source-guided presentation pass and reported fixing identified defects. The user still preferred standard. No new page-by-page defect list was supplied for the final Terra output; the earlier mixed-run defects must not all be attributed to it. |

The mixed economy run recorded 312 responsive captures without detected failures; the Terra retry also recorded 312. Both reported activity and reader checks passing within their documented scopes. Neither achieved the user's preferred visual result. Automated contrast checks also retained inconclusive findings (50 mixed; 44 Terra), and neither run established screen-reader conformance, complete translation/audio review or LMS certification.

## Why the economy process is not succeeding yet

**Observed: technical checks did not measure enough of the required visual quality.** Overflow, route, binding, interaction and accessibility scans can pass while hierarchy, composition, spacing, typography and image treatment remain less effective than the accepted reference. A capture count establishes coverage of automated observations; it does not establish design quality.

**Observed: model self-review and comparison sheets did not predict user acceptance.** The Terra pass included visual review of scaled desktop/phone sheets and representative full-size live checks. The user still rejected it relative to Sol. We need an explicit human visual acceptance gate before declaring a budget output successful; additional automated passes alone have not solved the issue.

**Observed: the mixed run needed substantial Sol work.** Its cost report attributed $10.48 of an $11.23 telemetry snapshot to Sol coordination, repair and escalation. The intended budget routing did not remove most Sol work. It also introduced handoffs and integration work. The Terra-only retry shows that handoffs alone cannot explain the quality gap: removing substantive Sol/Luna work did not produce an accepted replacement.

**Working hypothesis: visual judgment and source interpretation are the difficult parts to transfer.** The mixed-run defect pattern suggests that matching each PDF page family to a coherent, reusable web component system requires more than structurally valid CSS and HTML. The trials support keeping Sol responsible for this work today. They do not isolate model capability from prompts, implementation choices, review granularity or process design, and they do not prove Terra or Luna can never help.

**Observed: a lower model rate did not establish a lower cost for an acceptable result.** Coordination, retries, new adapters, test-harness work and review consume usage. An output requiring rejection or another repair pass is not equivalent completion. There is no reliable measured cost receipt for the original standard run, so a savings percentage against it cannot be claimed.

## Recorded cost context

These are historical API-equivalent estimates from Codex telemetry, not invoices or charges to UNICEF API credits. They exclude work after their recorded snapshots and are not new pricing quotations.

- Mixed economy: $11.23 measured snapshot; its report estimated about $12 allowing for final reporting.
- Terra-only: $8.05 substantive Terra snapshot, with $3.19 separately attributed to the Sol launch/status relay, approximately $11.24 combined. Relay attribution is an upper bound. Existing activity helpers and tests were reused; this was not a cold benchmark.
- Standard: reliable retrospective cost unavailable. No accepted economy saving has been demonstrated.

## What to keep and what to defer

Keep standard as the recommended release route. Preserve useful deterministic efficiencies: extract source assets once, share approved components across languages, group repeated fixes, retain provenance and saved-state contracts, and reuse validation only when its dependencies still match. These optimizations do not require changing the design model.

Defer economy release and further whole-book budget-model trials for now. If revisited, begin with a small, representative set of difficult pages and require user acceptance against the Sol reference before scaling. Test extraction, inventory or report formatting as separate bounded tasks first. A proposed worker assignment is not a validated saving until its output passes the same acceptance criteria and total cost includes failed attempts, coordination and review.

## Local evidence

Paths below are relative to the workspace root. The corresponding reports remain historical run records; this decision supersedes any suggestion that passing their tests made the economy output accepted.

- Accepted book: `5B pg1-20/repaired-adt/`
- Standard report: `5B pg1-20/5B ADT Review and Repair Report.pdf`
- Mixed run and cost report: `5B economy-v1.1.0/README.md`, `Economy Cost Report.md`
- Terra run report: `5B terra-only-v1.1.0/5B Terra-only Review and Cost Report.md`
- Recorded mixed-run defects: `5B terra-only-v1.1.0/reports/audit.md`
- Three-way visual examples: `5B terra-only-v1.1.0/reports/visual-review/comparison-cover.jpg`, `comparison-icon-key.jpg`, `comparison-practice.jpg`

This document is also saved alongside the accepted standard book as `5B pg1-20/5B Model Evaluation and Release Decision.md`.
