# Local setup and commands

Requires Python 3.10+, Node.js 20+, npm, and Poppler (`pdftoppm`, `pdftotext`). Use an existing suitable runtime or install the plugin dependencies in an isolated environment. Do not hardcode another user's cache path or install packages globally as a shortcut.

From the plugin directory containing `plugin.json`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
npx playwright install chromium
.venv/bin/python skills/adt-pdf-restyle/scripts/doctor.py
```

On Windows, use `.venv\Scripts\python.exe`. Install Poppler separately using the team's normal package manager. On Linux, Playwright may also need operating-system browser dependencies. `ADT_CHROME` can point at an existing compatible Chromium executable instead of downloading one.

All commands below run from the plugin directory. Use absolute user input/output paths when the working directory is uncertain. Store jobs outside the installed plugin, which may be read-only.

```sh
.venv/bin/python skills/adt-pdf-restyle/scripts/prepare_job.py \
  --adt /path/to/book.zip --pdf /path/to/source.pdf \
  --notes /path/to/reviewer-notes.docx --pages 1-20 --out /path/to/job
```

`--notes` can be repeated or omitted. `--pages` defaults to all physical PDF pages and also accepts comma-separated ranges. `--mode audit` prepares an audit-only job. Original source documents remain at their original paths; notes are copied and hashed. Keep the source PDF available for rendering. The job contains `baseline`, `repaired-adt`, `notes`, `reports`, and `job.json`.

```sh
.venv/bin/python skills/adt-pdf-restyle/scripts/inventory.py \
  --adt /path/to/job/baseline --pdf /path/to/source.pdf \
  --out /path/to/job/reports/baseline.json
node skills/adt-pdf-restyle/scripts/check-bundle.mjs /path/to/job/repaired-adt
node skills/adt-pdf-restyle/scripts/regen-preloader.mjs /path/to/job/repaired-adt
node skills/adt-pdf-restyle/scripts/browser-audit.mjs \
  --adt /path/to/job/repaired-adt --out /path/to/job/reports/browser
.venv/bin/python skills/adt-pdf-restyle/scripts/build_report.py \
  --job /path/to/job --out /path/to/job/ADT-Review-and-Repair-Report.pdf
```

Do not run the cache writer in audit mode. Only run it after planned, authorized changes, in the working copy. It updates the existing `var INLINE` JSON payload and retains the surrounding loader code. Unsupported formats require the bundle's own packager or an inspected adapter.

`browser-audit.mjs` serves only the supplied ADT on loopback with an ephemeral port and closes its browser/server on completion. It uses a fresh browser context per language and the Studio `currentLanguage` preference; verify that preference in the actual runtime. The tool attempts language selection but does not assert successful catalog application. Confirm language switching separately. `--file` captures direct-file loading; it does not prove a reader's save/submit behaviors. Run behavioral checks appropriate to the actual bundle using the available browser tools.

To compare before/after contracts:

```sh
.venv/bin/python skills/adt-pdf-restyle/scripts/inventory.py \
  --adt /path/to/job/repaired-adt --compare /path/to/job/reports/baseline.json \
  --out /path/to/job/reports/after.json
```

Intentional changes produce failures until reviewed. `--allow-change relative/path` records an explicit file exception; it is not a waiver of global ID, source or browser checks. Keep reasons in the issue/change register. Existing bundle versions differ; inspect the actual format rather than changing it to satisfy a helper's assumptions.
