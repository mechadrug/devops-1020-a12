"""Personal A-track evidence: a compiler flag enables an indirect dependency."""
import argparse
import csv
from pathlib import Path
from statistics import median

from lab import buildchecker, commit, fixture, save, scan


def experiment(out):
    if out.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    out.mkdir(parents=True)
    project = out / 'project'
    fixture(project)
    (project / 'config.h').write_text(
        '#ifdef MODE\n#include "extra.h"\n#endif\n#define VALUE 1\n'
    )
    commit(project, '231880397: conditional dependency baseline')
    previous = scan(project)
    assert previous['actual']['main.o'] == ['config.h', 'main.c']
    save(out / 'history.json', previous)

    makefile = project / 'Makefile'
    makefile.write_text(makefile.read_text().replace('CFLAGS = -O0', 'CFLAGS = -O0 -DMODE=1'))
    commit(project, '231880397: enable MODE')
    expected_actual = {
        'main.o': ['config.h', 'extra.h', 'main.c'],
        'helper.o': ['helper.c'],
    }
    expected_findings = {
        ('MISSING', 'main.o', 'config.h'),
        ('MISSING', 'main.o', 'extra.h'),
        ('REDUNDANT', 'main.o', 'unused.h'),
    }
    rows = []
    for repeat in range(1, 6):
        incremental, full = scan(project, previous), scan(project)
        equal = all(incremental[key] == full[key] for key in ('actual', 'declared', 'findings'))
        assert equal
        assert incremental['actual'] == expected_actual
        assert {
            (finding['type'], finding['target'], finding['dependency'])
            for finding in incremental['findings']
        } == expected_findings
        assert incremental['added'] == [['MISSING', 'main.o', 'extra.h']]
        assert incremental['refreshed'] == ['main.o', 'helper.o']
        assert incremental['reused'] == []
        save(out / f'flags-r{repeat}-incremental.json', incremental)
        save(out / f'flags-r{repeat}-full.json', full)
        rows.append({
            'case': 'conditional_flag', 'repeat': repeat, 'equal': equal,
            'incremental_s': incremental['elapsed_s'], 'full_s': full['elapsed_s'],
            'reused': len(incremental['reused']), 'refreshed': len(incremental['refreshed']),
        })
    with (out / 'results.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    save(out / 'performance-summary.json', {
        'case': 'conditional_flag', 'n': 5,
        'incremental_median_s': median(row['incremental_s'] for row in rows),
        'full_median_s': median(row['full_s'] for row in rows),
        'incremental_min_s': min(row['incremental_s'] for row in rows),
        'incremental_max_s': max(row['incremental_s'] for row in rows),
        'full_min_s': min(row['full_s'] for row in rows),
        'full_max_s': max(row['full_s'] for row in rows),
        'scope': 'scan only; excludes full clean build',
    })
    buildchecker(project, out / 'final-buildchecker')
    save(out / 'gate.json', {
        'student': '231880397', 'track': 'A', 'passed': True, 'rows': 5,
        'independent_expected_edges': True, 'dynamic_crosscheck': True,
    })
    print('CONDITIONAL_FLAG_PASS', out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    experiment(parser.parse_args().out.resolve())
