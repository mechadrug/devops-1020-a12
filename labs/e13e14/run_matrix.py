"""Run C1-C8 on an exchanged project inside the existing Linux course image.

This records the local executor. It cannot sign for a remote B12 participant.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'labs/e11e12'), str(ROOT/'labs/e8e10')]
from pipeline import execute, save
from lab import scan, patch, validate
from handoff_a_to_b import make_handoff


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(folder):
    r = json.loads((folder/'result.json').read_text())
    prefix = 'artifact://'+r['job_id']+'/'
    for item in r['artifacts']:
        assert item['uri'].startswith(prefix), item
        p = (folder/item['uri'][len(prefix):]).resolve()
        assert p.is_relative_to(folder.resolve())
        assert p.stat().st_size == item['bytes'] and digest(p) == item['sha256'], p
    return r


def run(request, out):
    r = execute(request, out)
    assert audit(out) == r
    return r


def main(request_path, out):
    if out.exists():
        raise ValueError('Use a new work directory')
    out.mkdir(parents=True)
    req = json.loads(request_path.read_text())
    a_req = dict(req, mode='e11-a')
    save(out/'input.json', req)
    rows = []
    def row(case, evidence, **details):
        item = {'case': case, 'status': 'PASS', 'executor': '231880138',
                'evidence': evidence, **details}
        rows.append(item)
        save(out/'local-results.json', {'scope': 'A12 execution of exchanged project; B12 execution/signoff separate',
                                      'rows': rows, 'all_local_passed': len(rows)==8})
        print(case, 'PASS', flush=True)

    current = run(a_req, out/'C1-A')
    assert current['status'] == 'SUCCEEDED', current
    handoff = make_handoff(out/'C1-A/result.json', req['target'])
    # External inputs must be under /course/data to be usable by the real API.
    transfer = ROOT/'data'/(out.name+'-transfer')
    transfer.mkdir()
    report = transfer/'fixed-md.json'
    save(report, handoff)
    b_req = dict(req, mode='e11-b', fixed_report=str(report), fixed_report_sha256=digest(report))
    save(out/'handoff.json', handoff)
    # Local component consumption is useful evidence; it is not B12's signature.
    consumed = run(b_req, out/'C1-local-consumer')
    assert consumed['status'] == 'SUCCEEDED', consumed
    assert json.loads((out/'C1-local-consumer/fixed-md-input.json').read_text())['source_report'] == handoff['source_report']
    for label in ['base-project', 'target-project']:
        directory = out/'C1-local-consumer'/label
        if '\ntest:' in '\n'+(directory/'Makefile').read_text():
            checks = subprocess.run(['make','test'],cwd=directory,capture_output=True,text=True,timeout=60)
            (out/('C1-'+label+'-behavior.log')).write_text(checks.stdout+checks.stderr)
            assert checks.returncode == 0, checks
    row('C1', ['C1-A', 'C1-local-consumer'], a_job=current['job_id'],
        consumer_job=consumed['job_id'], remote_B12_signoff='PENDING', report_sha256=digest(report))

    old_req = dict(a_req, target=req['base'])
    old = run(old_req, out/'C2-baseline-report')
    assert old['status'] == 'SUCCEEDED'
    old_file = transfer/'old-md.json'
    save(old_file, make_handoff(out/'C2-baseline-report/result.json', req['base']))
    rejected = run(dict(b_req, fixed_report=str(old_file), fixed_report_sha256=digest(old_file)), out/'C2-rejected')
    assert rejected['status'] == 'FAILED' and rejected['error']['code'] == 'STALE_REPORT', rejected
    assert rejected['stages'] == [], 'A stale report must not start DRAFT'
    row('C2', ['C2-baseline-report', 'C2-rejected'], code=rejected['error']['code'])

    damaged = transfer/'damaged-md.json'
    damaged.write_bytes(report.read_bytes()+b'\n')
    rejected = run(dict(b_req, fixed_report=str(damaged)), out/'C3-rejected')
    assert rejected['status'] == 'FAILED' and rejected['error']['code'] == 'ARTIFACT_HASH_MISMATCH', rejected
    assert rejected['stages'] == []
    save(out/'C3-hashes.json', {'original': digest(report), 'damaged': digest(damaged)})
    row('C3', ['C3-rejected', 'C3-hashes.json'], code=rejected['error']['code'])

    timed = run(dict(b_req, build_timeout=0.01), out/'C4-timeout')
    inner = json.loads((out/'C4-timeout/draft-build/result.json').read_text())
    assert timed['status'] != 'SUCCEEDED' and inner['status'] == 'TIMED_OUT', (timed, inner)
    # The pinned slim image has /proc but deliberately does not install procps.
    process_lines = []
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                argv=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                process_lines.append(entry.name+' '+argv)
            except (FileNotFoundError, ProcessLookupError):
                pass  # A process may exit between directory listing and read.
    processes='\n'.join(process_lines)+'\n'
    (out/'C4-processes.txt').write_text('Scope: caller container PID namespace\n'+processes)
    matches = [line for line in processes.splitlines() if 'docker build' in line and str(out/'C4-timeout') in line]
    assert not matches, matches
    containers = subprocess.run(['docker','ps','--no-trunc','--format','{{.ID}} {{.Image}} {{.Names}}'],capture_output=True,text=True,check=True).stdout
    (out/'C4-containers.txt').write_text(containers)
    tags = [a['tag'] for a in inner['attempts']]
    assert not any(tag in containers for tag in tags)
    cid = out/'C4-timeout/draft-build/verify-container-id.txt'
    if cid.exists():
        assert cid.read_text().strip() not in containers
    row('C4', ['C4-timeout','C4-processes.txt','C4-containers.txt'], outer=timed['status'], inner=inner['status'])

    project = Path(req['repo'])
    def state():
        head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=project,text=True).strip()
        status = subprocess.check_output(['git','status','--porcelain'],cwd=project,text=True)
        files = subprocess.check_output(['git','ls-files','-z'],cwd=project).decode().split('\0')
        return {'head':head, 'status':status, 'tracked_hashes':{f:digest(project/f) for f in files if f}}
    before = state()
    candidate = out/'C5-valid.patch'
    candidate.write_text(patch(project, scan(project))[0])
    verdict = validate(project, candidate, out/'C5-test-rejected', fail_test=True)
    invalid = out/'C5-invalid.patch'
    invalid.write_text('not a valid patch\n')
    invalid_verdict = validate(project, invalid, out/'C5-invalid-rejected')
    after = state()
    assert before == after and before['status'] == ''
    assert all(v['accepted'] is False and v['rollback'] and v['source_unchanged'] for v in [verdict,invalid_verdict])
    save(out/'C5-source-state.json', {'before':before,'after':after})
    row('C5', ['C5-test-rejected','C5-invalid-rejected','C5-source-state.json'], source_unchanged=True)

    probe = out/'C6-probe.log'
    probe.write_text('api_key = "'+'sk-'+'a12probe01234567890123456789'+'"\n')
    before_hash = digest(probe)
    scanner = ROOT/'labs/e13e14/scan_runtime_logs.py'
    hit = subprocess.run([sys.executable,str(scanner),str(probe)],capture_output=True,text=True)
    (out/'C6-hit.txt').write_text(hit.stdout+hit.stderr)
    probe.write_text('clean probe after negative check\n')
    clean = subprocess.run([sys.executable,str(scanner),str(probe)],capture_output=True,text=True)
    (out/'C6-clean.txt').write_text(clean.stdout+clean.stderr)
    assert (hit.returncode,clean.returncode) == (1,0)
    save(out/'C6-hashes.json', {'before':before_hash,'after':digest(probe),'fake_value_not_committed':True})
    row('C6', ['C6-hit.txt','C6-clean.txt','C6-hashes.json'], hit_code=hit.returncode, clean_code=clean.returncode)

    failed = run(dict(a_req, base='0'*40), out/'C7-failed')
    good = run(a_req, out/'C7-recovery')
    assert failed['status']=='FAILED' and good['status']=='SUCCEEDED'
    assert failed['job_id'] != good['job_id'] and failed['trace_id'] != good['trace_id']
    row('C7', ['C7-failed','C7-recovery'], failed_job=failed['job_id'], recovery_job=good['job_id'])

    client = out/'C8-api'
    client.mkdir()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    log = (client/'server.log').open('w')
    api = subprocess.Popen([sys.executable,str(ROOT/'labs/e11e12/server.py'),'--host','127.0.0.1','--port',str(port)],stdout=log,stderr=subprocess.STDOUT)
    url = f'http://127.0.0.1:{port}'
    def http(path, body=None):
        request = urllib.request.Request(url+path, data=json.dumps(body).encode() if body else None,
                                         headers={'Content-Type':'application/json'})
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response=error
        with response:
            return response.code, dict(response.headers), response.read()
    try:
        for _ in range(100):
            try:
                if http('/health')[0]==200:break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('API did not become healthy')
        body={'idempotency_key':'matrix-'+out.name,'input':a_req}
        save(client/'request.json',body)
        first=http('/v1/jobs',body);same=http('/v1/jobs',body)
        conflict=http('/v1/jobs',dict(body,input=dict(a_req,target=req['base'])))
        decoded=[{'http':r[0],'body':json.loads(r[2])} for r in [first,same,conflict]]
        save(client/'responses.json',decoded)
        assert [r[0] for r in [first,same,conflict]]==[202,202,409]
        jid=decoded[0]['body']['job_id']
        assert decoded[1]['body']['job_id']==jid and decoded[2]['body']['error']=='IDEMPOTENCY_CONFLICT'
        polls=[]
        for _ in range(180):
            state_json=json.loads(http('/v1/jobs/'+jid)[2]);polls.append(state_json)
            if state_json['status'] not in ['QUEUED','RUNNING']:break
            time.sleep(1)
        save(client/'polls.json',polls)
        assert state_json['status']=='SUCCEEDED',state_json
        artifact_result=json.loads(http('/v1/jobs/'+jid+'/artifacts')[2])
        save(client/'artifacts.json',artifact_result)
        code,headers,data=http('/v1/jobs/'+jid+'/files/incremental-check.json')
        (client/'downloaded-incremental.json').write_bytes(data)
        item=next(x for x in artifact_result['artifacts'] if x['uri'].endswith('/incremental-check.json'))
        assert code==200 and hashlib.sha256(data).hexdigest()==item['sha256']==headers['X-Content-SHA256']
        save(client/'download-headers.json',headers)
        row('C8', ['C8-api'], job_id=jid, download_sha256=item['sha256'])
    finally:
        api.terminate()
        api.wait(timeout=15)
        log.close()
    assert len(rows)==8
    print('ALL_LOCAL_C1_C8_PASS; B12 receipt is separately required', flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    args=p.parse_args()
    main(args.request,args.out.resolve())
