# Changelog

## 1.2.1 — reimport fidelity fixes

Preserve CSS variable shorthands, compile and prioritize interactive/responsive states in the import copy, and retain custom-activity startup and reset controls. Keep report section headings with their first finding. Add a real-browser regression fixture and require visual/state comparisons before and after import. Studio-side grading, quiz and reset fixes are an independently tested local experiment, not bundled or published upstream. Standard remains Sol-led; economy remains experimental and is not approved for production. This GitHub release includes the final Studio handoff stage from the unpublished v1.2.0 work; it does not publish the separate Studio patch or update the public plugin-directory draft.

## 1.2.0 — prepared locally, Studio reimport stage

- Add Studio reimport preparation as the final repair stage, preserving the accepted reader and creating a separate import copy/ZIP for PR #803 (`issue-705`). Audit-only jobs report risks without converting the book.
- Add a versioned import contract, extended standard-library preflight, isolated preparation, warning dispositions, deterministic packaging and hash-bound Studio preview evidence. Reject stale packages and distinguish preview acceptance from round-trip fidelity.
- Require ID/image/catalog migration records, supported section-level styling and custom-activity behavior, explicit runtime/quiz differences, and a per-language narration plan. Paid TTS is not automatic; speech-input freshness, regenerated alignment and post-export checks remain separate gates.
- Include import evidence and limitations in the standalone report, package the new references/helpers, and add synthetic preservation and acceptance-gate tests.
- Verify requested language/catalog samples during captures; record narration candidates without modifying media. The 5B trial passed import preview but exposed Studio-side grader recovery and generated-quiz regressions, so round-trip acceptance remains blocked and the Sol reader remains the accepted book.
- Keep Standard Sol-led and recommended. Economy routing remains experimental and on hold; neither 5B economy trial met the user's visual acceptance standard.

Prior published releases and existing ADT outputs remain available for rollback. The v1.2.0 preparation did not publish a separate GitHub release, update the public directory, modify an installed skill, or regenerate narration. Its tool changes are included in v1.2.1.

## 1.1.0 — prepared, not yet published

**Release hold:** after reviewing the mixed economy and Terra-only 5B trials, the user selected the original Sol standard output. Economy is experimental and not approved for release. See [findings](docs/economy-evaluation.md); the entries below describe prepared work, not accepted visual equivalence.

- Name the existing Sol-led workflow standard; require new jobs to explicitly select standard or economy at startup, separate from the audit/repair operation.
- Add economy routing for GPT-6 Luna triage, GPT-6.1 Terra bounded implementation, and GPT-6.1 Sol design, high-risk decisions, escalation and final review. Keep full coverage and quality gates in both modes.
- Add local dispatch/attempt and optional usage records, bounded escalation, and dependency/hash-checked evidence reuse. Helpers plan and record; model-aware Codex tools perform actual handoffs.
- Share source analysis and components across languages, group repeated defects, and limit handoff context. Preserve each note and affected section's verification evidence.
- Avoid duplicate HTML hashing, a third ZIP extraction copy, and repeated growing browser-results rewrites; retain incremental JSONL capture evidence and final JSON compatibility.
- Include execution mode and recorded model attempts in the shareable report. Document the standard pilot's limits and a controlled economy benchmark; no measured cost saving or book-level equivalence is claimed yet.

## 1.0.1 — 2026-11-01

Directory submission preparation: shorter listing subtitle, square book/check icon, expanded description and starter prompts, privacy policy and support links. Package validation now checks listing limits and branding assets. Prepared jobs record the manifest's actual tool version.

Public directory submission and approval are separate from the GitHub release; the current submission status is recorded in docs/public-directory.md.

## 1.0.0 — 2026-11-01

First shareable release of the PDF-guided ADT repair workflow.

- ADT folder/ZIP and source PDF inputs; optional teacher/reviewer notes and physical page ranges.
- Isolated job preparation with source hashes and original-note preservation.
- Full source/section inventory, source mapping, template classification and issue/restructure proposals.
- Preservation guidance for localization, navigation, audio, activities, offline loading and saved responses.
- Stable-control inventory, Studio static checks and loader-preserving offline-payload regeneration.
- All-section, all-language responsive screenshot/accessibility helper with explicit limitations.
- Evidence-driven standalone PDF report builder including reviewer-note dispositions.
- Versioned Codex marketplace, portable plugin manifest and reproducible release archives.

Validation scope: the source workflow was demonstrated on one 20-page, two-language, 39-section pilot; release helpers use synthetic regression fixtures. More book families and lower-cost model routing remain future validation work.
