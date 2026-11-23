"""Create A12's independently maintained policy project with reproducible history."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE_IMAGE = 'm.daocloud.io/docker.io/library/python:3.13-slim'
DIGEST = 'f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74'


def prepare(folder):
    if folder.exists():
        raise ValueError('Preserve the existing project; use a new directory')
    repo = folder / 'repo'
    repo.mkdir(parents=True)
    def write(name, text):
        (repo / name).write_text(text, encoding='utf-8', newline='\n')
    def git(*args, date=None):
        env = dict(os.environ)
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        return subprocess.check_output(['git', *args], cwd=repo, env=env, text=True).strip()
    git('init', '-b', 'main')
    git('config', 'user.name', '231880138')
    git('config', 'user.email', '231880138@localhost')
    git('config', 'core.autocrlf', 'false')
    write('.gitignore', 'app\n*.o\n')
    write('config.h', '#define VALUE 1\n')
    write('unused.h', '/* Retained RD: the detector must report rather than delete it. */\n')
    write('helper.c', 'int helper(void) { return 0; }\n')
    write('main.c', '''#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include "config.h"
int helper(void);
int main(int argc, char **argv) {
    long delta = 0;
    if (argc > 2) return 2;
    if (argc == 2) {
        char *end; errno = 0; delta = strtol(argv[1], &end, 10);
        if (errno || end == argv[1] || *end || delta < -1000 || delta > 1000) return 2;
    }
    printf("%ld\\n", VALUE + helper() + delta);
    return 0;
}
''')
    write('Makefile', '''CFLAGS = -O0
app: main.o helper.o
\tgcc main.o helper.o -o app
main.o: main.c unused.h
\tgcc $(CFLAGS) -c main.c -o main.o
helper.o: helper.c
\tgcc $(CFLAGS) -c helper.c -o helper.o
.PHONY: clean test
clean:
\trm -f main.o helper.o app
test: app
\tpython3 test_project.py
''')
    write('test_project.py', '''import subprocess
for args, expected in [([], '1'), (['0'], '1'), (['2'], '3'), (['-1'], '0')]:
    p = subprocess.run(['./app', *args], capture_output=True, text=True)
    assert (p.returncode, p.stdout.strip()) == (0, expected), (args, p)
for args in [['bad'], ['1x'], ['1001'], ['1','2']]:
    assert subprocess.run(['./app', *args], capture_output=True).returncode == 2, args
print('A12 policy project: 8 behavior cases PASS')
''')
    dockerfile = f'FROM {BASE_IMAGE}\nWORKDIR /work\nCOPY . .\nRUN make app\nCMD ["./app"]\n'
    write('Dockerfile.broken', dockerfile)
    write('README.md', '# A12 policy offset project\n\nOwner: 231880138 王备中. Derived from the course two-source build shape, with independent CLI argument validation, behavior tests, and a transitive policy-header change.\n\n`make test`: 8 behavior cases. Default output 1; changing VALUE to 2 yields 2. The C1 intentionally omits policy-header prerequisites, for detection and repair.\n')
    git('add', '.')
    git('commit', '-m', 'A12 C0: policy offset CLI with eight behavior tests', date='2026-11-23T14:00:00+08:00')
    base = git('rev-parse', 'HEAD')
    write('a12_policy.h', '#ifndef A12_POLICY_H\n#define A12_POLICY_H\n#include "policy_value.h"\n#define A12_OFFSET POLICY_OFFSET\n#endif\n')
    write('policy_value.h', '#define POLICY_OFFSET 0\n')
    write('helper.c', '#include "a12_policy.h"\nint helper(void) { return A12_OFFSET; }\n')
    git('add', '.')
    git('commit', '-m', 'A12 C1: read helper offset through a transitive policy header', date='2026-11-23T14:01:00+08:00')
    target = git('rev-parse', 'HEAD')
    candidate = dockerfile.replace(BASE_IMAGE, BASE_IMAGE + '@sha256:' + DIGEST).replace('COPY . .',
        "RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*\nCOPY . .")
    (folder / 'candidate.Dockerfile').write_text(candidate, encoding='utf-8', newline='\n')
    dataset = {'provider': 'A12 王备中 231880138', 'source': 'Course two-source shape; independently developed behavior and transitive-header change',
               'base_commit': base, 'target_commit': target, 'tests': 'make test (eight CLI cases)',
               'default_output': '1', 'header_change_output': '2',
               'candidate_source': 'Course digest-pinned toolchain replay adapted by 231880138; no model API call',
               'candidate_sha256': hashlib.sha256(candidate.encode()).hexdigest()}
    (folder / 'dataset.json').write_text(json.dumps(dataset, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    relative = folder.resolve().relative_to(ROOT.resolve()).as_posix()
    for mode in ['e11-a', 'e12']:
        request = {'mode': mode, 'repo': '/course/'+relative+'/repo', 'base': base, 'target': target,
                   'candidate': '/course/'+relative+'/candidate.Dockerfile', 'expected_output': '1', 'build_timeout': 600}
        (folder / ('request-'+mode+'.json')).write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
    git('bundle', 'create', str((folder/'project.bundle').resolve()), '--all')
    print(json.dumps(dataset, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT/'data/e13-a12-policy')
    prepare(p.parse_args().out.resolve())
