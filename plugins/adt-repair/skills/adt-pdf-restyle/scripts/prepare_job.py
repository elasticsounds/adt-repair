#!/usr/bin/env python3
"""Prepare an isolated ADT repair job; never edit the supplied book or notes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def reject_symlinks(root):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('ADT input contains a symlink; supply a self-contained folder.')


def extract_zip(source, target, max_bytes):
    with zipfile.ZipFile(source) as archive:
        names = set()
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            mode = info.external_attr >> 16
            if ('\\' in name or path.is_absolute() or '..' in path.parts
                    or ':' in name or not name or stat.S_ISLNK(mode)):
                raise ValueError('Unsafe ZIP member: ' + name)
            if path in names:
                raise ValueError('Duplicate ZIP member: ' + name)
            names.add(path)
        if sum(i.file_size for i in archive.infolist()) > max_bytes:
            raise ValueError('ZIP exceeds --max-extracted-gb; inspect it before raising the limit.')
        archive.extractall(target)


def find_root(folder):
    candidates = [p.parent.parent for p in folder.rglob('content/pages.json')
                  if '__MACOSX' not in p.parts]
    if (folder / 'content/pages.json').is_file() and folder not in candidates:
        candidates.append(folder)
    if len(candidates) != 1:
        raise ValueError(f'Expected one ADT root containing content/pages.json; found {len(candidates)}.')
    return candidates[0]


def parse_pages(value, count):
    if value == 'all':
        return list(range(1, count + 1))
    pages = set()
    for part in value.split(','):
        bounds = part.strip().split('-')
        if len(bounds) == 1:
            first = last = int(bounds[0])
        elif len(bounds) == 2:
            first, last = map(int, bounds)
        else:
            raise ValueError('Use physical page numbers such as 1-20 or 1-4,8,12-15.')
        if not 1 <= first <= last <= count:
            raise ValueError(f'Page range must be within physical PDF pages 1-{count}.')
        pages.update(range(first, last + 1))
    return sorted(pages)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(adt, pdf, out, notes=(), pages='all', mode='repair', max_gb=4,
            execution_mode='standard'):
    from pypdf import PdfReader
    if execution_mode not in {'standard', 'economy'}:
        raise ValueError('Execution mode must be standard or economy.')
    if mode not in {'audit', 'repair'}:
        raise ValueError('Operation must be audit or repair.')
    adt, pdf, out = adt.resolve(), pdf.resolve(), out.resolve()
    if out.exists():
        raise ValueError('Output already exists; choose a new job folder to avoid overwriting work.')
    if not adt.exists() or not pdf.is_file():
        raise ValueError('ADT input and source PDF must exist.')
    if adt.is_dir() and (out.is_relative_to(adt) or adt.is_relative_to(out)):
        raise ValueError('Output and ADT input must be separate directories.')
    selected = parse_pages(pages, len(PdfReader(str(pdf)).pages))
    note_paths = [Path(p).resolve() for p in notes]
    if any(not p.is_file() for p in note_paths):
        raise ValueError('Each --notes argument must identify a file.')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='adt-prepare-', dir=out.parent) as temp:
        staging = Path(temp)
        extracted = staging / 'unpacked'
        if adt.is_dir():
            reject_symlinks(adt)
            source_root = find_root(adt)
        elif zipfile.is_zipfile(adt):
            extracted.mkdir()
            extract_zip(adt, extracted, int(max_gb * 1024 ** 3))
            source_root = find_root(extracted)
        else:
            raise ValueError('ADT input must be a folder or ZIP.')
        job = staging / 'job'
        job.mkdir()
        if adt.is_dir():
            shutil.copytree(source_root, job / 'baseline')
        else:
            # The temporary extraction is disposable; move it instead of a third full copy.
            shutil.move(str(source_root), job / 'baseline')
        shutil.copytree(job / 'baseline', job / 'repaired-adt')
        (job / 'reports').mkdir()
        (job / 'notes').mkdir()
        copied_notes = []
        for index, source in enumerate(note_paths, 1):
            relative = Path('notes') / f'{index:03d}-{source.name}'
            shutil.copy2(source, job / relative)
            copied_notes.append({'source': str(source), 'copy': relative.as_posix(), 'sha256': sha256(source)})
        config = json.loads((job / 'baseline/assets/config.json').read_text(encoding='utf-8'))
        plugin_manifest = Path(__file__).resolve().parents[3] / 'plugin.json'
        tool_version = (json.loads(plugin_manifest.read_text(encoding='utf-8'))['version']
                        if plugin_manifest.is_file() else 'unpackaged')
        manifest = {
            'schema_version': 1,
            'tool_version': tool_version,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'execution_mode': execution_mode, 'operation': mode, 'mode': mode,
            'input': {'adt': str(adt), 'pdf': str(pdf), 'pdf_sha256': sha256(pdf),
                      'adt_zip_sha256': sha256(adt) if adt.is_file() else None},
            'physical_pdf_pages': selected,
            'languages': config.get('languages', {}).get('available', []),
            'notes': copied_notes, 'baseline': 'baseline', 'working_copy': 'repaired-adt',
            'stage': 'prepared',
            'final_stage': {'name': 'studio-reimport', 'status': 'pending' if mode == 'repair' else 'not-applicable'},
        }
        write_json(job / 'job.json', manifest)
        write_json(job / 'reports/issues.json', {'schema_version': 1, 'issues': []})
        write_json(job / 'reports/reviewer-notes.json', {'schema_version': 1, 'notes': []})
        write_json(job / 'reports/validation.json', {'schema_version': 1, 'checks': []})
        # Rename only after validation/copies succeed, leaving no partial job on failure.
        job.rename(out)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adt', required=True, type=Path)
    parser.add_argument('--pdf', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--notes', action='append', default=[], type=Path)
    parser.add_argument('--pages', default='all')
    parser.add_argument('--execution-mode', choices=['standard', 'economy'], required=True,
                        help='Startup cost policy; economy must be explicitly selected.')
    parser.add_argument('--operation', '--mode', dest='operation', choices=['audit', 'repair'],
                        default='repair', help='Audit or repair; --mode is a legacy alias.')
    parser.add_argument('--max-extracted-gb', type=float, default=4)
    args = parser.parse_args()
    try:
        result = prepare(args.adt, args.pdf, args.out, args.notes, args.pages,
                         args.operation, args.max_extracted_gb, args.execution_mode)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps({'job': str(args.out.resolve()), 'pages': len(result['physical_pdf_pages']),
                      'languages': result['languages'], 'note_files': len(result['notes']),
                      'execution_mode': result['execution_mode'], 'operation': result['operation']}))


if __name__ == '__main__':
    main()
