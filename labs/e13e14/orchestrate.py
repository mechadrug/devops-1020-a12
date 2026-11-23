"""Run E14's four Compose services on one pinned teaching project."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PORTS = {'buildchecker': 18081, 'echecker': 18082, 'draft': 18083, 'mdfixer': 18084}
ROOT = Path(__file__).resolve().parents[2]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def container_path(path):
    return '/course/' + path.resolve().relative_to(ROOT.resolve()).as_posix()


def host_path(value):
    if not isinstance(value, str) or not value.startswith('/course/'):
        raise ValueError('Expected /course path')
    path = (ROOT / value[len('/course/'):]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('Path escapes repository')
    return path


def command(argv, cwd, log):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode:
        raise ValueError(f'{argv[0]} failed; inspect {log}')
    return p.stdout.strip()


def snapshot(repo, revision, target, logs):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Use a full Git commit SHA')
    head = command(['git', 'rev-parse', '--verify', revision + '^{commit}'], repo,
                   logs / (target.name + '-resolve.log'))
    command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(repo), str(target)], repo,
            logs / (target.name + '-clone.log'))
    command(['git', 'checkout', '--detach', head], target, logs / (target.name + '-checkout.log'))
    if {p.name for p in target.glob('*.c')} != {'main.c', 'helper.c'} or not (target / 'config.h').is_file():
        raise ValueError('Unsupported teaching project profile')
    return head


def call(role, payload, evidence):
    req = urllib.request.Request(f'http://127.0.0.1:{PORTS[role]}/v1/run',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=720) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace')
        save(evidence, {'role': role, 'http': exc.code, 'error': body})
        raise ValueError(f'{role} HTTP {exc.code}: {body}') from exc
    save(evidence, data)
    if data['status'] != 'SUCCEEDED':
        raise ValueError(f'{role} did not succeed')
    return data


def execute(request, out):
    if out.exists():
        raise ValueError('Use a new output directory')
    if not out.resolve().is_relative_to((ROOT / 'work').resolve()):
        raise ValueError('Output must be inside work/')
    repo = host_path(request['repo'])
    candidate = host_path(request['candidate'])
    if not repo.resolve().is_relative_to((ROOT / 'data').resolve()) or not candidate.resolve().is_relative_to((ROOT / 'data').resolve()):
        raise ValueError('Input project and candidate must be in data/')
    out.mkdir(parents=True)
    job = 'job-' + uuid.uuid4().hex
    trace = 'trace-' + uuid.uuid4().hex
    result = {'schema_version': 'e14-compose-1', 'job_id': job, 'trace_id': trace,
              'status': 'RUNNING', 'stages': []}
    save(out / 'request.json', request)

    def payload(project, folder, **extra):
        return {'project': container_path(project), 'out': container_path(folder),
                'job_id': job, 'trace_id': trace, **extra}

    def stage(name, commit, data):
        item = {'name': name, 'commit': commit, 'job_id': job, 'trace_id': trace, 'status': 'SUCCEEDED', 'data': data}
        path = out / (name + '.json')
        save(path, item)
        result['stages'].append({'name': name, 'artifact': {'uri': path.name, 'sha256': digest(path)}})

    try:
        base = out / 'base-project'
        target = out / 'target-project'
        logs = out / 'logs'
        base_sha = snapshot(repo, request['base'], base, logs)
        target_sha = snapshot(repo, request['target'], target, logs)
        result.update(base_commit=base_sha, target_commit=target_sha)

        drafted = call('draft', payload(target, out / 'draft-build',
                                        candidate=container_path(candidate),
                                        expected_output=request.get('expected_output', '1'),
                                        build_timeout=request.get('build_timeout', 600)),
                       out / 'draft-response.json')
        stage('draft', target_sha, drafted)

        base_full = call('buildchecker', payload(base, out / 'baseline-full'), out / 'baseline-response.json')
        target_full = call('buildchecker', payload(target, out / 'target-full'), out / 'target-response.json')
        stage('full-check', base_sha, {'base': base_full, 'target': target_full})

        increment = call('echecker', payload(target, out / 'incremental', base=container_path(base),
                                            baseline_graph=container_path(out / 'baseline-full/actual-graph.json'),
                                            target_findings=container_path(out / 'target-full/findings.json'),
                                            target_commit=target_sha), out / 'incremental-response.json')
        stage('incremental-check', target_sha, increment)

        repair = call('mdfixer', payload(target, out / 'repair-work',
                                        report=increment['report'], report_sha256=increment['sha256'],
                                        target_commit=target_sha), out / 'repair-response.json')
        stage('repair', target_sha, repair)

        final = call('buildchecker', payload(target, out / 'final-full'), out / 'recheck-response.json')
        missing = [x for x in final['result']['findings'] if x['type'] == 'MISSING']
        if missing:
            raise ValueError(f'Recheck has {len(missing)} missing dependencies')
        stage('recheck', target_sha, {'result': final, 'remaining_missing': 0})
        result['status'] = 'SUCCEEDED'
    except Exception as exc:
        result.update(status='FAILED', error=str(exc))
    result['artifacts'] = [{'uri': path.relative_to(out).as_posix(), 'sha256': digest(path),
                            'bytes': path.stat().st_size} for path in sorted(out.rglob('*'))
                           if path.is_file() and '.git' not in path.parts and not path.is_symlink()]
    save(out / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = execute(json.loads(args.request.read_text(encoding='utf-8')), args.out.resolve())
    print(json.dumps({'status': result['status'], 'job_id': result['job_id'],
                      'stages': [x['name'] for x in result['stages']],
                      'error': result.get('error')}, ensure_ascii=False))
    return 0 if result['status'] == 'SUCCEEDED' else 1


if __name__ == '__main__':
    sys.exit(main())
