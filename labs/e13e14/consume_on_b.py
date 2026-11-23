"""Consume A12's exchange bundle using the receiver's own B repository.

Run inside the receiver's Linux course image with B source mounted at /b12,
the exchange at /exchange, and an empty evidence directory at /result.
This small bridge follows the component-consumption approach in Ding's E12
supplement, adding a verified exchange manifest and receiver identity.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def command(args, cwd, log):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=120)
    log.write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:
        raise ValueError('COMMAND_FAILED: '+str(log))
    return r.stdout.strip()


def consume(exchange, b_repo, out, executor, validate_only=False):
    if out.exists():
        raise ValueError('Use a new output directory; preserve earlier evidence')
    out.mkdir(parents=True)
    result={'status':'RUNNING','executor':executor,'b_job_id':'job-'+uuid.uuid4().hex}
    try:
        manifest=json.loads((exchange/'EXCHANGE.json').read_text(encoding='utf-8'))
        for entry in manifest['files']:
            p=(exchange/entry['path']).resolve()
            if not p.is_relative_to(exchange.resolve()) or not p.is_file() or sha(p)!=entry['sha256']:
                raise ValueError('ARTIFACT_HASH_MISMATCH: '+entry['path'])
        sys.path.insert(0,str(exchange))
        from handoff_a_to_b import make_handoff
        report=make_handoff(exchange/'a-result/result.json',manifest['target_commit'])
        if report['source_report']!=manifest['source_report']:
            raise ValueError('A_REPORT_IDENTITY_MISMATCH')
        save(out/'received-fixed-md.json',report)
        result.update(a_source_sha=manifest['a_source_sha'],target_commit=manifest['target_commit'],
                      source_report=report['source_report'],trace_id=report['source_report']['trace_id'])
        if validate_only:
            result['status']='VALIDATED_ONLY'
            return result
        identity=command(['git','config','--local','user.name'],b_repo,out/'b-identity.log')
        if identity!=executor:
            raise ValueError('Set B repository local git user.name to your own executor ID')
        result['b_source_sha']=command(['git','rev-parse','HEAD'],b_repo,out/'b-source-sha.log')
        result['b_source_status']=command(['git','status','--porcelain'],b_repo,out/'b-source-status.log')
        source_files=['services/draft/draft/autobuild.py','labs/e8e10/lab.py']
        command(['git','diff','--exit-code','HEAD','--',*source_files],b_repo,out/'b-source-unchanged.log')
        result['b_source_files']={f:sha(b_repo/f) for f in source_files}
        def load(name, path):
            spec=importlib.util.spec_from_file_location(name,path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return module
        builder=load('receiver_draft',b_repo/source_files[0])
        fixer=load('receiver_mdfixer',b_repo/source_files[1])
        project=out/'target-project'
        command(['git','clone','--no-hardlinks','--no-checkout',str(exchange/'project.bundle'),str(project)],out,out/'clone.log')
        command(['git','checkout','--detach',manifest['target_commit']],project,out/'checkout.log')
        before=command(['git','rev-parse','HEAD'],project,out/'target-before.log')
        draft=builder.auto_build(project,exchange/'candidate.Dockerfile',out/'draft-build','1',timeout=600)
        if draft['status']!='SUCCEEDED':
            raise ValueError('DRAFT_FAILED: '+str(draft.get('error')))
        diff,edits=fixer.patch(project,report['data'])
        if not diff:
            raise ValueError('NO_MISSING_DEPENDENCY')
        patchfile=out/'candidate.patch';patchfile.write_text(diff,encoding='utf-8')
        save(out/'repair-plan.json',edits)
        verdict=fixer.validate(project,patchfile,out/'validation')
        if not verdict['accepted']:
            raise ValueError('REPAIR_REJECTED: '+str(verdict))
        recheck=fixer.scan(project)
        save(out/'recheck.json',recheck)
        if any(f['type']=='MISSING' for f in recheck['findings']):
            raise ValueError('RECHECK_FAILED')
        command(['make','test'],project,out/'project-tests.log')
        result.update(status='SUCCEEDED',draft_status=draft['status'],validation=verdict,
                      target_before=before,patch_sha256=sha(patchfile),findings=recheck['findings'])
    except Exception as error:
        result.update(status='FAILED',error=str(error))
    finally:
        result['artifacts']=[{'path':p.relative_to(out).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
                             for p in sorted(out.rglob('*')) if p.is_file() and '.git' not in p.parts]
        save(out/'receipt.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exchange',type=Path,default=Path('/exchange'))
    parser.add_argument('--b-repo',type=Path,default=Path('/b12'))
    parser.add_argument('--out',type=Path,default=Path('/result/run'))
    parser.add_argument('--executor',required=True)
    parser.add_argument('--validate-only',action='store_true')
    a=parser.parse_args()
    if not a.executor.isdigit():parser.error('Use your own numeric student ID')
    r=consume(a.exchange.resolve(),a.b_repo.resolve(),a.out.resolve(),a.executor,a.validate_only)
    print(json.dumps({k:r.get(k) for k in ['status','executor','b_job_id','trace_id','error']},ensure_ascii=False))
    raise SystemExit(0 if r['status'] in ['SUCCEEDED','VALIDATED_ONLY'] else 1)
