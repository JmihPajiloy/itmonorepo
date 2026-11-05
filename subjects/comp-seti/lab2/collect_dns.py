#!/usr/bin/env python3
"""Record complete nslookup exchanges, saving only the two laboratory names."""
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parent
ws = Path('/Applications/Wireshark.app/Contents/MacOS')
out = root / 'captures/isu-dns-complete.pcap'
if out.exists():
    raise SystemExit('Existing evidence will not be overwritten')
with (root / 'verification/isu-dns-complete-capture.txt').open('w') as log:
    producer = subprocess.Popen([str(ws / 'dumpcap'), '-i', 'utun4', '-f',
        'host 172.19.0.2 and port 53', '-a', 'duration:10', '-F', 'pcap', '-w', '-'],
        stdout=subprocess.PIPE, stderr=log)
    # The intermediate stream is not saved. Only responses/queries for the two
    # explicitly selected lab names reach the output file.
    consumer = subprocess.Popen([str(ws / 'tshark'), '-n', '-r', '-', '-Y',
        'dns.qry.name == "isu.ifmo.ru" || dns.qry.name == "ifmo.ru"',
        '-F', 'pcap', '-w', str(out)], stdin=producer.stdout, stderr=log)
    producer.stdout.close()
    time.sleep(0.6)
    for name, args in [
        ('isu-a-complete', ['nslookup', 'isu.ifmo.ru', '172.19.0.2']),
        ('isu-ns-complete', ['nslookup', '-type=NS', 'isu.ifmo.ru', '172.19.0.2']),
        ('ifmo-ns-complete', ['nslookup', '-type=NS', 'ifmo.ru', '172.19.0.2']),
    ]:
        result = subprocess.run(args, text=True, capture_output=True, timeout=8)
        (root / 'verification' / (name + '.txt')).write_text(
            '$ ' + ' '.join(args) + '\n' + result.stdout + result.stderr +
            f'\nexit_code={result.returncode}\n')
    producer.wait(timeout=15)
    if consumer.wait(timeout=5):
        raise SystemExit('DNS output filtering failed')
print('Complete DNS exchanges for isu.ifmo.ru and ifmo.ru saved.')
