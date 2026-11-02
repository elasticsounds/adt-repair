#!/usr/bin/env python3
"""Plan model routing and record dispatch evidence and local artifact reuse."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

MODELS = {'sol': 'gpt-6.1-sol', 'terra': 'gpt-6.1-terra', 'luna': 'gpt-6-luna'}
KINDS = {
    **dict.fromkeys(('triage', 'classify', 'notes', 'report-draft'), 'luna'),
    **dict.fromkeys(('repair', 'asset-repair', 'component-implementation', 'behavior-diagnosis'), 'terra'),
    **dict.fromkeys(('design-contract', 'outline', 'answer-key', 'final-review'), 'sol'),
}


def read_json(path):
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def job_config(job):
    job = Path(job).absolute()
    if job.is_symlink():
        raise ValueError('The job root must not be a symlink')
    job = job.resolve(strict=True)
    safe_file(job / 'job.json', job, None)
    config = read_json(job / 'job.json')
    mode = config.get('execution_mode', 'standard')
    if mode not in ('standard', 'economy'):
        raise ValueError('Unknown execution mode: ' + str(mode))
    return job, config, mode


def route(job, kind, risk=None):
    _, _, mode = job_config(job)
    if kind not in KINDS:
        raise ValueError('Unknown task kind: ' + str(kind))
    if risk not in (None, 'high'):
        raise ValueError('Unknown risk: ' + str(risk))
    role = 'sol' if mode == 'standard' or risk == 'high' else KINDS[kind]
    return {'model': MODELS[role], 'effort': 'high' if risk == 'high' else ('low' if role == 'luna' else 'medium'),
            'mode': mode, 'why': f'{mode} routing for {kind}' + ('; high risk' if risk else '')}


def safe_file(path, job, pdf, artifact=False):
    path = Path(path)
    if not path.is_absolute():
        path = job / path
    # Reject links within the job, while allowing OS aliases above its root
    # (for example /var -> /private/var on macOS).
    path = Path(os.path.abspath(path))
    resolved = path.resolve()
    inside = resolved.is_relative_to(job)
    chain = []
    reached_job = False
    for part in (path, *path.parents):
        chain.append(part)
        if part.resolve() == job:
            reached_job = True
            break
    if inside or reached_job:
        for part in chain:
            if part.is_symlink():
                raise ValueError('Symlinks are not allowed: ' + str(path))
    elif path.is_symlink():
        raise ValueError('Symlinks are not allowed: ' + str(path))
    path = resolved
    if not path.is_file():
        raise ValueError('Expected a regular file: ' + str(path))
    if not inside and (artifact or pdf is None or path != pdf.resolve()):
        raise ValueError('File is outside the job: ' + str(path))
    return path


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def evidence(job, config, paths, artifact=False):
    pdf_value = config.get('input', {}).get('pdf')
    pdf = Path(os.path.abspath(pdf_value)) if pdf_value else None
    result = []
    for item in paths or []:
        path = safe_file(item, job, pdf, artifact)
        name = path.relative_to(job).as_posix() if path.is_relative_to(job) else 'source-pdf'
        result.append({'path': name, 'sha256': digest(path)})
    return sorted(result, key=lambda x: x['path'])


def scope(job, config, mode):
    pdf_value = config.get('input', {}).get('pdf')
    if not pdf_value:
        raise ValueError('Job must declare input.pdf')
    pdf = evidence(job, config, [pdf_value])[0]
    return {'physical_pdf_pages': config.get('physical_pdf_pages'), 'languages': config.get('languages'),
            'pdf_sha256': pdf['sha256'], 'mode': mode,
            'operation': config.get('operation', config.get('mode', 'repair'))}


def load_store(job, filename, field):
    path = job / 'reports' / filename
    # Refuse symlinks for store and its ancestors, even when the file does not yet exist.
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError('Symlinks are not allowed: ' + str(path))
    if path.exists():
        if not path.is_file():
            raise ValueError('Store is not a regular file')
        data = read_json(path)
        if not isinstance(data.get(field), dict):
            raise ValueError('Invalid workflow store')
        return path, data
    return path, {'schema_version': 1, field: {}}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = f.name
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def require_id(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('An ID or key is required')


def start(job, task_id, kind, risk=None, inputs=None, context=None):
    job, config, _ = job_config(job)
    require_id(task_id)
    planned = route(job, kind, risk)
    record = {'task_id': task_id, 'kind': kind, 'risk': risk, 'requested': planned,
              'inputs': evidence(job, config, inputs), 'context': evidence(job, config, context),
              'state': 'started', 'attempts': []}
    path, data = load_store(job, 'execution.json', 'tasks')
    if task_id in data['tasks']:
        raise ValueError('Task ID already exists')
    data['tasks'][task_id] = record
    save(path, data)
    return record


def finish(job, task_id, actual_model, status, summary, outputs=None, usage_json=None):
    job, config, _ = job_config(job)
    require_id(task_id)
    if actual_model not in MODELS.values():
        raise ValueError('Unsupported actual model')
    if status not in ('passed', 'needs-escalation', 'blocked') or not isinstance(summary, str) or not summary.strip():
        raise ValueError('A valid status and summary are required')
    if status == 'passed' and not outputs:
        raise ValueError('Passed tasks require output evidence')
    output = evidence(job, config, outputs)
    usage = None
    if usage_json is not None:
        usage_path = safe_file(usage_json, job, Path(os.path.abspath(config['input']['pdf'])) if config.get('input', {}).get('pdf') else None)
        usage = read_json(usage_path)
        if not isinstance(usage, dict):
            raise ValueError('Provider usage must be a JSON object')
    path, data = load_store(job, 'execution.json', 'tasks')
    record = data['tasks'].get(task_id)
    if not record or record.get('state') != 'started':
        raise ValueError('Task does not exist or is already finished')
    mismatch = actual_model != record['requested']['model']
    record.update({'state': 'finished', 'actual_model': actual_model,
                   'status': 'blocked' if mismatch else status, 'reported_status': status,
                   'model_mismatch': mismatch, 'summary': summary, 'outputs': output,
                   'provider_usage': usage})
    save(path, data)
    return record


def block(job, task_id, reason):
    job, _, _ = job_config(job)
    require_id(task_id)
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('A blocking reason is required')
    path, data = load_store(job, 'execution.json', 'tasks')
    record = data['tasks'].get(task_id)
    if not record or record.get('state') != 'started':
        raise ValueError('An unfinished task is required')
    record.update(state='finished', status='blocked', actual_model=None,
                  summary=reason, outputs=[], provider_usage=None)
    save(path, data)
    return record


def escalate(job, task_id, reason):
    job, config, mode = job_config(job)
    require_id(task_id)
    if mode != 'economy' or not isinstance(reason, str) or not reason.strip():
        raise ValueError('Escalation requires economy mode and a reason')
    path, data = load_store(job, 'execution.json', 'tasks')
    record = data['tasks'].get(task_id)
    if not record or record.get('state') != 'finished' or record.get('status') != 'needs-escalation':
        raise ValueError('A finished attempt needing escalation is required')
    order = [MODELS['luna'], MODELS['terra'], MODELS['sol']]
    current = record['actual_model']
    if current not in order or current == order[-1]:
        raise ValueError('No higher model is available')
    next_model = order[order.index(current) + 1]
    def refresh(items):
        paths = [config['input']['pdf'] if item['path'] == 'source-pdf' else item['path'] for item in items]
        return evidence(job, config, paths)
    new_inputs = refresh(record['inputs'])
    new_context = refresh(record['context'])
    attempt = {k: record[k] for k in ('requested', 'actual_model', 'status', 'reported_status',
                                      'model_mismatch', 'summary', 'outputs', 'provider_usage', 'inputs', 'context')}
    record['attempts'].append(attempt)
    record['inputs'], record['context'] = new_inputs, new_context
    for k in ('actual_model', 'status', 'reported_status', 'model_mismatch', 'summary', 'outputs', 'provider_usage'):
        del record[k]
    record['requested'] = {'model': next_model, 'effort': 'high' if record['risk'] == 'high' else 'medium',
                           'mode': mode, 'why': 'Escalation: ' + reason}
    record['state'] = 'started'
    save(path, data)
    return record


def cache_fingerprint(job, config, mode, inputs, context, tool_version):
    if not isinstance(tool_version, str) or not tool_version.strip():
        raise ValueError('Tool version is required')
    return {'scope': scope(job, config, mode), 'tool_version': tool_version,
            'inputs': evidence(job, config, inputs), 'context': evidence(job, config, context)}


def cache_put(job, key, inputs, artifacts, context, tool_version, status):
    job, config, mode = job_config(job)
    require_id(key)
    if status != 'passed' or not inputs or not artifacts:
        raise ValueError('Only passed results with inputs and artifacts are cacheable')
    fingerprint = cache_fingerprint(job, config, mode, inputs, context, tool_version)
    output = evidence(job, config, artifacts, artifact=True)
    path, data = load_store(job, 'workflow-cache.json', 'entries')
    if key in data['entries']:
        raise ValueError('Cache key already exists')
    data['entries'][key] = {'fingerprint': fingerprint, 'artifacts': output, 'status': status}
    save(path, data)
    return data['entries'][key]


def cache_check(job, key, inputs, artifacts, context, tool_version):
    job, config, mode = job_config(job)
    require_id(key)
    if not inputs or not artifacts:
        raise ValueError('Inputs and artifacts are required')
    path, data = load_store(job, 'workflow-cache.json', 'entries')
    entry = data['entries'].get(key)
    try:
        fingerprint = cache_fingerprint(job, config, mode, inputs, context, tool_version)
        output = evidence(job, config, artifacts, artifact=True)
    except FileNotFoundError:
        return {'reusable': False}
    except ValueError as exc:
        if str(exc).startswith('Expected a regular file:'):
            return {'reusable': False}
        raise
    return {'reusable': bool(entry and entry.get('status') == 'passed' and
                             entry.get('fingerprint') == fingerprint and entry.get('artifacts') == output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('route', 'start', 'finish', 'block', 'escalate', 'cache-put', 'cache-check'):
        p = sub.add_parser(command)
        p.add_argument('--job', required=True)
        if command in ('route', 'start'):
            p.add_argument('--kind', required=True)
            p.add_argument('--risk', choices=['high'])
        if command in ('start', 'finish', 'block', 'escalate'):
            p.add_argument('--task-id', required=True)
        if command in ('start', 'cache-put', 'cache-check'):
            p.add_argument('--input', action='append', default=[])
            p.add_argument('--context', action='append', default=[])
        if command in ('cache-put', 'cache-check'):
            p.add_argument('--key', required=True)
            p.add_argument('--artifact', action='append', default=[])
            p.add_argument('--tool-version', required=True)
        if command == 'cache-put':
            p.add_argument('--status', required=True, choices=['passed'])
        if command in ('escalate', 'block'):
            p.add_argument('--reason', required=True)
        if command == 'finish':
            p.add_argument('--actual-model', required=True)
            p.add_argument('--status', required=True, choices=['passed', 'needs-escalation', 'blocked'])
            p.add_argument('--summary', required=True)
            p.add_argument('--output', action='append', default=[])
            p.add_argument('--usage-json')
    a = parser.parse_args(argv)
    try:
        if a.command == 'route': result = route(a.job, a.kind, a.risk)
        elif a.command == 'start': result = start(a.job, a.task_id, a.kind, a.risk, a.input, a.context)
        elif a.command == 'finish': result = finish(a.job, a.task_id, a.actual_model, a.status, a.summary, a.output, a.usage_json)
        elif a.command == 'block': result = block(a.job, a.task_id, a.reason)
        elif a.command == 'escalate': result = escalate(a.job, a.task_id, a.reason)
        elif a.command == 'cache-put': result = cache_put(a.job, a.key, a.input, a.artifact, a.context, a.tool_version, a.status)
        else: result = cache_check(a.job, a.key, a.input, a.artifact, a.context, a.tool_version)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
