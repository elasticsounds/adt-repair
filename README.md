# ADT Repair

**ADT Repair — a Codex plugin for auditing and repairing an existing Accessible Digital Textbook using its source PDF. Standard (Sol-led) is the recommended workflow.**

**Evaluation decision:** the user preferred the original Sol standard output over both the mixed economy and Terra-only trials on 5B. Economy is experimental and on hold for release; the prepared v1.1.0 economy build is not an approved replacement. See the [findings and release decision](docs/economy-evaluation.md).

**Version 1.2.1:** adds a final [Studio reimport preparation stage](docs/studio-reimport.md). It preserves the accepted reader and creates a separate import ZIP and narration handoff for Studio PR #803. Compatibility, round-trip fidelity and TTS completion are reported independently. Paid TTS is not automatic. The fidelity correction preserves variable borders, activity startup, reset controls and compiled interactive states. The 5B round trip also needs the separately tested Studio fixes; those are not published upstream or included in the MIT plugin.

Give Codex an ADT folder or ZIP, the original PDF, and optionally notes from teachers or reviewers. ADT Repair guides source comparison, layout and asset repairs, activity checks, accessibility review, and a standalone PDF report alongside the repaired book.

This is an agent skill with local helper scripts. Codex performs the analysis and develops book-specific repairs. It is not a one-command automatic converter, an accessibility certification, or a replacement reader.

## Install

Use a recent Codex desktop/CLI version with plugin marketplace support:

```sh
codex plugin marketplace add elasticsounds/adt-repair --ref v1.2.1
codex plugin add adt-repair@elasticsounds-adt
```

Open the desktop app's Plugins directory, choose the **ADT Repair** marketplace and install **ADT Repair**. Refresh/restart the client if the source does not appear. Installation surfaces vary by client version and workspace policy. This GitHub marketplace is separate from the public OpenAI Plugin Directory.

Alternatively, download the **marketplace ZIP** from [Releases](https://github.com/elasticsounds/adt-repair/releases), extract it, and register the extracted directory:

```sh
codex plugin marketplace add /absolute/path/to/extracted-marketplace
```

The GitHub command pins v1.2.1. You can also download the v1.2.1 marketplace ZIP from [its release](https://github.com/elasticsounds/adt-repair/releases/tag/v1.2.1) and use the local-directory installation command. The older v1.0.1 release remains available for rollback. Economy is experimental and is not an approved production route.

The smaller **plugin ZIP** contains the standalone plugin with `plugin.json` at its root; it is intended for plugin packaging/submission workflows. To install only the skill manually, copy its `skills/adt-pdf-restyle` folder into your Codex skills directory and follow its setup reference. Keep the sibling plugin `requirements.txt`, `package.json` and lockfile available for dependency setup, or install their declared versions in your own environment.

For local prerequisites and commands see [setup](plugins/adt-repair/skills/adt-pdf-restyle/references/setup.md). The tool requires Python 3.10+, Node.js 20+, Poppler and a Chromium browser for automated captures. It does not bundle these runtimes.

## Use

Open a local Codex chat in a workspace containing the book and say:

```text
Use $adt-pdf-restyle to audit and repair this ADT.

ADT: /path/to/book.zip
Source PDF: /path/to/source.pdf
Teacher/reviewer notes: /path/to/review-notes.docx (optional)
Pages: all
Output: /path/to/repair-job
Execution mode: standard
Operation: repair

Preserve the existing reader, languages, navigation, activity behavior and
saved responses. Deliver the repaired ADT and one shareable review PDF.
```

When your client exposes namespaced plugin skills, select **ADT Repair → PDF-guided ADT repair** from its skill picker. You can also request an `audit` operation, limit the physical PDF pages, or paste reviewer notes directly into the chat.

Use **standard** at startup. The source retains experimental **economy** routing for explicitly requested trials: bounded analysis to GPT-6 Luna and repairs to GPT-6.1 Terra, with GPT-6.1 Sol for design decisions, high-risk changes, escalation and final review. Its intended coverage and quality gates did not establish visual equivalence in the 5B trials. Worker model controls and availability are required; a skill cannot switch models by itself. Missing budget models are reported instead of silently charging Sol work as economy.

See the [evaluation findings](docs/economy-evaluation.md) for the two trials and the [original economy design](docs/execution-modes.md) for intended routing and optimizations. The user rejected both economy outputs relative to standard; no cost saving for an accepted equivalent output has been demonstrated. `audit` versus `repair` remains a separate operation.

Examples of later changes:

- “Remove the decorative yellow right-hand bar across the whole book.”
- “Make this image 60% of the content width on desktop; retain a usable phone layout.”
- “Apply the teacher's notes to sections 12–18 and report the outcome of each comment.”

Include page/element identity, language, reading variant and scope when annotating. Accepted edits must be preserved in the book's editable source or override configuration so a later rebuild does not discard them. Custom annotation controls are not included in v1; normal Codex annotations can supply change requests.

## Outputs

- Untouched baseline and a separate repaired ADT folder/ZIP.
- A separately labeled Studio-import folder/ZIP, import gate evidence, ID/catalog migration records, differences/runtime follow-ups and narration regeneration plan. Studio preview requires a compatible reachable build; actual TTS is a separate requested action.
- A standalone **ADT Review and Repair Report.pdf** listing issues, fixes, reviewer-note dispositions, validation and remaining work.
- Source-page/section map, issue register and proposed section restructuring.
- Editable brand/component definitions, extracted-asset provenance and change records.
- Responsive screenshots, automated accessibility findings and documented behavioral checks.

The audit operation leaves the working ADT unchanged. PDF page numbers mean physical pages, starting at 1. Existing translated content is preserved and checked; full translation rewriting and new narration are separate work.

## What v1 protects

The workflow preserves routes, stable content/image IDs, localization bindings, reader controls, activity identity and saved-response contracts. It inspects the actual bundle rather than replacing compiled reader code. Repairs are validated against the source and real runtime; intentional departures requested by reviewers are documented.

Teacher/reviewer notes are optional. Each actionable comment is mapped to affected scope and tracked as addressed, partially addressed, needing clarification, not applied or out of scope. Unreadable notes and material conflicts remain visible in the report.

## Validation and limitations

The original workflow was exercised on one 20-page, two-language ADT pilot containing 39 sections. That book and its assets are not distributed here. Release helper tests use synthetic fixtures; they do not establish fidelity on every book or Studio version.

Static checks and browser scans catch specific errors. They do not establish screen-reader conformance, linguistic accuracy, audio correctness, LMS integration or working grading/persistence. Those need explicit checks and evidence. Inconclusive accessibility results remain inconclusive. A Studio re-export can overwrite export-only repairs; retain the change log and editable source.

## Privacy and usage cost

This plugin runs local scripts and has no hosted service, telemetry endpoint, MCP server or bundled API key. However, Codex may send supplied text, images and tool results to the model under your account's configuration. Local processing does not mean the model operates offline. Review your team's data policy before supplying books or notes.

Read the [privacy policy](docs/PRIVACY.md). Support is available through [GitHub Issues](https://github.com/elasticsounds/adt-repair/issues); do not include private source material in a public issue.

Model usage is charged to the user's Codex allowance or API account. No fixed price is guaranteed. Shared templates, targeted reruns and compact evidence can reduce usage; record actual tokens and cost when available.

## Development and releases

From `plugins/adt-repair`, install the pinned dependencies as described in setup. Then, from the repository root:

```sh
plugins/adt-repair/.venv/bin/python -m unittest discover -s tests -v
plugins/adt-repair/.venv/bin/python scripts/build_release.py
```

Release ZIPs use an explicit file list, exclude dependencies/book data and include SHA-256 receipts. See [CHANGELOG](CHANGELOG.md), [contribution guidance](CONTRIBUTING.md) and the [public-directory plan](docs/public-directory.md).

## License

MIT — see [LICENSE](LICENSE). The license covers this tool, not the textbooks or reviewer materials supplied to it. Dependencies retain their own licenses.
