#!/usr/bin/env python3
"""Bounded capture of Telegram IPv4 headers; never save application payload.

tcpdump filters the process before delivering a short snapshot through a pipe.
Only IPv4 + TCP base header / UDP header are written to the resulting pcap.
Packet wire lengths and timestamps are preserved for traffic statistics.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import threading
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument('phase', choices=['text', 'audio', 'video'])
p.add_argument('--seconds', type=int, default=60)
a = p.parse_args()
if not 1 <= a.seconds <= 60:
    p.error('Capture duration must be between 1 and 60 seconds')
root = Path(__file__).resolve().parents[2]
out = root / 'captures' / f'telegram-{a.phase}.pcap'
if out.exists():
    p.error(f'Refusing to overwrite existing evidence: {out}')
socket_list = subprocess.check_output(
    ['lsof', '-nP', '-a', '-c', 'Telegram', '-i4', '-F', 'nP'], text=True)
protocol = None
sockets = []
for line in socket_list.splitlines():
    if line.startswith('P'):
        protocol = line[1:].lower()
    if line.startswith('n') and protocol in ('tcp', 'udp'):
        local = line[1:].split('->')[0]
        host, port = local.rsplit(':', 1)
        if port.isdigit():
            sockets.append((protocol, host, int(port)))
if not sockets:
    p.error('No Telegram IPv4 sockets found; start the test session first')
terms = []
for protocol, host, port in sorted(set(sockets)):
    terms.append(f'({protocol} port {port})' if host == '*' else
                 f'({protocol} and ((src host {host} and src port {port}) or '
                 f'(dst host {host} and dst port {port})))')
capture_filter = 'ip and (' + ' or '.join(terms) + ')'
cmd = ['/Applications/Wireshark.app/Contents/MacOS/dumpcap', '-i', 'utun4',
       '-s', '100', '-a', f'duration:{a.seconds}', '-P', '-w', '-', '-f', capture_filter]
started = datetime.now(timezone.utc).isoformat()
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
timer = threading.Timer(a.seconds, proc.terminate)
timer.start()
count = 0
try:
    header = proc.stdout.read(24)
    if len(header) != 24 or header[:4] not in (b'\xd4\xc3\xb2\xa1', b'\xa1\xb2\xc3\xd4'):
        raise RuntimeError('tcpdump did not provide classic microsecond pcap')
    endian = '<' if header[:4] == b'\xd4\xc3\xb2\xa1' else '>'
    linktype = struct.unpack(endian + 'I', header[20:24])[0]
    offset = {0: 4, 1: 14, 12: 0, 101: 0, 228: 0}.get(linktype)
    if offset is None:
        raise RuntimeError(f'Unsupported link type: {linktype}')
    with out.open('wb') as stream:
        stream.write(header)
        while True:
            record = proc.stdout.read(16)
            if len(record) != 16:
                break
            sec, usec, size, original = struct.unpack(endian + 'IIII', record)
            data = proc.stdout.read(size)
            if len(data) != size:
                raise RuntimeError('Incomplete pcap record')
            ip = data[offset:]
            if len(ip) < 20 or ip[0] >> 4 != 4:
                continue
            ihl = (ip[0] & 15) * 4
            transport = 20 if ip[9] == 6 else 8 if ip[9] == 17 else 0
            # No application payload is retained, including UDP payload.
            saved = data[:offset + ihl + transport]
            stream.write(struct.pack(endian + 'IIII', sec, usec, len(saved), original))
            stream.write(saved)
            count += 1
finally:
    timer.cancel()
    if proc.poll() is None:
        proc.terminate()
    _, stderr = proc.communicate()
    (root / 'verification' / f'telegram-{a.phase}.json').write_text(json.dumps({
        'phase': a.phase, 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'requested_seconds': a.seconds, 'packets': count, 'interface': 'utun4',
        'process': 'Telegram', 'socket_selection': sockets,
        'capture_filter': capture_filter, 'payload_saved': False,
        'capture_stderr': stderr.decode(errors='replace'),
    }, ensure_ascii=False, indent=2) + '\n')
print(f'{out.name}: {count} packets; application payload omitted')
