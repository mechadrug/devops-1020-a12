"""Cloud-host teaching entry point; Docker experiments run only on Linux."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
TRACK = 'A' if (ROOT / 'services/buildchecker').is_dir() else 'B'
SERVICE = 'buildchecker' if TRACK == 'A' else 'draft'
IMAGE = f'course1020-{SERVICE}:local'

def execute(command, folder, timeout=1800):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'command.json').write_text(json.dumps(command, indent=2), encoding='utf-8')
    with (folder / 'stdout.log').open('w', encoding='utf-8') as out, (folder / 'stderr.log').open('w', encoding='utf-8') as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
            if '--cidfile' in command:
                cid_file = Path(command[command.index('--cidfile') + 1])
                if cid_file.is_file():
                    cid = cid_file.read_text().strip()
                    if len(cid) == 64 and all(c in '0123456789abcdef' for c in cid):
                        try:
                            subprocess.run(['docker', 'rm', '-f', cid], stdout=err, stderr=err, timeout=20)
                        except (OSError, subprocess.TimeoutExpired):
                            err.write('\nCleanup incomplete; inspect saved service container ID.\n')
    (folder / 'exit-code.json').write_text(json.dumps({'exit_code': code}), encoding='utf-8')
    for name in ('stdout.log', 'stderr.log'):
        lines = (folder / name).read_text(encoding='utf-8', errors='replace').splitlines()
        print('\n'.join(lines[-35:]))
    return code

def container(extra=()):
    return ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp', *extra]

def main(argv=None):
    parser = argparse.ArgumentParser(description=f'Track {TRACK} cloud lab; run from your own course host')
    parser.add_argument('stage', choices=['doctor', 'build', 'e5', 'e6', 'gate'])
    parser.add_argument('--out', help='Fresh output directory, relative to this repository or absolute')
    parser.add_argument('--image', default=IMAGE)
    parser.add_argument('--fixed', action='store_true', help='A only: repair the declaration in an isolated copy')
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--candidate', help='B e6/gate: Dockerfile saved from your own model response')
    choice.add_argument('--replay', action='store_true', help='B e6/gate: explicitly use the supplied recorded DeepSeek response')
    parser.add_argument('--build-timeout', type=int, default=600)
    args = parser.parse_args(argv)
    if sys.platform != 'linux':
        parser.error('Run after SSH login on the Linux cloud host; Windows is not the experiment host')
    if args.build_timeout <= 0:
        parser.error('Build timeout must be positive')
    if TRACK == 'B' and args.stage in ('e6', 'gate') and not (args.candidate or args.replay):
        parser.error('Specify --candidate PATH or --replay; replay is not fresh model generation')
    if args.fixed and (TRACK != 'A' or args.stage != 'e6'):
        parser.error('--fixed is for A e6 only')
    if args.stage == 'doctor':
        return subprocess.run([sys.executable, 'scripts/doctor.py'], cwd=ROOT).returncode
    output = (ROOT / args.out).resolve() if args.out else ROOT / 'work' / f'{args.stage}-{datetime.now().strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}'
    if output != ROOT / 'work' and ROOT / 'work' not in output.parents:
        parser.error('Keep evidence below this repository work/ directory')
    if output == ROOT / 'work' or (output.exists() and any(output.iterdir())):
        parser.error('Use a fresh directory below work/; previous evidence is preserved')
    output.mkdir(parents=True, exist_ok=True)
    meta = {'track': TRACK, 'stage': args.stage, 'time_utc': datetime.now(timezone.utc).isoformat(), 'image': args.image, 'packaging_entrypoint': 'cloud-v1', 'replay': args.replay}
    (output / 'invocation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'EVIDENCE_DIR={output}', flush=True)
    if args.stage == 'build':
        code = execute(['docker', 'build', '--progress=plain', '-f', f'services/{SERVICE}/Dockerfile', '-t', args.image, '.'], output / 'build', args.build_timeout)
        if code:
            return code
        if execute(['docker', 'image', 'inspect', args.image], output / 'image', 30):
            return 1
        return execute(['docker', 'run', '--rm', '--network', 'none', args.image, 'pytest'], output / 'unit-tests', 180)
    if args.stage == 'gate':
        command = [sys.executable, f'scripts/run_e7_{TRACK.lower()}_gate.py', '--image', args.image, '--out', str(output / 'gate')]
        if TRACK == 'B':
            candidate = (ROOT / args.candidate).resolve() if args.candidate else ROOT / 'fixtures/ci-candidates/DeepSeek-E5.Dockerfile'
            command += ['--candidate', str(candidate), '--build-timeout', str(args.build_timeout)]
        return execute(command, output / 'driver', 12 * args.build_timeout + 1200)
    if TRACK == 'A':
        if args.stage == 'e5':
            shell = 'set -eu\ncp -R /app/fixtures/md-rd/. /evidence/\ncd /evidence\nmkdir trace\nmake clean\nstrace -ff -s 4096 -o trace/t -e trace=%file,%process make -p app > make-db.txt 2> build-stderr.log\n./app > program-output.txt\ngrep -n config.h trace/t.*\ngrep -n "^main.o:" make-db.txt\ncat program-output.txt\n'
            evidence = output / 'evidence'
            evidence.mkdir()
            return execute(container(['--network', 'none', '--cap-add', 'SYS_PTRACE', '--cidfile', str(output / 'service-container-id.txt'), '--mount', f'type=bind,src={evidence},dst=/evidence']) + [args.image, 'bash', '-c', shell], output / 'runner', 180)
        fixture = output / 'fixture'
        shutil.copytree(ROOT / 'fixtures/md-rd', fixture)
        if args.fixed:
            path = fixture / 'Makefile'
            text = path.read_text(encoding='utf-8')
            if 'main.o: main.c unused.h' not in text:
                raise ValueError('Review changed fixture before applying teaching repair')
            path.write_text(text.replace('main.o: main.c unused.h', 'main.o: main.c config.h'), encoding='utf-8')
        evidence = output / 'evidence'
        evidence.mkdir()
        return execute(container(['--network', 'none', '--cap-add', 'SYS_PTRACE', '--cidfile', str(output / 'service-container-id.txt'), '--mount', f'type=bind,src={fixture},dst=/fixture,readonly', '--mount', f'type=bind,src={evidence},dst=/evidence']) + [args.image, 'python3', '-m', 'buildchecker', 'full-check', '--fixture', '/fixture', '--out', '/evidence', '--fail-on-findings'], output / 'runner', 180)
    if args.stage == 'e5':
        project = output / 'project'
        shutil.copytree(ROOT / 'fixtures/draft', project, ignore=shutil.ignore_patterns('Dockerfile.reference'))
        iteration = output / 'iter-01'
        iteration.mkdir()
        first = (ROOT / 'fixtures/ci-candidates/DeepSeek-E5.Dockerfile').read_text(encoding='utf-8').splitlines()[0]
        broken = (project / 'Dockerfile.broken').read_text(encoding='utf-8').splitlines()
        dockerfile = first + '\n' + '\n'.join(broken[1:]) + '\n'
        (iteration / 'Dockerfile').write_text(dockerfile, encoding='utf-8')
        code = execute(['docker', 'build', '--progress=plain', '-f', str(iteration / 'Dockerfile'), '-t', f'course1020-b-broken:{uuid.uuid4().hex[:8]}', str(project)], iteration / 'build', args.build_timeout)
        log = '\n'.join((iteration / 'build' / n).read_text(encoding='utf-8', errors='replace') for n in ('stdout.log', 'stderr.log'))
        (iteration / 'build-retry.log').write_text(log, encoding='utf-8')
        (iteration / 'result-retry.json').write_text(json.dumps({'build_exit_code': code}), encoding='utf-8')
        if code in (0, 124) or 'make: not found' not in log:
            print('Baseline did not reach the expected missing-make error. Preserve logs and fix infrastructure.')
            return 1
        return subprocess.run([sys.executable, 'scripts/prepare_e5_prompts.py', '--run-dir', str(output)], cwd=ROOT).returncode
    candidate = (ROOT / args.candidate).resolve() if args.candidate else ROOT / 'fixtures/ci-candidates/DeepSeek-E5.Dockerfile'
    if not candidate.is_file():
        raise ValueError(f'Candidate missing: {candidate}')
    meta['candidate_sha256'] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    meta['candidate_source'] = 'supplied recorded response' if args.replay else 'student supplied; see student provenance record'
    (output / 'invocation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    evidence = output / 'evidence'
    evidence.mkdir()
    return execute(container(['--network', 'bridge', '--cidfile', str(output / 'service-container-id.txt'), '--group-add', str(Path('/var/run/docker.sock').stat().st_gid), '-v', '/var/run/docker.sock:/var/run/docker.sock', '--mount', f'type=bind,src={candidate},dst=/inputs/Dockerfile,readonly', '--mount', f'type=bind,src={evidence},dst=/evidence']) + [args.image, 'python3', '-m', 'draft', 'auto-build', '--fixture', '/app/fixtures/draft', '--candidate', '/inputs/Dockerfile', '--out', '/evidence', '--expected-output', 'hello E3', '--timeout', str(args.build_timeout)], output / 'runner', 2 * args.build_timeout + 180)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f'ERROR: {exc}')
