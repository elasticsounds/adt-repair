"""Regression tests for local routing, dispatch evidence and cache validity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/adt-repair/skills/adt-pdf-restyle/scripts/workflow.py'
spec = importlib.util.spec_from_file_location('workflow', SCRIPT)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=str(Path(tempfile.gettempdir()).resolve()))
        self.root = Path(self.temp.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.pdf = self.root / 'source.pdf'
        self.pdf.write_bytes(b'pdf')
        self.config = {'input': {'pdf': str(self.pdf)}, 'physical_pdf_pages': [1], 'languages': ['en']}
        self.write_config()
        for file in ('input', 'context', 'artifact'):
            (self.job / file).write_text(file)

    def tearDown(self):
        self.temp.cleanup()

    def write_config(self):
        (self.job / 'job.json').write_text(json.dumps(self.config))

    def test_ancestor_alias_is_allowed_but_job_symlink_is_not(self):
        alias = self.root / 'os-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(w.route(alias / 'job', 'triage')['model'], w.MODELS['sol'])
        resolved_job, config, _ = w.job_config(alias / 'job')
        rows = w.evidence(resolved_job, config, [alias / 'job/input'])
        self.assertEqual(rows[0]['path'], 'input')
        (self.root / 'linked-job').symlink_to(self.job, target_is_directory=True)
        with self.assertRaises(ValueError):
            w.route(self.root / 'linked-job', 'triage')

    def test_routing_and_mode_validation(self):
        self.assertEqual(w.route(self.job, 'triage')['model'], w.MODELS['sol'])
        self.config['execution_mode'] = 'economy'; self.write_config()
        for kind, role in w.KINDS.items():
            self.assertEqual(w.route(self.job, kind)['model'], w.MODELS[role])
        self.assertEqual(w.route(self.job, 'notes')['effort'], 'low')
        self.assertEqual(w.route(self.job, 'notes', 'high')['effort'], 'high')
        self.assertEqual(w.route(self.job, 'triage', 'high')['model'], w.MODELS['sol'])
        with self.assertRaises(ValueError): w.route(self.job, 'unknown')
        self.config['execution_mode'] = 'typo'; self.write_config()
        with self.assertRaises(ValueError): w.route(self.job, 'notes')

    def test_dispatch_mismatch_and_unknown_usage(self):
        w.start(self.job, 't', 'repair', inputs=['input'], context=['context'])
        ledger = self.job / 'reports/execution.json'
        before = ledger.read_bytes()
        with self.assertRaises(ValueError): w.finish(self.job, 't', 'unknown', 'passed', 'done')
        self.assertEqual(ledger.read_bytes(), before)

        with self.assertRaises(ValueError): w.finish(self.job, 't', w.MODELS['sol'], 'passed', 'claim only')
        self.assertEqual(ledger.read_bytes(), before)
        result = w.finish(self.job, 't', w.MODELS['terra'], 'passed', 'done', ['artifact'])
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(result['model_mismatch'])
        self.assertIsNone(result['provider_usage'])
        self.assertEqual(result['outputs'][0]['path'], 'artifact')
        before = ledger.read_bytes()
        with self.assertRaises(ValueError): w.start(self.job, 't', 'repair')
        with self.assertRaises(ValueError): w.finish(self.job, 't', w.MODELS['sol'], 'passed', 'done')
        self.assertEqual(ledger.read_bytes(), before)

    def test_unavailable_worker_can_be_blocked_without_fabricated_model(self):
        w.start(self.job, 'unavailable', 'triage', inputs=['input'])
        result = w.block(self.job, 'unavailable', 'Requested model unavailable; no worker ran.')
        self.assertEqual(result['status'], 'blocked')
        self.assertIsNone(result['actual_model'])
        self.assertIsNone(result['provider_usage'])
        with self.assertRaises(ValueError):
            w.block(self.job, 'unavailable', 'again')

    def test_bounded_escalation_retains_attempts(self):
        self.config['execution_mode'] = 'economy'; self.write_config()
        first = w.start(self.job, 't', 'triage', inputs=['input'], context=['context'])
        old_hash = first['inputs'][0]['sha256']
        (self.job / 'input').write_text('updated')
        for model in ('luna', 'terra'):
            w.finish(self.job, 't', w.MODELS[model], 'needs-escalation', 'needs review')
            result = w.escalate(self.job, 't', 'complex')
        self.assertEqual(result['requested']['model'], w.MODELS['sol'])
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual(result['attempts'][0]['inputs'][0]['sha256'], old_hash)
        self.assertNotEqual(result['inputs'][0]['sha256'], old_hash)
        w.finish(self.job, 't', w.MODELS['sol'], 'needs-escalation', 'still unresolved')
        with self.assertRaises(ValueError): w.escalate(self.job, 't', 'again')

    def test_cache_invalidation(self):
        args = (self.job, 'key', ['input'], ['artifact'], ['context'], '1')
        w.cache_put(*args, 'passed')
        self.assertTrue(w.cache_check(*args)['reusable'])
        for filename in ('input', 'context', 'artifact'):
            path = self.job / filename
            original = path.read_text(); path.write_text('changed')
            self.assertFalse(w.cache_check(*args)['reusable'])
            path.write_text(original)
        self.assertFalse(w.cache_check(*args[:-1], '2')['reusable'])
        for field, value in [('physical_pdf_pages', [2]), ('languages', ['fr']),
                             ('execution_mode', 'economy'), ('operation', 'audit')]:
            previous = self.config.get(field); self.config[field] = value; self.write_config()
            self.assertFalse(w.cache_check(*args)['reusable'])
            if previous is None: del self.config[field]
            else: self.config[field] = previous
            self.write_config()
        self.pdf.write_bytes(b'new pdf')
        self.assertFalse(w.cache_check(*args)['reusable'])
        (self.job / 'artifact').unlink()
        self.assertFalse(w.cache_check(*args)['reusable'])

    def test_escalation_missing_input_is_atomic(self):
        self.config['execution_mode'] = 'economy'; self.write_config()
        w.start(self.job, 't', 'triage', inputs=['input'])
        w.finish(self.job, 't', w.MODELS['luna'], 'needs-escalation', 'review')
        ledger = self.job / 'reports/execution.json'; before = ledger.read_bytes()
        (self.job / 'input').unlink()
        with self.assertRaises(ValueError): w.escalate(self.job, 't', 'review')
        self.assertEqual(ledger.read_bytes(), before)

    def test_reports_symlink_is_rejected(self):
        (self.job / 'reports').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): w.start(self.job, 't', 'notes')
        self.assertFalse((self.root / 'execution.json').exists())

    def test_unsafe_paths_and_atomic_failures(self):
        (self.job / 'link').symlink_to(self.root, target_is_directory=True)
        for bad in ('../source.pdf', 'link/source.pdf'):
            if bad.startswith('..'): # exact source PDF is allowed as input
                self.assertEqual(w.evidence(self.job, self.config, [bad])[0]['path'], 'source-pdf')
            else:
                with self.assertRaises(ValueError): w.start(self.job, 'bad', 'notes', inputs=[bad])
        outside = self.root / 'other'; outside.write_text('other')
        with self.assertRaises(ValueError): w.start(self.job, 'bad', 'notes', inputs=[outside])
        with self.assertRaises(ValueError): w.cache_put(self.job, 'k', ['input'], [self.pdf], [], '1', 'passed')
        with self.assertRaises(ValueError): w.cache_put(self.job, 'k', ['input'], ['artifact'], [], '1', 'blocked')
        self.assertFalse((self.job / 'reports/workflow-cache.json').exists())
        w.cache_put(self.job, 'k', ['input'], ['artifact'], [], '1', 'passed')
        store = self.job / 'reports/workflow-cache.json'; before = store.read_bytes()
        with self.assertRaises(ValueError): w.cache_put(self.job, 'k', ['input'], ['artifact'], [], '1', 'passed')
        self.assertEqual(store.read_bytes(), before)
        cli = subprocess.run([sys.executable, str(SCRIPT), 'route', '--job', str(self.job), '--kind', 'unknown'], capture_output=True)
        self.assertNotEqual(cli.returncode, 0)


if __name__ == '__main__': unittest.main()
