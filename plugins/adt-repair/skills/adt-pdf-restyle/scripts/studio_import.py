#!/usr/bin/env python3
"""Prepare, check and package a separate Studio-import handoff; never run TTS.

Repairs are book-specific work performed by the agent under the import contract.
This helper records evidence; a successful preflight is not round-trip fidelity.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def tree(root):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Bundle must be self-contained without symlinks.')
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def checker():
    spec = importlib.util.spec_from_file_location('studio_preflight', Path(__file__).with_name('check_studio_import.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state(job):
    data = json.loads((job / 'studio-handoff.json').read_text())
    if data.get('bundle') != 'studio-import-adt':
        raise ValueError('Unrecognized handoff bundle path.')
    return data


def save(job, data):
    data['updated_at'] = now()
    write(job / 'studio-handoff.json', data)


def prepare(adt, out):
    adt, out = adt.resolve(), out.resolve()
    if not (adt / 'content/pages.json').is_file():
        raise ValueError('Supply an extracted repaired ADT containing content/pages.json.')
    if out.exists() or out.is_relative_to(adt) or adt.is_relative_to(out):
        raise ValueError('Choose a new output directory separate from the repaired book.')
    files = tree(adt)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='studio-prepare-', dir=out.parent) as temp:
        staging = Path(temp) / 'job'
        staging.mkdir()
        shutil.copytree(adt, staging / 'studio-import-adt')
        manifest = Path(__file__).resolve().parents[3] / 'plugin.json'
        version = json.loads(manifest.read_text())['version'] if manifest.is_file() else 'unpackaged'
        data = {'schema_version': 1, 'tool_version': version, 'created_at': now(),
                'source': str(adt), 'bundle': 'studio-import-adt',
                'target': {'pull_request': 'https://github.com/unicef/adt-studio/pull/803', 'branch': 'issue-705'},
                'stages': {'preflight': 'not-run', 'preview': 'not-run', 'roundtrip': 'not-run', 'tts': 'not-run'},
                'differences': [], 'runtime_followups': [],
                'warning_dispositions': [],
                'scope': 'Prepare a new-project recovery archive; no existing project merge or paid speech generation.'}
        write(staging / 'reports/repaired-source-files.json', files)
        save(staging, data)
        if tree(adt) != files:
            raise ValueError('Source changed during preparation; retry from a stable accepted book.')
        staging.rename(out)
    return data


def check(job):
    data = state(job)
    result = checker().inspect(job / data['bundle'])
    result['checked_at'] = now()
    write(job / 'reports/studio-preflight.json', result)
    data['stages']['preflight'] = 'failed' if result['errors'] else 'passed'
    receipt_path = job / 'reports/studio-package.json'
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        archive = job / 'studio-import.zip'
        if tree(job / data['bundle']) != receipt['files'] or not archive.is_file() or sha(archive) != receipt['sha256']:
            data['stages']['preview'] = 'stale'
            data['stages']['roundtrip'] = 'stale'
    save(job, data)
    return result


def package(job):
    result = check(job)
    if result['errors']:
        raise ValueError(f"Preflight has {len(result['errors'])} errors; see reports/studio-preflight.json.")
    data = state(job)
    dispositions = data.get('warning_dispositions', [])
    if any(not any(d.get('warning') == warning and d.get('explanation', '').strip() for d in dispositions)
           for warning in result['warnings']):
        raise ValueError('Explain every remaining warning in studio-handoff.json warning_dispositions before packaging.')
    bundle = job / data['bundle']
    files = tree(bundle)
    destination = job / 'studio-import.zip'
    with tempfile.NamedTemporaryFile(prefix='studio-package-', suffix='.zip', dir=job, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted(files):
                info = zipfile.ZipInfo(relative, date_time=(2026, 11, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (bundle / relative).read_bytes())
        if tree(bundle) != files:
            raise ValueError('Bundle changed during packaging; repeat preflight and package.')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    receipt = {'created_at': now(), 'archive': destination.name, 'sha256': sha(destination), 'files': files}
    write(job / 'reports/studio-package.json', receipt)
    data['stages']['preview'] = 'not-run'
    data['stages']['roundtrip'] = 'not-run'
    data['package_sha256'] = receipt['sha256']
    save(job, data)
    return receipt


def verify_package(job):
    data = state(job)
    receipt = json.loads((job / 'reports/studio-package.json').read_text())
    archive = job / 'studio-import.zip'
    if sha(archive) != receipt['sha256'] or tree(job / data['bundle']) != receipt['files']:
        raise ValueError('Package or working files changed; rerun preflight and packaging before preview.')
    return archive, receipt


def preview_result(status, response):
    compatibility, activities = response.get('compatibility'), response.get('activityReview')
    return bool(status == 200 and response.get('isAdtBundle') is True
                and isinstance(compatibility, dict) and compatibility.get('supported') is True
                and compatibility.get('issues') == [] and isinstance(activities, dict)
                and type(activities.get('needsReviewCount')) is int and activities['needsReviewCount'] == 0)


def narration(job, baseline):
    """Report changed/missing speech inputs without modifying catalogs or media."""
    data = state(job)
    bundle = job / data['bundle']
    baseline = baseline.resolve()
    if not (baseline / 'content/i18n').is_dir():
        raise ValueError('Supply the original pre-repair baseline containing content/i18n.')
    entries, evidence = [], {}
    def catalog(root, language, name):
        file = root / 'content/i18n' / language / name
        if not file.is_file():
            return {}
        evidence[str(file)] = sha(file)
        result = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(result, dict):
            raise ValueError('Expected a catalog object: ' + str(file))
        return result
    for locale in sorted((bundle / 'content/i18n').iterdir()):
        if not locale.is_dir():
            continue
        language = locale.name
        before = catalog(baseline, language, 'texts.json')
        old_audio = catalog(baseline, language, 'audios.json')
        old_speech = catalog(baseline, language, 'speech_texts.json')
        after = catalog(bundle, language, 'texts.json')
        audio = catalog(bundle, language, 'audios.json')
        speech = catalog(bundle, language, 'speech_texts.json')
        for key, text in after.items():
            if not isinstance(text, str) or not text.strip():
                continue
            changed = key in before and text != before[key]
            missing = key not in audio or not (locale / 'audio' / str(audio[key])).is_file()
            new = key not in before
            if not (changed or missing or new):
                continue
            if not (changed or new or key in old_audio):
                continue  # Existing, intentionally un-narrated label.
            stale_provider_input = changed and key in speech and speech[key] == old_speech.get(key) and speech[key] != text
            entries.append({'language': language, 'id': key, 'display_before': before.get(key),
                            'display_after': text, 'speech_before': old_speech.get(key),
                            'speech_after': speech.get(key, text), 'display_changed': changed,
                            'new_id': new, 'audio_missing': missing,
                            'provider_input_needs_review': stale_provider_input,
                            'kind': 'required-regeneration' if changed and key in old_audio else 'review-narration-policy',
                            'timings': 'regenerate alignment when recording changes' if changed or missing else 'verify retained alignment',
                            'status': 'pending'})
    result = {'schema_version': 1, 'created_at': now(), 'tts': 'not-run', 'baseline': str(baseline),
              'catalog_hashes': evidence, 'entries': entries,
              'required_regeneration_count': sum(e['kind'] == 'required-regeneration' for e in entries),
              'limitations': ['Candidate list requires intended narration policy and repair change records.',
                              'Agent-added ID clones can be new labels rather than new narration.',
                              'No catalog, audio, timing file, provider or voice was modified.']}
    write(job / 'reports/narration-plan.json', result)
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Studio preview redirected; supply the actual API origin explicitly.')


def preview(job, studio_url):
    data = state(job)
    archive, receipt = verify_package(job)
    origin = urllib.parse.urlsplit(studio_url)
    if origin.scheme not in {'http', 'https'} or not origin.netloc or origin.username or origin.password or origin.query or origin.fragment or origin.path not in {'', '/'}:
        raise ValueError('Supply an explicit Studio API origin, e.g. http://localhost:3003 (no credentials or path).')
    url = studio_url.rstrip('/') + '/api/books/preview-import'
    boundary = 'adt-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="zip"; filename="studio-import.zip"\r\n'
            'Content-Type: application/zip\r\n\r\n').encode() + archive.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    data['stages']['preview'] = 'not-run'
    save(job, data)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=120) as response:
            status, payload = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status = error.code
        try:
            payload = json.load(error)
        except (ValueError, OSError):
            payload = {'error': 'Studio rejected preview without a JSON result.'}
    except (OSError, ValueError) as error:
        data['stages']['preview'] = 'unavailable'
        write(job / 'reports/studio-preview.json', {'checked_at': now(), 'endpoint': url,
              'archive_sha256': receipt['sha256'], 'http_status': None, 'passed': False,
              'error': str(error)})
        save(job, data)
        raise ValueError('Studio preview unavailable; import has not been verified: ' + str(error)) from error
    passed = isinstance(payload, dict) and preview_result(status, payload)
    evidence = {'checked_at': now(), 'endpoint': url, 'archive_sha256': receipt['sha256'],
                'http_status': status, 'passed': passed, 'response': payload}
    write(job / 'reports/studio-preview.json', evidence)
    data['stages']['preview'] = 'passed' if passed else 'failed'
    save(job, data)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--adt', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    for name in ['check', 'package', 'preview', 'narration']:
        p = sub.add_parser(name)
        p.add_argument('--job', type=Path, required=True)
        if name == 'preview':
            p.add_argument('--studio-url', required=True)
        elif name == 'narration':
            p.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.adt, args.out)
        elif args.command == 'check':
            result = check(args.job)
        elif args.command == 'package':
            receipt = package(args.job)
            result = {key: value for key, value in receipt.items() if key != 'files'}
        elif args.command == 'narration':
            plan = narration(args.job, args.baseline)
            result = {'required_regeneration_count': plan['required_regeneration_count'],
                      'candidate_count': len(plan['entries']), 'tts': plan['tts']}
        else:
            evidence = preview(args.job, args.studio_url)
            result = {key: value for key, value in evidence.items() if key != 'response'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'check' and result['errors'] or args.command == 'preview' and not result['passed']:
            parser.exit(1)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
