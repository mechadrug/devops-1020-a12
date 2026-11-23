"""One HTTP boundary per E14 teaching capability, using the existing implementations."""
import hashlib
import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path[:0] = ['/course/labs/e8e10', '/course/labs/e11e12/vendor', '/app']
from lab import scan, patch, validate
from draft.autobuild import auto_build
from buildchecker.fullcheck import full_check

ROOT = Path('/course').resolve()
ROLE = os.environ['E14_ROLE']


def local(value, area='work'):
    path = Path(value).resolve()
    allowed = ROOT / area
    if not path.is_relative_to(allowed):
        raise ValueError(f'Path must be inside {allowed}')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(data):
    project = local(data['project'])
    out = local(data['out'])
    if out.exists():
        raise ValueError('Output already exists')
    if ROLE == 'draft':
        candidate = local(data['candidate'], 'data')
        result = auto_build(project, candidate, out, data.get('expected_output', '1'),
                            timeout=float(data.get('build_timeout', 600)))
        if result['status'] != 'SUCCEEDED':
            raise ValueError('DRAFT_' + result['status'] + ': ' + str(result.get('error')))
        return {'status': 'SUCCEEDED', 'result': result, 'artifact': str(out / 'result.json')}
    if ROLE == 'buildchecker':
        result = full_check(project, out)
        if result['status'] != 'SUCCEEDED':
            raise ValueError('BUILDCHECKER_' + result['status'] + ': ' + str(result.get('error')))
        return {'status': 'SUCCEEDED', 'result': result, 'artifact': str(out / 'findings.json')}
    if ROLE == 'echecker':
        base = local(data['base'])
        baseline_graph = local(data['baseline_graph'])
        target_findings = local(data['target_findings'])
        old = scan(base)
        graph = json.loads(baseline_graph.read_text())
        projected = {t: sorted({e['dependency'] for e in graph if e['target'] == t})
                     for t in ('main.o', 'helper.o')}
        if old['actual'] != projected:
            raise ValueError('Baseline BuildChecker/GCC graph mismatch')
        old['actual'] = projected
        current = scan(project, old)
        reference = json.loads(target_findings.read_text())
        normalize = lambda fs: sorted((x['type'], x['target'], x['dependency']) for x in fs
                                      if x['target'] in ('main.o', 'helper.o'))
        if reference['status'] != 'SUCCEEDED' or normalize(current['findings']) != normalize(reference['findings']):
            raise ValueError('Incremental/full findings mismatch')
        out.mkdir(parents=True)
        save(out / 'baseline-cache.json', old)
        envelope = {'schema_version': 'e11e12-1', 'kind': 'incremental-check',
                    'status': 'SUCCEEDED', 'commit': data['target_commit'],
                    'job_id': data['job_id'], 'trace_id': data['trace_id'], 'data': current}
        if current['commit'] != data['target_commit']:
            raise ValueError('Target commit mismatch')
        save(out / 'incremental-check.json', envelope)
        return {'status': 'SUCCEEDED', 'report': str(out / 'incremental-check.json'),
                'sha256': sha(out / 'incremental-check.json'), 'findings': current['findings']}
    if ROLE == 'mdfixer':
        report = local(data['report'])
        if sha(report) != data['report_sha256']:
            raise ValueError('Report transfer hash mismatch')
        envelope = json.loads(report.read_text())
        if (envelope['schema_version'], envelope['kind'], envelope['status'],
            envelope['commit'], envelope['job_id'], envelope['trace_id']) != (
                'e11e12-1', 'incremental-check', 'SUCCEEDED', data['target_commit'],
                data['job_id'], data['trace_id']):
            raise ValueError('Report identity mismatch')
        out.mkdir(parents=True)
        diff, edits = patch(project, envelope['data'])
        if not diff:
            raise ValueError('No missing dependency to repair')
        candidate = out / 'candidate.patch'
        candidate.write_text(diff, encoding='utf-8')
        save(out / 'repair-plan.json', edits)
        verdict = validate(project, candidate, out / 'validation')
        if not verdict['accepted']:
            raise ValueError('Patch rejected: ' + str(verdict))
        return {'status': 'SUCCEEDED', 'patch': str(candidate),
                'sha256': sha(candidate), 'validation': verdict}
    raise ValueError('Unknown role')


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body = (json.dumps(data, ensure_ascii=False) + '\n').encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'status': 'ok', 'role': ROLE})
        else:
            self.reply(404, {'error': 'NOT_FOUND'})

    def do_POST(self):
        if self.path != '/v1/run':
            self.reply(404, {'error': 'NOT_FOUND'})
            return
        start = time.monotonic()
        data = {}
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 100000:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(length))
            result = run(data)
            print(json.dumps({'role': ROLE, 'job_id': data.get('job_id'),
                              'trace_id': data.get('trace_id'), 'status': 'SUCCEEDED',
                              'elapsed_ms': round((time.monotonic()-start)*1000)}), flush=True)
            self.reply(200, result)
        except Exception as exc:
            traceback.print_exc()
            code = 'TIMEOUT' if 'TIMED_OUT' in str(exc) else type(exc).__name__.upper()
            print(json.dumps({'role': ROLE, 'job_id': data.get('job_id'),
                              'trace_id': data.get('trace_id'), 'status': 'FAILED',
                              'error_code': code, 'elapsed_ms': round((time.monotonic()-start)*1000)}), flush=True)
            self.reply(422, {'status': 'FAILED', 'role': ROLE, 'error_code': code, 'error': str(exc)})


if __name__ == '__main__':
    if ROLE not in {'draft', 'buildchecker', 'echecker', 'mdfixer'}:
        raise SystemExit('Invalid E14_ROLE')
    HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
