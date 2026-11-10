"""Personal E10 measurement 231880224: compiler-flag change after declaration repair."""
import argparse
import csv
from pathlib import Path
from statistics import median

from lab import buildchecker, commit, fixture, save, scan


def experiment(out):
    if out.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    out.mkdir(parents=True)
    project=out/'project'; fixture(project)
    makefile=project/'Makefile'
    makefile.write_text(makefile.read_text().replace(
        'main.o: main.c unused.h','main.o: main.c unused.h config.h'))
    commit(project,'231880224: repaired declaration baseline')
    previous=scan(project); save(out/'history.json',previous)
    makefile.write_text(makefile.read_text().replace('-O0','-O1'))
    commit(project,'231880224: switch optimisation level')
    expected_actual={'main.o':['config.h','main.c'],'helper.o':['helper.c']}
    expected_findings={('REDUNDANT','main.o','unused.h')}
    rows=[]
    for repeat in range(1,6):
        incremental,full=scan(project,previous),scan(project)
        equal=all(incremental[key]==full[key] for key in ['actual','declared','findings'])
        assert equal
        assert incremental['actual']==expected_actual
        assert {(f['type'],f['target'],f['dependency']) for f in incremental['findings']}==expected_findings
        assert incremental['reused']==[] and set(incremental['refreshed'])=={'main.o','helper.o'}
        assert incremental['added']==[] and incremental['resolved']==[]
        save(out/f'flags-r{repeat}-incremental.json',incremental)
        save(out/f'flags-r{repeat}-full.json',full)
        rows.append({'case':'flags_after_repair','repeat':repeat,'equal':equal,
                     'incremental_s':incremental['elapsed_s'],'full_s':full['elapsed_s'],
                     'reused':len(incremental['reused']),'refreshed':len(incremental['refreshed'])})
    with (out/'results.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    incremental_times=[row['incremental_s'] for row in rows]
    full_times=[row['full_s'] for row in rows]
    summary={'case':'flags_after_repair','n':5,
             'incremental_median_s':median(incremental_times),'full_median_s':median(full_times),
             'incremental_min_s':min(incremental_times),'incremental_max_s':max(incremental_times),
             'full_over_incremental':median(full_times)/median(incremental_times),
             'scope':'scan only; excludes full clean build'}
    save(out/'performance-summary.json',summary)
    buildchecker(project,out/'final-buildchecker')
    save(out/'gate.json',{'student':'231880224','track':'A','passed':True,'rows':5,
                          'independent_expected_edges':True,'dynamic_crosscheck':True})
    print('FLAGS_AFTER_REPAIR_PASS',summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    experiment(parser.parse_args().out.resolve())
