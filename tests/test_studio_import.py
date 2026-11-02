"""Import handoff invariants on synthetic bundles, without a live Studio or paid API."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/adt-repair/skills/adt-pdf-restyle/scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


check = module('check_studio_import')
stage = module('studio_import')


class StudioImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.book = self.root / 'accepted'
        (self.book / 'content/i18n/en').mkdir(parents=True)
        (self.book / 'assets').mkdir()
        (self.book / 'images').mkdir()
        stage.write(self.book / 'content/pages.json', [{'href': 'pg001_sec001.html', 'section_id': 'pg001_sec001'}])
        stage.write(self.book / 'content/i18n/en/texts.json', {'pg001_n001': 'Keep this wording'})
        (self.book / 'index.html').write_text('<!doctype html><a href="pg001_sec001.html">Open</a>')
        (self.book / 'pg001_sec001.html').write_text('''<!doctype html><div id="content">
<section data-section-id="pg001_sec001" data-section-type="content">
<p data-id="pg001_n001">Keep this wording</p></section></div>''')

    def tearDown(self):
        self.temp.cleanup()

    def test_prepare_keeps_accepted_book_and_audit_status_honest(self):
        before = stage.tree(self.book)
        job = self.root / 'handoff'
        data = stage.prepare(self.book, job)
        self.assertTrue(all(s == 'not-run' for s in data['stages'].values()))
        (job / 'studio-import-adt/pg001_sec001.html').write_text('changed only in copy')
        self.assertEqual(stage.tree(self.book), before)
        with self.assertRaises(ValueError):
            stage.prepare(self.book, job)
        with self.assertRaises(ValueError):
            stage.prepare(self.book, self.book / 'nested')

    def test_preflight_detects_discarded_content_and_duplicate_global_ids(self):
        pages = json.loads((self.book / 'content/pages.json').read_text())
        pages.append({'href': 'pg002_sec001.html', 'section_id': 'pg002_sec001'})
        stage.write(self.book / 'content/pages.json', pages)
        original = (self.book / 'pg001_sec001.html').read_text()
        (self.book / 'pg002_sec001.html').write_text(original.replace('pg001_sec001', 'pg002_sec001'))
        (self.book / 'pg001_sec001.html').write_text(original.replace('<section ', '<nav data-id="crumb">Context</nav><section '))
        result = check.inspect(self.book)
        self.assertTrue(any('outside the canonical' in e for e in result['errors']))
        self.assertTrue(any('used on 2 pages' in e for e in result['errors']))

    def test_preflight_catches_index_dependencies_and_inline_stylesheets(self):
        (self.book / 'assets/custom.js').write_text('/* not importable */')
        (self.book / 'index.html').write_text('<script src="assets/custom.js"></script>')
        page = self.book / 'pg001_sec001.html'
        page.write_text('<style>p{color:red}</style>' + page.read_text())
        errors = check.inspect(self.book)['errors']
        self.assertTrue(any('index.html' in e and 'custom script' in e for e in errors))
        self.assertTrue(any('<style>' in e for e in errors))

    def test_spine_escape_is_not_read(self):
        stage.write(self.book / 'content/pages.json', [{'href': '../outside.html', 'section_id': 'pg001_sec001'}])
        errors = check.inspect(self.book)['errors']
        self.assertTrue(any('unsafe or nested' in e for e in errors))

    def test_package_is_hash_bound_and_never_certifies_roundtrip_or_tts(self):
        job = self.root / 'handoff'
        stage.prepare(self.book, job)
        receipt = stage.package(job)
        archive, _ = stage.verify_package(job)
        with zipfile.ZipFile(archive) as zipped:
            self.assertIn('index.html', zipped.namelist())
            self.assertFalse(any('reports/' in name or name.endswith('.zip') for name in zipped.namelist()))
        data = stage.state(job)
        self.assertEqual(data['stages']['preflight'], 'passed')
        self.assertEqual(data['stages']['preview'], 'not-run')
        self.assertEqual(data['stages']['roundtrip'], 'not-run')
        self.assertEqual(data['stages']['tts'], 'not-run')
        self.assertEqual(stage.sha(archive), receipt['sha256'])
        data['stages']['preview'] = 'passed'
        stage.save(job, data)
        page = job / 'studio-import-adt/pg001_sec001.html'
        page.write_text(page.read_text().replace('Keep this wording', 'Changed'))
        with self.assertRaises(ValueError):
            stage.verify_package(job)
        stage.check(job)
        self.assertEqual(stage.state(job)['stages']['preview'], 'stale')

    def test_packaging_rejects_nested_archive_and_unexplained_warning(self):
        job = self.root / 'handoff'
        stage.prepare(self.book, job)
        nested = job / 'studio-import-adt/assets/leftover.zip'
        nested.write_bytes(b'archive')
        with self.assertRaises(ValueError):
            stage.package(job)
        nested.unlink()
        text = job / 'studio-import-adt/content/i18n/en/texts.json'
        stage.write(text, {})
        with self.assertRaises(ValueError):
            stage.package(job)
        warning = stage.check(job)['warnings'][0]
        data = stage.state(job)
        data['warning_dispositions'] = [{'warning': warning, 'explanation': 'Synthetic fixture; not a narrated production book.'}]
        stage.save(job, data)
        self.assertIsNotNone(stage.package(job))

    def test_preview_requires_exact_studio_adt_acceptance(self):
        accepted = {'isAdtBundle': True, 'compatibility': {'supported': True, 'issues': []},
                    'activityReview': {'needsReviewCount': 0}}
        self.assertTrue(stage.preview_result(200, accepted))
        for response in [{}, {'isAdtBundle': True},
                         {**accepted, 'activityReview': {'needsReviewCount': 1}},
                         {**accepted, 'activityReview': {'needsReviewCount': False}},
                         {**accepted, 'compatibility': {'supported': True, 'issues': ['unsupported-script']}}]:
            self.assertFalse(stage.preview_result(200, response))
        self.assertFalse(stage.preview_result(201, accepted))

    def test_narration_exposes_stale_provider_text_without_generating_audio(self):
        stage.write(self.book / 'content/i18n/en/speech_texts.json', {'pg001_n001': 'Keep this wording'})
        stage.write(self.book / 'content/i18n/en/audios.json', {'pg001_n001': 'old.mp3'})
        job = self.root / 'handoff'
        stage.prepare(self.book, job)
        new = job / 'studio-import-adt/content/i18n/en'
        stage.write(new / 'texts.json', {'pg001_n001': 'Corrected wording', 'new_context': 'Lesson context'})
        stage.write(new / 'audios.json', {})
        before = stage.tree(job / 'studio-import-adt')
        plan = stage.narration(job, self.book)
        self.assertEqual(plan['required_regeneration_count'], 1)
        corrected = next(e for e in plan['entries'] if e['id'] == 'pg001_n001')
        self.assertTrue(corrected['provider_input_needs_review'])
        self.assertEqual(plan['tts'], 'not-run')
        self.assertEqual(stage.tree(job / 'studio-import-adt'), before)

    def test_preflight_flags_answer_globals_that_preview_can_miss(self):
        page = self.book / 'pg001_sec001.html'
        page.write_text(page.read_text().replace('data-section-type="content"', 'data-section-type="activity_fill_in_the_blank"') +
                        '<script>window.correctAnswers={"item-1":"Right"}</script>')
        result = check.inspect(self.book)
        self.assertTrue(any('answer-key recovery' in warning for warning in result['warnings']))


if __name__ == '__main__':
    unittest.main()
