#!/usr/bin/env python3
"""Configure only the containers belonging to this laboratory."""
import argparse
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--output-root', default='.', help='New directory inside this lab; existing captures are preserved')
args = parser.parse_args()
result = (ROOT / args.output_root).resolve()
relative = result.relative_to(ROOT)
if (result / 'captures').exists() and any((result / 'captures').iterdir()):
    raise SystemExit('Existing evidence will not be overwritten. Use --output-root verification/runs/NEW_NAME')
for directory in ('captures', 'verification'):
    (result / directory).mkdir(parents=True, exist_ok=True)
container_result = '/lab' if str(relative) == '.' else '/lab/' + relative.as_posix()
def dc(*args):
    return subprocess.run(['docker', 'compose', *args], cwd=ROOT, check=True)
def execute(service, *args):
    dc('exec', '-T', '-e', 'LAB2_RUN_ROOT=' + container_result, service, *args)

dc('up', '-d', '--force-recreate')
execute('client', 'ip', 'route', 'replace', '172.28.22.0/24', 'via', '172.28.20.254')
execute('r1', 'ip', 'route', 'replace', '172.28.22.0/24', 'via', '172.28.21.20')
execute('r2', 'ip', 'route', 'replace', '172.28.20.0/24', 'via', '172.28.21.10')
execute('server', 'ip', 'route', 'replace', '172.28.20.0/24', 'via', '172.28.22.254')
dc('exec', '-T', '-d', 'server', 'sh', '-c',
   'exec python /lab/stand/services.py > ' + shlex.quote(container_result + '/verification/services.txt') + ' 2>&1')
dc('exec', '-T', '-d', 'server', 'sh', '-c',
   'exec dnsmasq --keep-in-foreground --conf-file=/lab/stand/dnsmasq.conf > ' +
   shlex.quote(container_result + '/verification/dnsmasq.txt') + ' 2>&1')
time.sleep(1)
execute('client', 'python', '/lab/stand/experiments.py', 'client')
execute('dhcp-client', 'python', '/lab/stand/experiments.py', 'dhcp')
