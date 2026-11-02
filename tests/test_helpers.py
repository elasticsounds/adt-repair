"""Behavioral regression tests using synthetic books; no copyrighted input assets."""
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/adt-repair/skills/adt-pdf-restyle/scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


prepare = module('prepare_job')
inventory = module('inventory')
report = module('build_report')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def fixture(root):
    from pypdf import PdfWriter
    book = root / 'source-adt'
    (book / 'assets').mkdir(parents=True)
    dump(book / 'assets/config.json', {'languages': {'available': ['sq', 'en'], 'default': 'sq'}})
    dump(book / 'content/pages.json', [{'section_id': 'pg001_sec001', 'href': 'pg001_sec001.html'}])
    dump(book / 'content/toc.json', [])
    for lang in ['sq', 'en']:
        dump(book / f'content/i18n/{lang}/texts.json', {'title': 'Synthetic lesson', 'label': 'Your response'})
    (book / 'assets/base.bundle.local.js').write_text('/* synthetic runtime fixture */')
    (book / 'content/tailwind_output.css').write_text('')
    (book / 'pg001_sec001.html').write_text('''<!doctype html><html lang="en"><head>
<meta name="title-id" content="pg001_sec001"><meta name="page-section-id" content="1">
<title>Synthetic lesson</title></head><body><main id="content">
<h1 data-id="title">Synthetic lesson</h1><section data-section-type="activity_open_ended_answer">
<label data-id="label" for="answer">Your response</label>
<textarea id="answer" data-aria-id="saved-answer" data-activity-item="item-1"></textarea>
</section></main><script src="assets/base.bundle.local.js"></script></body></html>''', encoding='utf-8')
    embedded = {'./pg001_sec001.html': (book / 'pg001_sec001.html').read_text()}
    (book / 'assets/offline-preloader.js').write_text(
        '// custom loader remains byte-identical outside payload\n(function(){\n  var INLINE = '
        + json.dumps(embedded) + ';\n  var BASE_DIR = "custom";\nwindow.fixture = INLINE;\n})();\n')
    pdf = root / 'source.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    writer.add_blank_page(width=300, height=400)
    writer.write(pdf)
    return book, pdf


class Helpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book, self.pdf = fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def node(self, script, *args):
        return subprocess.run(['node', str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)

    def test_prepare_folder_isolates_inputs_and_preserves_optional_notes(self):
        notes = self.root / 'notes.txt'
        notes.write_text('Resize the map on page 1.')
        before = inventory.snapshot(self.book)
        job = self.root / 'job'
        result = prepare.prepare(self.book, self.pdf, job, [notes], '1')
        self.assertEqual(result['physical_pdf_pages'], [1])
        self.assertEqual(result['languages'], ['sq', 'en'])
        self.assertEqual((job / result['notes'][0]['copy']).read_text(), notes.read_text())
        (job / 'repaired-adt/pg001_sec001.html').write_text('changed')
        self.assertEqual(before, inventory.snapshot(self.book))
        self.assertNotEqual((job / 'baseline/pg001_sec001.html').read_text(), 'changed')

    def test_prepare_nested_zip_and_no_notes(self):
        source = self.root / 'book.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            for file in self.book.rglob('*'):
                if file.is_file():
                    archive.write(file, 'wrapped/' + file.relative_to(self.book).as_posix())
        result = prepare.prepare(source, self.pdf, self.root / 'job')
        self.assertEqual(result['physical_pdf_pages'], [1, 2])
        self.assertEqual(result['notes'], [])
        self.assertIsNotNone(result['input']['adt_zip_sha256'])

    def test_execution_mode_is_explicit_and_independent_of_operation(self):
        result = prepare.prepare(self.book, self.pdf, self.root / 'economy-job',
                                 mode='audit', execution_mode='economy')
        self.assertEqual(result['execution_mode'], 'economy')
        self.assertEqual(result['operation'], 'audit')
        self.assertEqual(result['mode'], 'audit')
        self.assertEqual(prepare.prepare(self.book, self.pdf, self.root / 'legacy-api')['execution_mode'], 'standard')
        for value in ['auto', 'budget', 'audit']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare.prepare(self.book, self.pdf, self.root / 'invalid', execution_mode=value)
        import sys
        command = [sys.executable, str(SCRIPTS / 'prepare_job.py'), '--adt', str(self.book),
                   '--pdf', str(self.pdf), '--out', str(self.root / 'cli-job')]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('--execution-mode', missing.stderr)
        accepted = subprocess.run(command + ['--execution-mode', 'economy'], capture_output=True, text=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)['execution_mode'], 'economy')

    def test_prepare_rejects_overwrite_and_nested_output(self):
        with self.assertRaises(ValueError):
            prepare.prepare(self.book, self.pdf, self.book / 'job')
        job = self.root / 'job'
        job.mkdir()
        (job / 'keep.txt').write_text('keep')
        with self.assertRaises(ValueError):
            prepare.prepare(self.book, self.pdf, job)
        self.assertEqual((job / 'keep.txt').read_text(), 'keep')

    def test_ranges_reject_invalid_physical_pages(self):
        self.assertEqual(prepare.parse_pages('1,2-4,4', 5), [1, 2, 3, 4])
        for value in ['0', '3-2', '6', '-1', '1-2-3']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare.parse_pages(value, 5)

    def test_zip_rejects_traversal_links_and_size_limit(self):
        for name, mode in [('../escape.txt', None), ('absolute\\escape.txt', None), ('link', stat.S_IFLNK | 0o777)]:
            archive = self.root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                info = zipfile.ZipInfo(name)
                if mode:
                    info.external_attr = mode << 16
                z.writestr(info, 'outside')
            with self.subTest(name=name), self.assertRaises(ValueError):
                prepare.extract_zip(archive, self.root / 'unpack', 100)
        archive = self.root / 'size.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('large.txt', 'x' * 101)
        with self.assertRaises(ValueError):
            prepare.extract_zip(archive, self.root / 'unpack', 100)
        self.assertFalse((self.root / 'escape.txt').exists())

    def test_rejects_ambiguous_roots_and_symlinked_book(self):
        other = self.root / 'another-adt'
        shutil.copytree(self.book, other)
        with self.assertRaises(ValueError):
            prepare.find_root(self.root)
        (self.book / 'linked').symlink_to(self.pdf)
        with self.assertRaises(ValueError):
            prepare.reject_symlinks(self.book)

    def test_inventory_detects_saved_response_key_regression(self):
        before = inventory.snapshot(self.book)
        page = self.book / 'pg001_sec001.html'
        page.write_text(page.read_text().replace('saved-answer', 'new-key'))
        comparison = inventory.compare(before, inventory.snapshot(self.book), set())
        self.assertFalse(comparison['passed'])
        self.assertTrue(any('controls' in issue['message'] for issue in comparison['issues']))

    def test_inventory_rejects_spine_escape(self):
        dump(self.book / 'content/pages.json', [{'section_id': 'bad', 'href': '../outside.html'}])
        with self.assertRaises(ValueError):
            inventory.snapshot(self.book)

    def test_cache_refresh_preserves_loader_and_adds_catalogs(self):
        preloader = self.book / 'assets/offline-preloader.js'
        before = preloader.read_text()
        result = self.node('regen-preloader.mjs', self.book)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = preloader.read_text()
        self.assertEqual(before.split('var INLINE = ')[0], after.split('var INLINE = ')[0])
        self.assertEqual(before.split(';\n  var BASE_DIR')[1], after.split(';\n  var BASE_DIR')[1])
        self.assertIn('./content/i18n/en/texts.json', after)
        self.assertIn('saved-answer', after)
        self.assertEqual(self.node('check-bundle.mjs', self.book).returncode, 0)

    def test_cache_rejects_bad_json_without_writing(self):
        preloader = self.book / 'assets/offline-preloader.js'
        before = preloader.read_bytes()
        (self.book / 'content/i18n/en/texts.json').write_text('{bad')
        result = self.node('regen-preloader.mjs', self.book)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, preloader.read_bytes())

    def test_static_checker_finds_stale_cache(self):
        page = self.book / 'pg001_sec001.html'
        page.write_text(page.read_text().replace('Synthetic lesson', 'Updated lesson'))
        result = self.node('check-bundle.mjs', self.book)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('snapshot is stale', result.stdout)

    def test_static_checker_rejects_missing_navigation_manifest(self):
        (self.book / 'content/pages.json').unlink()
        result = self.node('check-bundle.mjs', self.book)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing, invalid or empty navigation spine', result.stdout)

    def test_pdf_includes_findings_notes_and_unperformed_checks(self):
        from pypdf import PdfReader
        job = self.root / 'job'
        prepare.prepare(self.book, self.pdf, job)
        dump(job / 'reports/issues.json', {'issues': [{'id': 'ADT-001', 'summary': 'Map & legend',
             'status': 'open', 'evidence': 'Source page 1', 'action': 'Pending verification'}]})
        dump(job / 'reports/reviewer-notes.json', {'notes': [{'id': 'NOTE-001',
             'comment': 'Resize the map', 'status': 'needs-clarification', 'disposition': 'Confirm scope'}]})
        dump(job / 'reports/validation.json', {'checks': [{'name': 'Screen reader session', 'status': 'not-run',
             'limitations': 'No manual session performed'}]})
        output = report.build(job, self.root / 'report.pdf')
        text = '\n'.join(page.extract_text() for page in PdfReader(output).pages)
        for expected in ['ADT-001', 'NOTE-001', 'needs-clarification', 'not-run', 'Map & legend']:
            self.assertIn(expected, text)

    def test_empty_report_does_not_claim_validation(self):
        from pypdf import PdfReader
        job = self.root / 'job'
        prepare.prepare(self.book, self.pdf, job)
        output = report.build(job, self.root / 'report.pdf')
        text = '\n'.join(page.extract_text() for page in PdfReader(output).pages)
        self.assertIn('Validation is not established', text)

    def test_report_records_model_attempts_and_unknown_usage(self):
        from pypdf import PdfReader
        job = self.root / 'job'
        prepare.prepare(self.book, self.pdf, job, execution_mode='economy')
        dump(job / 'reports/execution.json', {'tasks': {'classify-001': {
            'requested': {'model': 'gpt-6.1-terra'}, 'actual_model': 'gpt-6.1-terra',
            'state': 'finished', 'status': 'passed', 'provider_usage': None,
            'attempts': [{'requested': {'model': 'gpt-6-luna'}, 'actual_model': 'gpt-6-luna',
                          'status': 'needs-escalation', 'provider_usage': None}]}}})
        output = report.build(job, self.root / 'routing-report.pdf')
        text = '\n'.join(page.extract_text() for page in PdfReader(output).pages)
        for expected in ['economy', 'gpt-6-luna', 'gpt-6.1-terra', 'needs-escalation',
                         'Cost is unmeasured', 'unknown, not zero']:
            self.assertIn(expected, text)

    def test_report_does_not_conflate_preview_acceptance_with_roundtrip(self):
        from pypdf import PdfReader
        job = self.root / 'job'
        prepare.prepare(self.book, self.pdf, job)
        dump(job / 'studio-reimport/studio-handoff.json', {
            'stages': {'preflight': 'passed', 'preview': 'passed', 'roundtrip': 'failed', 'tts': 'not-run'},
            'runtime_followups': [{'id': 'MAP-GRADING', 'status': 'open', 'description': 'Wrong answers accepted after export'}],
        })
        output = report.build(job, self.root / 'handoff-report.pdf')
        text = '\n'.join(page.extract_text() for page in PdfReader(output).pages)
        for expected in ['preview: passed', 'roundtrip: failed', 'tts: not-run', 'MAP-GRADING']:
            self.assertIn(expected, text)


if __name__ == '__main__':
    unittest.main()
