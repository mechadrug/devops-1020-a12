"""Compose the existing E5-E10 teaching components using versioned artifacts."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e8e10'), str(ROOT / 'labs/e11e12/vendor'), '/app']
from lab import scan, patch, validate

class Failure(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def artifact(path, out, job_id):
    return {'uri': f'artifact://{job_id}/{path.relative_to(out).as_posix()}',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes':path.stat().st_size}

def check_envelope(report, commit, kind=None):
    if report.get('schema_version') != 'e11e12-1':
        raise Failure('SCHEMA_MISMATCH', 'Expected e11e12-1')
    if report.get('commit') != commit:
        raise Failure('STALE_REPORT', 'Report belongs to another commit')
    payload = report.get('data')
    if isinstance(payload, dict) and 'commit' in payload and payload['commit'] != commit:
        raise Failure('STALE_REPORT', 'Report data belongs to another commit')
    if report.get('status') != 'SUCCEEDED':
        raise Failure('UPSTREAM_FAILED', 'Upstream stage did not succeed')
    if kind and report.get('kind') != kind:
        raise Failure('ARTIFACT_TYPE_MISMATCH', kind)

def load_artifact(path, expected_sha256):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected_sha256:
        raise Failure('ARTIFACT_HASH_MISMATCH','Artifact content changed during transfer')
    return json.loads(data)

def command(argv, cwd, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
    log.write_text(p.stdout+p.stderr, encoding='utf-8')
    if p.returncode:
        raise Failure('COMMAND_FAILED', f'{argv[0]} failed; see {log.name}')
    return p.stdout.strip()

def snapshot(repo, revision, dest, logs):
    sha = command(['git','rev-parse','--verify',revision+'^{commit}'], repo, logs/(dest.name+'-resolve.log'))
    command(['git','clone','--no-hardlinks','--no-checkout',str(repo),str(dest)], repo, logs/(dest.name+'-clone.log'))
    command(['git','checkout','--detach',sha], dest, logs/(dest.name+'-checkout.log'))
    # E8-E10 profile; fail early instead of silently ignoring other targets.
    names = {p.name for p in dest.glob('*.c')}
    if names != {'main.c','helper.c'} or not (dest/'config.h').is_file():
        raise Failure('UNSUPPORTED_PROJECT', 'Expected main.c/helper.c/config.h and explicit Make rules')
    return sha

def full(project, folder):
    from buildchecker.fullcheck import full_check
    report = full_check(project, folder)
    if report.get('status') != 'SUCCEEDED':
        raise Failure('FULL_CHECK_FAILED', str(report.get('error', report.get('error_code'))))
    return report

def normalized(findings):
    return sorted((f['type'],f['target'],f['dependency']) for f in findings if f['target'] in ('main.o','helper.o'))

def execute(request, out, job_id=None):
    job_id = job_id or 'job-'+uuid.uuid4().hex
    trace_id = 'trace-'+uuid.uuid4().hex
    if out.exists() and any(out.iterdir()):
        raise Failure('OUTPUT_EXISTS', 'Use a fresh output directory')
    out.mkdir(parents=True, exist_ok=True)
    result = {'schema_version':'e11e12-1','job_id':job_id,'trace_id':trace_id,'status':'RUNNING','stages':[]}
    save(out/'request.json',request)
    def stage(name, commit, payload, files=()):
        envelope = {'schema_version':'e11e12-1','job_id':job_id,'trace_id':trace_id,'kind':name,
                    'commit':commit,'status':'SUCCEEDED','data':payload,
                    'artifacts':[artifact(p,out,job_id) for p in files]}
        save(out/(name+'.json'),envelope)
        result['stages'].append({'name':name,'artifact':artifact(out/(name+'.json'),out,job_id)})
        return envelope
    try:
        mode=request['mode']
        if mode not in ('e11-a','e11-b','e12'):
            raise Failure('INVALID_REQUEST','Unknown mode')
        repo=Path(request['repo']).resolve()
        if not repo.is_dir():
            raise Failure('INVALID_REQUEST','Repository missing')
        base=out/'base-project'; target=out/'target-project'
        base_sha=snapshot(repo,request['base'],base,out/'logs')
        target_sha=snapshot(repo,request['target'],target,out/'logs')
        result.update(base_commit=base_sha,target_commit=target_sha)
        if mode in ('e11-b','e12'):
            from draft.autobuild import auto_build
            candidate=Path(request['candidate']).resolve()
            draft=auto_build(target,candidate,out/'draft-build',request.get('expected_output','1'),timeout=request.get('build_timeout',600))
            if draft['status']!='SUCCEEDED':
                raise Failure('DRAFT_FAILED',draft.get('error','Inspect draft-build logs'))
            stage('draft',target_sha,draft,[out/'draft-build/result.json'])
        if mode in ('e11-a','e12'):
            base_full=full(base,out/'baseline-full')
            old=scan(base)
            edges=json.loads((out/'baseline-full/actual-graph.json').read_text())
            projected={t:sorted({e['dependency'] for e in edges if e['target']==t}) for t in ('main.o','helper.o')}
            if projected != old['actual']:
                raise Failure('GRAPH_MISMATCH','BuildChecker baseline differs from GCC observations')
            old['actual']=projected
            save(out/'baseline-cache.json',old)
            baseline=stage('full-check',base_sha,base_full,[out/'baseline-full/actual-graph.json',out/'baseline-full/findings.json',out/'baseline-cache.json'])
            check_envelope(baseline,base_sha,'full-check')
            current=scan(target,old)
            save(out/'incremental-report.json',current)
            reference=full(target,out/'target-full')
            if normalized(reference['findings']) != normalized(current['findings']):
                raise Failure('FINDINGS_MISMATCH','Incremental/full object-target findings differ')
            md_envelope=stage('incremental-check',target_sha,current,[out/'incremental-report.json',out/'target-full/findings.json'])
        else:
            # E11-B still consumes a fixed MD input, separately from A's live output.
            fixed=Path(request['fixed_report'])
            envelope=json.loads(fixed.read_text(encoding='utf-8'))
            check_envelope(envelope,target_sha,'fixed-md')
            current=envelope['data']
            if current.get('commit') != target_sha:
                raise Failure('STALE_REPORT','Fixed report data commit mismatch')
            save(out/'fixed-md-input.json',envelope)
            md_envelope=stage('fixed-md',target_sha,current,[out/'fixed-md-input.json'])
        if mode in ('e11-b','e12'):
            reference=result['stages'][-1]['artifact']
            md_envelope=load_artifact(out/(md_envelope['kind']+'.json'),reference['sha256'])
            check_envelope(md_envelope,target_sha)
            current=md_envelope['data']
            before=(target/'Makefile').read_bytes()
            diff,edits=patch(target,current)
            if not diff:
                raise Failure('NO_MISSING_DEPENDENCY','No MD to repair')
            patchfile=out/'candidate.patch';patchfile.write_text(diff,encoding='utf-8')
            save(out/'repair-plan.json',edits)
            stage('repair',target_sha,{'edits':edits,'input_report':artifact(out/(md_envelope['kind']+'.json'),out,job_id)},[patchfile,out/'repair-plan.json'])
            verdict=validate(target,patchfile,out/'validation')
            if not verdict['accepted']:
                raise Failure('REPAIR_REJECTED',str(verdict))
            final=full(target,out/'final-full')
            if any(f['type']=='MISSING' for f in final['findings']):
                (target/'Makefile').write_bytes(before)
                raise Failure('RECHECK_FAILED','MD remains; working-copy declaration restored')
            stage('recheck',target_sha,{'validation':verdict,'findings':final['findings'],'patched_makefile_sha256':hashlib.sha256((target/'Makefile').read_bytes()).hexdigest()},[out/'validation/validation.json',out/'final-full/findings.json'])
        result['status']='SUCCEEDED'
    except (Failure,ValueError,OSError,KeyError,subprocess.TimeoutExpired) as exc:
        result.update(status='TIMED_OUT' if isinstance(exc,subprocess.TimeoutExpired) else 'FAILED',error={'code':getattr(exc,'code','EXECUTION_FAILED'),'message':str(exc)})
    result['artifacts']=[artifact(p,out,job_id) for p in sorted(out.rglob('*')) if p.is_file() and '.git' not in p.parts and not p.is_symlink()]
    save(out/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=execute(json.loads(a.request.read_text(encoding='utf-8')),a.out.resolve());print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='SUCCEEDED' else 1

if __name__=='__main__':raise SystemExit(main())
