#!/usr/bin/env python3
"""Recompute measurements and check protocol exchanges from saved captures."""
from collections import defaultdict
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-root', default='.',
                    help='Directory of captures and verification logs inside this lab')
parser.add_argument('--stand-only', action='store_true',
                    help='Check the six container experiments without external/browser captures')
args = parser.parse_args()
RUN_ROOT = (ROOT / args.run_root).resolve()
if not RUN_ROOT.is_relative_to(ROOT):
    parser.error('--run-root must stay inside this lab')
capture_names = ['stand-ping.pcap', 'stand-traceroute.pcap', 'stand-http-arp.pcap',
                 'stand-dns.pcap', 'stand-ftp.pcap', 'stand-dhcp.pcap']
if not args.stand_only:
    capture_names += ['isu-utilities.pcap', 'isu-dns-complete.pcap',
                      'browser-http.pcap', 'browser-dns-isu.pcap']
required = [RUN_ROOT / 'captures' / name for name in capture_names]
required.append(RUN_ROOT / 'verification/ftp-index.html')
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    parser.error('Missing evidence: ' + ', '.join(missing))
OUT = RUN_ROOT / 'generated'
OUT.mkdir(exist_ok=True)
TSHARK = os.environ.get('TSHARK') or shutil.which('tshark') or '/Applications/Wireshark.app/Contents/MacOS/tshark'
FIELDS = ['frame.number', 'frame.time_epoch', 'frame.len', 'frame.cap_len', 'frame.interface_name',
          'eth.src', 'eth.dst', 'ip.src', 'ip.dst', 'ip.len', 'ip.hdr_len', 'ip.id',
          'ip.flags.mf', 'ip.frag_offset', 'ip.ttl', 'ip.proto', 'icmp.type', 'icmp.code',
          'tcp.srcport', 'tcp.dstport', 'tcp.len', 'udp.srcport', 'udp.dstport', 'udp.length',
          'arp.opcode', 'arp.src.proto_ipv4', 'arp.dst.proto_ipv4',
          'http.request.method', 'http.response.code', 'http.content_length',
          'http.request.line', 'dns.id', 'dns.flags.response', 'dns.flags.authoritative',
          'dns.qry.name', 'dns.qry.type', 'dns.a', 'dns.ns', 'dns.soa.mname',
          'dhcp.option.dhcp', 'dhcp.id', 'dhcp.ip.your', 'dhcp.option.dhcp_server_id',
          'ftp.request.command', 'ftp.request.arg', 'ftp.response.code', 'ftp.response.arg',
          '_ws.col.protocol', '_ws.col.info']

def read(name):
    path = RUN_ROOT / 'captures' / name
    command = [TSHARK, '-n', '-r', str(path), '-T', 'fields', '-E', 'header=y',
               '-E', 'separator=\t', '-E', 'quote=d', '-E', 'occurrence=f']
    for field in FIELDS:
        command += ['-e', field]
    output = subprocess.check_output(command, text=True)
    rows = list(csv.DictReader(io.StringIO(output), delimiter='\t'))
    with (OUT / (path.stem + '.csv')).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows

def integer(row, key, default=0):
    value = row.get(key, '')
    return int(value, 16) if value.startswith('0x') else int(value) if value else default

def summarize(rows):
    if not rows:
        return {'packets': 0, 'duration_s': 0, 'frame_bytes': 0, 'mean_frame_bytes': 0,
                'bitrate_kbit_s': 0, 'udp_flows': []}
    start = float(rows[0]['frame.time_epoch'])
    end = float(rows[-1]['frame.time_epoch'])
    size = sum(integer(r, 'frame.len') for r in rows)
    flows = defaultdict(lambda: {'packets': 0, 'bytes': 0})
    for r in rows:
        if r['udp.srcport'] and integer(r, 'ip.proto') == 17:
            endpoints = sorted([(r['ip.src'], r['udp.srcport']), (r['ip.dst'], r['udp.dstport'])])
            key = ' ↔ '.join(f'{ip}:{port}' for ip, port in endpoints)
            flows[key]['packets'] += 1
            flows[key]['bytes'] += integer(r, 'frame.len')
    return {'packets': len(rows), 'duration_s': round(end - start, 6), 'frame_bytes': size,
            'mean_frame_bytes': round(size / len(rows), 2),
            'bitrate_kbit_s': round(size * 8 / (end - start) / 1000, 3) if end > start else 0,
            'udp_flows': [{'endpoints': key, **value} for key, value in sorted(
                flows.items(), key=lambda x: -x[1]['bytes'])]}

captures = {name: read(name) for name in capture_names}
checks = []
def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})

groups = defaultdict(list)
for row in captures['stand-ping.pcap']:
    if row['ip.src'] == '172.28.20.10' and row['ip.ttl'] == '64':
        groups[row['ip.id']].append(row)
fragmentation = []
for ident, group in groups.items():
    size = sum(integer(r, 'ip.len') - integer(r, 'ip.hdr_len') for r in group) - 8
    fragments = len(group)
    fragmentation.append({'data_bytes': size, 'fragments': fragments, 'ip_id': ident,
                          'frames': [integer(r, 'frame.number') for r in group],
                          'offset_units': [integer(r, 'ip.frag_offset') for r in group],
                          'ip_lengths': [integer(r, 'ip.len') for r in group]})
    check(f'ping-{size}: fragmentation matches MTU 1500', fragments == math.ceil((size + 8) / 1480))
    check(f'ping-{size}: final MF is zero', group[-1]['ip.flags.mf'] == 'False')
fragmentation.sort(key=lambda x: x['data_bytes'])
check('ping: sizes cover 100–10000 bytes', len(fragmentation) == 13 and
      fragmentation[0]['data_bytes'] == 100 and fragmentation[-1]['data_bytes'] == 10000)
with (OUT / 'fragmentation.csv').open('w', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['data_bytes', 'observed_fragments'])
    writer.writerows((x['data_bytes'], x['fragments']) for x in fragmentation)

traceroute = captures['stand-traceroute.pcap']
ttl = [integer(r, 'ip.ttl') for r in traceroute if r['ip.src'] == '172.28.20.10'
       and r['ip.proto'] == '1' and r['icmp.type'] == '8']
check('traceroute: increasing ICMP TTL starts with 1, 2, 3', ttl[:3] == [1, 2, 3] and ttl == sorted(ttl))
check('traceroute: destination sends Echo Reply', any(
    r['ip.src'] == '172.28.22.10' and r['icmp.type'] == '0' for r in traceroute))
check('traceroute: Time Exceeded from both routers',
      {'172.28.20.254', '172.28.21.20'} <= {r['ip.src'] for r in traceroute if r['icmp.type'] == '11'})

http_arp = captures['stand-http-arp.pcap']
http = [r for r in http_arp if r['http.request.method'] or r['http.response.code']]
check('HTTP: responses are 200 then 304', [r['http.response.code'] for r in http if r['http.response.code']] == ['200', '304'])
conditional_frames = subprocess.check_output([TSHARK, '-n', '-r',
    str(RUN_ROOT / 'captures/stand-http-arp.pcap'), '-Y', 'http.request && http contains "If-Modified-Since"',
    '-T', 'fields', '-e', 'frame.number'], text=True).split()
check('HTTP: conditional GET contains If-Modified-Since', len(conditional_frames) == 1)
if 'browser-http.pcap' in captures:
    browser_http = captures['browser-http.pcap']
    browser_responses = [r['http.response.code'] for r in browser_http if r['http.response.code']]
    browser_conditions = subprocess.check_output([TSHARK, '-n', '-r',
        str(RUN_ROOT / 'captures/browser-http.pcap'), '-Y',
        'http.request && http contains "If-Modified-Since"', '-T', 'fields', '-e', 'frame.number'],
        text=True).split()
    check('Browser: real GET receives 200 and subsequent conditional GET receives 304',
          browser_responses == ['200', '404', '304'] and len(browser_conditions) == 1)
    check('Browser: local educational page returns 476-byte entity',
          any(r['http.response.code'] == '200' and r['http.content_length'] == '476'
              for r in browser_http))
arp = [r for r in http_arp if r['arp.opcode']]
check('ARP: request and reply observed', {'1', '2'} <= {r['arp.opcode'] for r in arp})

dns = captures['stand-dns.pcap']
check('DNS: authoritative A response', any(r['dns.a'] == '172.28.22.10' and r['dns.flags.authoritative'] == 'True' for r in dns))
check('DNS: NS response names ns.shibaev.test', any(r['dns.ns'] == 'ns.shibaev.test' for r in dns))
if 'browser-dns-isu.pcap' in captures:
    browser_dns = captures['browser-dns-isu.pcap']
    check('Browser DNS: one complete A query-response transaction for ISU',
          len(browser_dns) == 2 and browser_dns[0]['dns.flags.response'] == 'False' and
          browser_dns[1]['dns.flags.response'] == 'True' and
          browser_dns[0]['dns.id'] == browser_dns[1]['dns.id'] and
          all(r['dns.qry.type'] == '1' for r in browser_dns))
    check('Browser DNS: resolver returns selected ISU IPv4 address',
          any(r['ip.src'] == '172.19.0.2' and r['dns.a'] == '77.234.212.21'
              for r in browser_dns))
    check('Browser DNS: saved trace excludes unrelated names',
          bool(browser_dns) and all(r['dns.qry.name'] == 'isu.ifmo.ru' for r in browser_dns))
if 'isu-dns-complete.pcap' in captures:
    public_dns = captures['isu-dns-complete.pcap']
    check('Public DNS: complete A and NS query-response exchanges', len(public_dns) == 6 and
          sum(r['dns.flags.response'] == 'True' for r in public_dns) == 3)
    check('Public DNS: isu.ifmo.ru resolves to selected public server', any(
        r['dns.qry.name'] == 'isu.ifmo.ru' and r['dns.a'] == '77.234.212.21' for r in public_dns))
    check('Public DNS: NS for host has zone SOA', any(
        r['dns.qry.name'] == 'isu.ifmo.ru' and r['dns.qry.type'] == '2' and
        r['dns.flags.response'] == 'True' and r['dns.soa.mname'] == 'ns.itmo.ru' for r in public_dns))

ftp = captures['stand-ftp.pcap']
ftp_data = [r for r in ftp if r['_ws.col.protocol'] == 'FTP-DATA']
ftp_bytes = sum(integer(r, 'tcp.len') for r in ftp_data)
check('FTP: data stream contains exactly source-file length', ftp_bytes == (ROOT / 'stand/www/index.html').stat().st_size)
check('FTP: downloaded content is identical', (RUN_ROOT / 'verification/ftp-index.html').read_bytes() == (ROOT / 'stand/www/index.html').read_bytes())
check('FTP: transfer completes with 226', any(r['ftp.response.code'] == '226' for r in ftp))

dhcp = [r for r in captures['stand-dhcp.pcap'] if r['dhcp.option.dhcp']]
transactions = defaultdict(list)
for r in dhcp:
    transactions[r['dhcp.id']].append(r)
dora = []
for xid, rows in transactions.items():
    messages = [integer(r, 'dhcp.option.dhcp') for r in rows]
    if {1, 2, 3, 5} <= set(messages):
        selected = [next(r for r in rows if integer(r, 'dhcp.option.dhcp') == x) for x in (1, 2, 3, 5)]
        dora.append({'xid': xid, 'frames': [integer(r, 'frame.number') for r in selected],
                     'address': selected[-1]['dhcp.ip.your'],
                     'server': selected[-1]['dhcp.option.dhcp_server_id']})
check('DHCP: two actual DORA transactions', len(dora) == 2)
check('DHCP: two releases', sum(r['dhcp.option.dhcp'] == '7' for r in dhcp) == 2)

media = {}
for phase in (() if args.stand_only else ('idle', 'text', 'audio', 'video')):
    path = RUN_ROOT / 'captures' / f'telemost-{phase}.pcapng'
    if path.exists():
        media[phase] = summarize(read(path.name))

results = {
    'analysis_scope': 'stand-only' if args.stand_only else 'full',
    'run_root': str(RUN_ROOT.relative_to(ROOT)),
    'tshark_version': subprocess.check_output([TSHARK, '--version'], text=True).splitlines()[0],
    'fragmentation': fragmentation, 'traceroute_icmp_ttls': ttl,
    'http': [{k: r[k] for k in ['frame.number', 'http.request.method', 'http.response.code',
                               'http.content_length', 'http.request.line']} for r in http],
    'http_conditional_frames': conditional_frames,
    'arp': [{k: r[k] for k in ['frame.number', 'arp.opcode', 'eth.src', 'eth.dst',
                              'arp.src.proto_ipv4', 'arp.dst.proto_ipv4']} for r in arp],
    'ftp_data_bytes': ftp_bytes, 'ftp_data_frames': [integer(r, 'frame.number') for r in ftp_data],
    'dhcp_dora': dora, 'telemost': media,
    'captures': {name: summarize(rows) for name, rows in captures.items()},
    'checks': checks,
    'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((RUN_ROOT / 'captures').glob('*')) if p.is_file()},
}
(OUT / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
(RUN_ROOT / 'verification/check.txt').write_text('\n'.join(
    f'{"PASS" if c["passed"] else "FAIL"}: {c["name"]}' for c in checks) + '\n')
if not all(x['passed'] for x in checks):
    raise SystemExit(f'Capture verification failed: see {RUN_ROOT / "verification/check.txt"}')

os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.venv' / 'matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 14, 'svg.fonttype': 'none'})
fig, ax = plt.subplots(figsize=(6.3, 3.8), constrained_layout=True)
ax.step([x['data_bytes'] for x in fragmentation], [x['fragments'] for x in fragmentation],
        where='post', color='#194c76', marker='o', linewidth=2)
ax.set(xlabel='Размер данных ICMP Echo Request, байт', ylabel='Число IPv4-пакетов',
       yticks=range(1, 8), xlim=(0, 10300), ylim=(0.5, 7.5))
ax.grid(alpha=0.25)
fig.savefig(OUT / 'fragmentation.svg')
plt.close(fig)
if dora:
    rows = captures['stand-dhcp.pcap']
    chosen = [next(r for r in rows if integer(r, 'frame.number') == n) for n in dora[0]['frames']]
    t0 = float(chosen[0]['frame.time_epoch'])
    fig, ax = plt.subplots(figsize=(6.3, 4.3), constrained_layout=True)
    ax.plot([0, 0], [0, 5], color='#8798a5', linewidth=1)
    ax.plot([1, 1], [0, 5], color='#8798a5', linewidth=1)
    names = ['Discover', 'Offer', 'Request', 'ACK']
    for i, (r, name) in enumerate(zip(chosen, names), 1):
        reverse = i in (2, 4)
        start, end = (1, 0) if reverse else (0, 1)
        ax.annotate('', xy=(end, i), xytext=(start, i),
                    arrowprops={'arrowstyle': '->', 'color': '#194c76', 'linewidth': 2})
        ports = '67 → 68' if reverse else '68 → 67'
        elapsed = float(r['frame.time_epoch']) - t0
        ax.text(0.5, i - 0.15, f'{name}; UDP {ports}; t={elapsed:.6f} с', ha='center', va='bottom')
    ax.text(0, 0, 'Клиент\n' + chosen[0]['eth.src'], ha='center', va='bottom')
    ax.text(1, 0, 'Сервер\n' + dora[0]['server'], ha='center', va='bottom')
    ax.set(xlim=(-0.3, 1.3), ylim=(5, -0.7))
    ax.axis('off')
    fig.savefig(OUT / 'dhcp-dora.svg')
    plt.close(fig)
print(f'{len(checks)} capture checks passed ({results["analysis_scope"]}, '
      f'run={results["run_root"]}); results and graphs: {OUT.relative_to(ROOT)}')
