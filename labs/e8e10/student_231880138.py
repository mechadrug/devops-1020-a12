"""Personal E10 measurement: remove an indirect include and its header file."""
import argparse
import csv
from pathlib import Path
from statistics import median

from lab import buildchecker, commit, fixture, save, scan


def experiment(out):
    if out.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    out.mkdir(parents=True)
    project=out/'project'
    fixture(project)
    (project/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
    (project/'extra.h').write_text('#include "leaf.h"\n#define EXTRA 0\n')
    (project/'leaf.h').write_text('#define LEAF 7\n')
    commit(project,'231880138: indirect-header history')
    previous=scan(project)
    save(out/'history.json',previous)
    (project/'extra.h').write_text('#define EXTRA 0\n')
    (project/'leaf.h').unlink()
    commit(project,'231880138: remove indirect include and file')
    expected_actual={'main.o':['config.h','extra.h','main.c'],'helper.o':['helper.c']}
    expected_findings={('MISSING','main.o','config.h'),('MISSING','main.o','extra.h'),
                       ('REDUNDANT','main.o','unused.h')}
    rows=[]
    for repeat in range(1,6):
        inc,full=scan(project,previous),scan(project)
        equal=all(inc[key]==full[key] for key in ['actual','declared','findings'])
        assert equal
        assert inc['actual']==expected_actual
        assert {(f['type'],f['target'],f['dependency']) for f in inc['findings']}==expected_findings
        assert inc['resolved']==[['MISSING','main.o','leaf.h']] and inc['added']==[]
        assert inc['refreshed']==['main.o','helper.o'] and inc['reused']==[]
        save(out/f'removed-r{repeat}-incremental.json',inc)
        save(out/f'removed-r{repeat}-full.json',full)
        rows.append({'case':'transitive_removed','repeat':repeat,'equal':equal,
                     'incremental_s':inc['elapsed_s'],'full_s':full['elapsed_s'],
                     'reused':len(inc['reused']),'refreshed':len(inc['refreshed'])})
    with (out/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    inc_times=[r['incremental_s'] for r in rows]
    full_times=[r['full_s'] for r in rows]
    save(out/'performance-summary.json',{
        'case':'transitive_removed','n':5,
        'incremental_median_s':median(inc_times),'full_median_s':median(full_times),
        'incremental_min_s':min(inc_times),'incremental_max_s':max(inc_times),
        'full_over_incremental':median(full_times)/median(inc_times),
        'scope':'scan only; excludes full clean build'})
    buildchecker(project,out/'final-buildchecker')
    save(out/'gate.json',{'student':'231880138','track':'A','passed':True,'rows':5,
                          'independent_expected_edges':True,'dynamic_crosscheck':True})
    print('TRANSITIVE_REMOVAL_PASS',out)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    experiment(parser.parse_args().out.resolve())
