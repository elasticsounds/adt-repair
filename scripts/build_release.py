#!/usr/bin/env python3
"""Build versioned archives from an explicit allowlist, excluding books and local dependencies."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/adt-repair'
ROOT_FILES = ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', '.gitignore',
              '.agents/plugins/marketplace.json', '.github/workflows/checks.yml',
              'scripts/build_release.py', 'scripts/validate_package.py',
              'docs/public-directory.md', 'docs/PRIVACY.md', 'docs/execution-modes.md', 'docs/economy-evaluation.md',
              'docs/studio-reimport.md',
              'tests/test_helpers.py', 'tests/test_workflow.py', 'tests/test_studio_import.py', 'tests/browser-smoke.mjs', 'tests/studio-style-smoke.mjs']
PLUGIN_FILES = ['plugin.json', 'package.json', 'package-lock.json', 'requirements.txt',
                'assets/icon.svg',
                'skills/adt-pdf-restyle/SKILL.md', 'skills/adt-pdf-restyle/agents/openai.yaml',
                'skills/adt-pdf-restyle/references/setup.md',
                'skills/adt-pdf-restyle/references/reporting.md',
                'skills/adt-pdf-restyle/references/execution-modes.md',
                'skills/adt-pdf-restyle/references/studio-integration.md',
                'skills/adt-pdf-restyle/references/studio-reimport.md',
                'skills/adt-pdf-restyle/references/studio-import-contract.md',
                'skills/adt-pdf-restyle/references/adt-bundle-architecture.md',
                'skills/adt-pdf-restyle/scripts/prepare_job.py',
                'skills/adt-pdf-restyle/scripts/inventory.py',
                'skills/adt-pdf-restyle/scripts/doctor.py',
                'skills/adt-pdf-restyle/scripts/build_report.py',
                'skills/adt-pdf-restyle/scripts/workflow.py',
                'skills/adt-pdf-restyle/scripts/studio_import.py',
                'skills/adt-pdf-restyle/scripts/studio_styles.mjs',
                'skills/adt-pdf-restyle/scripts/check_studio_import.py',
                'skills/adt-pdf-restyle/scripts/check-bundle.mjs',
                'skills/adt-pdf-restyle/scripts/regen-preloader.mjs',
                'skills/adt-pdf-restyle/scripts/browser-audit.mjs']


def archive(destination, files):
    records = []
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for source, relative in sorted(files, key=lambda pair: pair[1]):
            if source.is_symlink() or not source.is_file():
                raise ValueError('Missing or symlink release input: ' + str(source))
            data = source.read_bytes()
            if b'/' + b'Users/' in data or re.search(rb'(?:gh[o_ps]_[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,})', data):
                raise ValueError('Machine path or credential-like content in ' + relative)
            info = zipfile.ZipInfo(relative, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, data)
            records.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return {'archive': destination.name, 'bytes': destination.stat().st_size,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'files': records}


def main():
    from validate_package import validate
    validate()
    version = json.loads((PLUGIN / 'plugin.json').read_text())['version']
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    plugin_files = PLUGIN_FILES + (['LICENSE'] if (PLUGIN / 'LICENSE').is_file() else [])
    root_files = ROOT_FILES + (['LICENSE'] if (ROOT / 'LICENSE').is_file() else [])
    receipts = [archive(dist / f'adt-repair-plugin-v{version}.zip', [(PLUGIN / f, f) for f in plugin_files]),
                archive(dist / f'adt-repair-marketplace-v{version}.zip',
                        [(ROOT / f, f) for f in root_files] + [(PLUGIN / f, 'plugins/adt-repair/' + f) for f in plugin_files])]
    (dist / 'release-manifest.json').write_text(json.dumps({'version': version, 'artifacts': receipts}, indent=2) + '\n')
    (dist / 'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['archive']}\n" for r in receipts))
    for receipt in receipts:
        print(f"{receipt['archive']}: {receipt['bytes']} bytes, {len(receipt['files'])} files")


if __name__ == '__main__':
    main()
