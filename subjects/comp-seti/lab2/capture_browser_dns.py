#!/usr/bin/env python3
"""Record DNS for ISU while the user opens it in a fresh browser context."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--interface', default='utun4')
p.add_argument('--resolver', default='172.19.0.2')
p.add_argument('--seconds', type=int, default=30)
a = p.parse_args()
if not 1 <= a.seconds <= 60:
    p.error('duration must be between 1 and 60 seconds')
root = Path(__file__).resolve().parent
out = root / 'captures/browser-dns-isu.pcap'
if out.exists():
    p.error('existing evidence will not be overwritten')
ws = Path('/Applications/Wireshark.app/Contents/MacOS')
started = datetime.now(timezone.utc).isoformat()
flush = subprocess.run(['/usr/bin/dscacheutil', '-flushcache'], capture_output=True, text=True)
with (root / 'verification/browser-dns-capture.txt').open('w') as log:
    producer = subprocess.Popen([str(ws / 'dumpcap'), '-i', a.interface, '-f',
        f'host {a.resolver} and port 53', '-a', f'duration:{a.seconds}',
        '-F', 'pcap', '-w', '-'], stdout=subprocess.PIPE, stderr=log)
    # Background DNS names are discarded in memory and never written to disk.
    consumer = subprocess.Popen([str(ws / 'tshark'), '-n', '-r', '-', '-Y',
        'dns.qry.name == "isu.ifmo.ru"', '-F', 'pcap', '-w', str(out)],
        stdin=producer.stdout, stderr=log)
    producer.stdout.close()
    result = producer.wait(timeout=a.seconds + 10)
    filtered = consumer.wait(timeout=10)
(root / 'verification/browser-dns.json').write_text(json.dumps({
    'started_utc': started, 'duration_limit_s': a.seconds,
    'interface': a.interface, 'resolver': a.resolver,
    'saved_names': ['isu.ifmo.ru'],
    'dscacheutil_exit_code': flush.returncode,
    'dscacheutil_output': flush.stdout + flush.stderr,
    'dumpcap_exit_code': result, 'tshark_exit_code': filtered,
    'browser_action': 'Chrome Clear host cache, then ISU root opened in a new Incognito window',
}, ensure_ascii=False, indent=2) + '\n')
if result or filtered:
    raise SystemExit('capture failed; see verification/browser-dns-capture.txt')
print(out.name + ' saved')
