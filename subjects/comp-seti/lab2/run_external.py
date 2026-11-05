#!/usr/bin/env python3
"""Capture actual macOS utility traffic to the selected public site."""
from pathlib import Path
import json
import signal
import subprocess
import time
from datetime import datetime, timezone

root = Path(__file__).resolve().parent
target = '77.234.212.21'
iface = 'utun4'
resolver = '172.19.0.2'
out = root / 'captures/isu-utilities.pcap'
if out.exists():
    raise SystemExit('Existing evidence will not be overwritten')
def run(name, args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    (root / 'verification' / f'{name}.txt').write_text(
        '$ ' + ' '.join(args) + '\n' + result.stdout + result.stderr +
        f'\nexit_code={result.returncode}\n')
    return result.returncode
with (root / 'verification/isu-capture.txt').open('w') as log:
    proc = subprocess.Popen(['/Applications/Wireshark.app/Contents/MacOS/dumpcap',
        '-i', iface, '-F', 'pcap', '-a', 'duration:100', '-s', '0', '-w', str(out),
        '-f', f'(host {target} and (icmp or udp or tcp port 443)) or (host {resolver} and port 53)'],
        stderr=log)
    time.sleep(0.8)
    try:
        for size in [100, 1000, 1472, 1473, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]:
            run(f'isu-ping-{size}', ['ping', '-n', '-c', '1', '-W', '1500', '-s', str(size), target])
        run('isu-ping-ttl', ['ping', '-n', '-c', '1', '-W', '1500', '-m', '7', '-s', '100', target])
        run('isu-traceroute-icmp', ['traceroute', '-n', '-I', '-m', '12', '-q', '1', '-w', '1', target])
        run('isu-traceroute-udp', ['traceroute', '-n', '-m', '6', '-q', '1', '-w', '1', target])
        run('isu-nslookup-a', ['nslookup', 'isu.ifmo.ru', resolver])
        run('isu-nslookup-ns', ['nslookup', '-type=NS', 'isu.ifmo.ru', resolver])
        run('ifmo-nslookup-ns', ['nslookup', '-type=NS', 'ifmo.ru', resolver])
        run('isu-https-head', ['curl', '-sS', '-I', '--max-time', '15', 'https://isu.ifmo.ru/'])
    finally:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
(root / 'verification/isu-environment.json').write_text(json.dumps({
    'finished_utc': datetime.now(timezone.utc).isoformat(), 'interface': iface,
    'target': target, 'hostname': 'isu.ifmo.ru', 'resolver': resolver,
    'note': 'Actual macOS traffic via the current VPN tunnel; no TLS keys saved.'
}, ensure_ascii=False, indent=2) + '\n')
print('Public-site experiments finished; consult individual exit codes.')
