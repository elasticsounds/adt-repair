#!/usr/bin/env python3
"""Validate local release structure and references; not a substitute for portal scans."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def validate():
    from build_release import PLUGIN, PLUGIN_FILES, ROOT_FILES
    manifest = json.loads((PLUGIN / 'plugin.json').read_text())
    marketplace = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
    package = json.loads((PLUGIN / 'package.json').read_text())
    assert manifest['name'] == 'adt-repair'
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert manifest['version'] == package['version']
    assert manifest['extensions']['com.openai']['requires_local_executor'] is True
    assert not (PLUGIN / 'mcp.json').exists(), 'v1 has no MCP dependency'
    for entry in marketplace['plugins']:
        source = (ROOT / entry['source']['path']).resolve()
        assert source.is_relative_to(ROOT) and (source / 'plugin.json').is_file()
        assert entry['policy']['installation'] == 'AVAILABLE'
    for file in PLUGIN_FILES:
        assert (PLUGIN / file).is_file(), f'Missing plugin file: {file}'
    for file in ROOT_FILES:
        assert (ROOT / file).is_file(), f'Missing repository file: {file}'
    for markdown in (PLUGIN / 'skills').rglob('*.md'):
        text = markdown.read_text(encoding='utf-8')
        assert '/' + 'Users/' not in text, f'Absolute machine path: {markdown}'
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in target and not target.startswith('#'):
                assert (markdown.parent / target.split('#')[0]).is_file(), f'Broken link: {target}'
    for json_file in [PLUGIN / 'plugin.json', PLUGIN / 'package-lock.json']:
        json.loads(json_file.read_text())
    print('Package structure, references and version consistency passed.')


if __name__ == '__main__':
    validate()
