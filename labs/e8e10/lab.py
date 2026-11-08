"""E8-E10 teaching profile: explicit C/Make rules, GCC dependency observation."""
import argparse, csv, difflib, json, re, shutil, subprocess, time
from pathlib import Path

def save(p, data):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def run(cmd, cwd):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=30)
    if p.returncode: raise ValueError('COMMAND_FAILED '+repr(cmd)+'\n'+p.stdout+p.stderr)
    return p.stdout

def fixture(p, style='direct'):
    p.mkdir(parents=True)
    (p/'main.c').write_text('#include <stdio.h>\n#include "config.h"\nint helper(void);\nint main(void){printf("%d\\n",VALUE+helper());return 0;}\n')
    (p/'helper.c').write_text('int helper(void){return 0;}\n')
    (p/'config.h').write_text('#define VALUE 1\n')
    (p/'extra.h').write_text('#define EXTRA 0\n')
    (p/'unused.h').write_text('/* unused */\n')
    prefix={'direct':'','macro':'DEPS = main.c unused.h\n','mixed':'HEADERS = unused.h\n'}[style]
    deps={'direct':'main.c unused.h','macro':'$(DEPS)','mixed':'main.c $(HEADERS)'}[style]
    (p/'Makefile').write_text(prefix+'CFLAGS = -O0\napp: main.o helper.o\n\tgcc main.o helper.o -o app\nmain.o: '+deps+'\n\tgcc $(CFLAGS) -c main.c -o main.o\nhelper.o: helper.c\n\tgcc $(CFLAGS) -c helper.c -o helper.o\n.PHONY: clean\nclean:\n\trm -f main.o helper.o app\n')
    run(['git','init','-b','main'],p)
    run(['git','config','user.name','TeachingFixture'],p)
    run(['git','config','user.email','fixture@localhost'],p)
    (p/'.gitignore').write_text('*.o\napp\n')
    commit(p,'C0 baseline')

def commit(p, msg):
    run(['git','add','.'],p); run(['git','commit','-m',msg],p)
    return run(['git','rev-parse','HEAD'],p).strip()

def declarations(p):
    text=(p/'Makefile').read_text()
    variables=dict(re.findall(r'^(\w+)\s*=\s*(.*)$',text,re.M))
    graph={}
    for target in ['main.o','helper.o']:
        m=re.search(r'^'+re.escape(target)+r': ([^\n]*)$',text,re.M)
        if not m: raise ValueError('UNSUPPORTED_RULE '+target)
        dep=m[1]
        for _ in range(8):
            dep=re.sub(r'\$\((\w+)\)',lambda x:variables.get(x[1],x[0]),dep)
        if '$' in dep or '%' in dep or '|' in dep: raise ValueError('UNSUPPORTED_DECLARATION')
        graph[target]=sorted(set(dep.split()))
    return graph,variables.get('CFLAGS','')

def scan(p, old=None):
    start=time.perf_counter(); declared,flags=declarations(p)
    if flags not in ['-O0','-O1','-O0 -DMODE=1']: raise ValueError('UNSUPPORTED_FLAGS')
    # Conservative invalidation: all local preprocessor lines, source set and recipes.
    files={x.name:x.read_text() for x in sorted(p.glob('*')) if x.suffix in ['.c','.h']}
    key={'directives':{n:[l for l in t.splitlines() if l.lstrip().startswith('#')] for n,t in files.items()},
         'recipes':[l for l in (p/'Makefile').read_text().splitlines() if l.startswith('\t')],
         'flags':flags,'compiler':run(['gcc','--version'],p).splitlines()[0]}
    actual={}; refreshed=[]; reused=[]
    for target,source in [('main.o','main.c'),('helper.o','helper.c')]:
        if old and old['key']==key and target in old['actual']:
            actual[target]=old['actual'][target]; reused.append(target)
        else:
            output=run(['gcc',*flags.split(),'-MM','-MT',target,source],p)
            actual[target]=sorted(set(output.replace('\\\n',' ').split(':',1)[1].split()))
            refreshed.append(target)
    findings=[]
    for t in actual:
        for kind,edges in [('MISSING',set(actual[t])-set(declared[t])),('REDUNDANT',set(declared[t])-set(actual[t]))]:
            findings.extend({'type':kind,'target':t,'dependency':d} for d in sorted(edges))
    current={ (f['type'],f['target'],f['dependency']) for f in findings}
    previous={ (f['type'],f['target'],f['dependency']) for f in old['findings']} if old else set()
    return {'schema_version':'e8e10-1','profile':'GCC_LOCAL_HEADERS_EXPLICIT_MAKE',
            'commit':run(['git','rev-parse','HEAD'],p).strip(),'key':key,'actual':actual,'declared':declared,
            'findings':findings,'added':[list(x) for x in sorted(current-previous)],
            'resolved':[list(x) for x in sorted(previous-current)],'refreshed':refreshed,'reused':reused,
            'elapsed_s':time.perf_counter()-start}

def patch(p,report):
    if report['commit']!=run(['git','rev-parse','HEAD'],p).strip(): raise ValueError('STALE_REPORT')
    original=(p/'Makefile').read_text(); changed=original; edits=[]
    for f in report['findings']:
        if f['type']!='MISSING': continue
        t,d=f['target'],f['dependency']
        if not re.fullmatch(r'[\w./-]+',d) or '..' in Path(d).parts or Path(d).is_absolute(): raise ValueError('UNSAFE_PATH')
        if not (p/d).is_file(): raise ValueError('MISSING_INPUT')
        m=re.search(r'^'+re.escape(t)+r': (.*)$',changed,re.M)
        if not m: raise ValueError('UNSUPPORTED_TARGET')
        raw=m[1]; macros=re.findall(r'\$\((\w+)\)',raw)
        if raw.strip()==('$(%s)'%macros[0] if macros else ''):
            name=macros[0]; vm=re.search(r'^'+name+r' = (.*)$',changed,re.M)
            if not vm: raise ValueError('UNSUPPORTED_MACRO')
            changed=changed[:vm.end()]+ ' '+d+changed[vm.end():]; style='macro'
        else:
            changed=changed[:m.end()]+' '+d+changed[m.end():]; style='mixed' if macros else 'direct'
        edits.append({'target':t,'dependency':d,'style':style})
    diff=''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='a/Makefile',tofile='b/Makefile'))
    return diff,edits

def validate(p, patchfile, evidence, fail_test=False):
    evidence.mkdir(parents=True); before=(p/'Makefile').read_bytes()
    sandbox=evidence/'sandbox'; shutil.copytree(p,sandbox,ignore=shutil.ignore_patterns('.git','*.o','app'))
    run(['git','init','-b','main'],sandbox)
    run(['git','config','user.name','ValidationSandbox'],sandbox)
    run(['git','config','user.email','fixture@localhost'],sandbox)
    commit(sandbox,'sandbox input')
    checks={}; error=None
    try:
        run(['git','apply','--check',str(patchfile.resolve())],sandbox); checks['patch_applies']=True
        run(['git','apply',str(patchfile.resolve())],sandbox)
        log=run(['make','clean'],sandbox)+run(['make','app'],sandbox);(evidence/'build.log').write_text(log);checks['build']=True
        output=run(['./app'],sandbox).strip(); checks['test']=output==('99' if fail_test else '1')
        # Real header-change build checks the originally broken incremental behavior.
        time.sleep(1.05); (sandbox/'config.h').write_text('#define VALUE 2\n')
        (evidence/'incremental.log').write_text(run(['make','app'],sandbox))
        checks['header_change']=run(['./app'],sandbox).strip()=='2'
        recheck=scan(sandbox); save(evidence/'recheck.json',recheck)
        checks['no_missing']=not any(f['type']=='MISSING' for f in recheck['findings'])
    except (ValueError,subprocess.TimeoutExpired) as ex: error=str(ex)
    accepted=bool(checks) and all(checks.values()) and error is None
    # Source remains untouched until all checks pass. Evidence sandbox is retained.
    if accepted: (p/'Makefile').write_bytes((sandbox/'Makefile').read_bytes())
    unchanged=(p/'Makefile').read_bytes()==before
    result={'accepted':accepted,'checks':checks,'error':error,'source_unchanged':unchanged,'rollback':not accepted and unchanged}
    save(evidence/'validation.json',result);return result

def buildchecker(p,out):
    import sys
    sys.path.insert(0,'/app')
    from buildchecker.fullcheck import full_check
    full_check(p,out)
    report=json.loads((out/'findings.json').read_text())
    if report['status']!='SUCCEEDED': raise ValueError('BUILDCHECKER_FAILED '+str(report))
    projected=[f for f in report['findings'] if f['target'] in ['main.o','helper.o']]
    oracle=scan(p)
    norm=lambda fs: sorted((f['type'],f['target'],f['dependency']) for f in fs)
    assert norm(projected)==norm(oracle['findings']), 'BuildChecker/GCC projection mismatch'
    return report

def demo(stage,out,track):
    if out.exists(): raise ValueError('OUTPUT_MUST_BE_NEW')
    out.mkdir(parents=True); p=out/'project';fixture(p); baseline=scan(p);save(out/'baseline.json',baseline)
    if stage=='e8':
        if track=='A':
            buildchecker(p,out/'buildchecker')
            edges=json.loads((out/'buildchecker/actual-graph.json').read_text())
            baseline['actual']={t:sorted({e['dependency'] for e in edges if e['target']==t}) for t in ['main.o','helper.o']}
            baseline['baseline_source']='BuildChecker actual-graph.json projected to object targets'
            save(out/'baseline.json',baseline)
            save(out/'incremental.json',scan(p,baseline))
        else:
            save(out/'fixed-md-report.json',baseline)
            diff,edits=patch(p,baseline);(out/'candidate.patch').write_text(diff);save(out/'patch-plan.json',edits)
            stale=dict(baseline,commit='0'*40)
            try: patch(p,stale)
            except ValueError as ex: save(out/'expected-failure.json',{'error':str(ex)})
        return
    if stage=='e9':
        if track=='A':
            (out/'C0-build.log').write_text(run(['make','app'],p))
            (p/'main.c').write_text((p/'main.c').read_text().replace('VALUE+helper()','VALUE+helper()+0'))
            commit(p,'C1 body change'); (out/'C1-build.log').write_text(run(['make','app'],p)); one=scan(p,baseline);save(out/'C1.json',one)
            (p/'main.c').write_text('#include "extra.h"\n'+(p/'main.c').read_text());commit(p,'C2 include change')
            (out/'C2-build.log').write_text(run(['make','app'],p)); two=scan(p,one); save(out/'C2.json',two)
            (p/'Makefile').write_text((p/'Makefile').read_text().replace('main.c unused.h','main.c unused.h config.h extra.h'))
            commit(p,'C3 repair declarations');save(out/'C3.json',scan(p,two))
        else:
            for style in ['direct','macro','mixed']:
                q=out/style;fixture(q,style);r=scan(q);diff,edits=patch(q,r)
                (out/(style+'.patch')).write_text(diff);save(out/(style+'-plan.json'),edits)
                assert (q/'Makefile').read_text().find('config.h')<0
        return
    rows=[]
    if track=='A':
        previous=baseline
        cases=['unchanged','body','include','declaration','flags','header']
        for case in cases:
            if case=='body': (p/'helper.c').write_text('int helper(void){return 0+0;}\n')
            if case=='include': (p/'main.c').write_text('#include "extra.h"\n'+(p/'main.c').read_text())
            if case=='declaration': (p/'Makefile').write_text((p/'Makefile').read_text().replace('main.c unused.h','main.c unused.h config.h extra.h'))
            if case=='flags': (p/'Makefile').write_text((p/'Makefile').read_text().replace('-O0','-O1'))
            if case=='header': (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            if case!='unchanged':commit(p,case)
            for repeat in range(5):
                inc=scan(p,previous); full=scan(p)
                passed=all(inc[k]==full[k] for k in ['actual','declared','findings'])
                rows.append({'case':case,'repeat':repeat+1,'equal':passed,'incremental_s':inc['elapsed_s'],'full_s':full['elapsed_s'],'reused':len(inc['reused']),'refreshed':len(inc['refreshed'])})
                assert passed,case
            save(out/(case+'.json'),inc); previous=inc
        buildchecker(p,out/'final-buildchecker')
    else:
        diff,_=patch(p,baseline); candidate=out/'candidate.patch';candidate.write_text(diff)
        rejected=validate(p,candidate,out/'reject-test',True);assert rejected['rollback']
        rows.append({'case':'test-rejection','passed':rejected['rollback']})
        accepted=validate(p,candidate,out/'accept');assert accepted['accepted']
        rows.append({'case':'accepted','passed':accepted['accepted']})
        broken=out/'broken.patch';broken.write_text('invalid patch\n')
        rejected2=validate(p,broken,out/'reject-patch');assert rejected2['rollback']
        rows.append({'case':'patch-rejection','passed':rejected2['rollback']})
        buildchecker(p,out/'recheck-buildchecker')
    with (out/'results.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save(out/'gate.json',{'track':track,'passed':True,'rows':len(rows)})

def main():
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['e8','e9','e10']);a.add_argument('--track',choices=['A','B'],required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
    demo(args.stage,args.out.resolve(),args.track);print('COMPLETED',args.stage,args.track,args.out)

if __name__=='__main__':main()
