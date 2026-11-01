#!/usr/bin/env python3
"""Check local prerequisites without installing packages or changing configuration."""
import importlib.metadata
import json
import shutil
import subprocess
import sys


def main():
    results = {'python': sys.version.split()[0], 'packages': {}, 'commands': {}}
    failed = sys.version_info < (3, 10)
    for name in ['pypdf', 'Pillow', 'reportlab']:
        try:
            results['packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            results['packages'][name] = None
            failed = True
    for name in ['node', 'npm', 'pdftoppm', 'pdftotext']:
        results['commands'][name] = shutil.which(name)
        failed |= results['commands'][name] is None
    if results['commands']['node']:
        major = int(subprocess.check_output(['node', '--version'], text=True).strip().lstrip('v').split('.')[0])
        failed |= major < 20
        results['node_major'] = major
    results['passed'] = not failed
    results['note'] = 'Browser validation also requires the plugin npm dependencies and a Playwright Chromium install or ADT_CHROME.'
    print(json.dumps(results, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
