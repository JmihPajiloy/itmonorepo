"""Run real clients and capture their traffic inside the teaching network."""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from email.utils import formatdate

ROOT = Path('/lab')
RESULT = Path(os.environ.get('LAB2_RUN_ROOT', '/lab'))
def run(name, args, allowed=(0,)):
    result = subprocess.run(args, capture_output=True, text=True, timeout=40)
    (RESULT / 'verification' / f'{name}.txt').write_text(
        '$ ' + ' '.join(args) + '\n' + result.stdout + result.stderr +
        f'\nexit_code={result.returncode}\n')
    if result.returncode not in allowed:
        raise RuntimeError(f'{name}: exit {result.returncode}')
    return result

@contextmanager
def capture(name, interface='eth0', expression='ip or arp'):
    path = RESULT / 'captures' / f'{name}.pcap'
    if path.exists():
        raise RuntimeError(f'Refusing to overwrite evidence: {path}')
    with (RESULT / 'verification' / f'{name}-capture.txt').open('w') as log:
        proc = subprocess.Popen(['tcpdump', '-n', '-i', interface, '-s', '0', '-U',
                                 '-w', str(path), expression], stderr=log)
        time.sleep(0.6)
        if proc.poll() is not None:
            raise RuntimeError('Capture failed to start')
        try:
            yield
        finally:
            time.sleep(0.4)
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)

def interface_for(prefix):
    links = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr']))
    return next(x['ifname'] for x in links if any(
        a.get('local', '').startswith(prefix) for a in x.get('addr_info', [])))

def client():
    iface = interface_for('172.28.20.')
    with capture('stand-ping', iface, 'icmp'):
        for size in [100, 1000, 1472, 1473, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]:
            run(f'stand-ping-{size}', ['ping', '-n', '-c', '1', '-W', '2', '-M', 'dont', '-s',
                str(size), '172.28.22.10'])
        run('stand-ping-ttl', ['ping', '-n', '-c', '1', '-W', '2', '-t', '7', '-p',
            'abcd', '-s', '100', '172.28.22.10'])
    with capture('stand-traceroute', iface, 'icmp or udp'):
        run('stand-traceroute-icmp', ['traceroute', '-n', '-I', '-q', '1', '-w', '1',
            '-m', '5', '172.28.22.10'])
        run('stand-traceroute-udp', ['traceroute', '-n', '-q', '1', '-w', '1',
            '-m', '5', '172.28.22.10'])
    with capture('stand-http-arp', iface, 'arp or tcp port 8000'):
        run('stand-neigh-flush', ['ip', 'neigh', 'flush', 'dev', iface])
        run('stand-http-get', ['curl', '--noproxy', '*', '-sS', '-D',
            str(RESULT / 'verification/http-first.headers'), 'http://172.28.22.10:8000/',
            '-o', str(RESULT / 'verification/http-first.html')])
        modified = formatdate((ROOT / 'stand/www/index.html').stat().st_mtime, usegmt=True)
        run('stand-http-conditional', ['curl', '--noproxy', '*', '-sS', '-D',
            str(RESULT / 'verification/http-conditional.headers'), '-H', f'If-Modified-Since: {modified}',
            'http://172.28.22.10:8000/', '-o', str(RESULT / 'verification/http-conditional.body')])
    with capture('stand-dns', iface, 'port 53'):
        run('stand-nslookup-a', ['nslookup', 'shibaev.test', '172.28.22.10'])
        run('stand-nslookup-ns', ['nslookup', '-type=NS', 'shibaev.test', '172.28.22.10'])
    with capture('stand-ftp', iface, 'tcp'):
        run('stand-ftp-get', ['curl', '--noproxy', '*', '-v', '--disable-epsv',
            'ftp://172.28.22.10/index.html', '-o', str(RESULT / 'verification/ftp-index.html')])
    assert (RESULT / 'verification/http-first.html').read_bytes() == (RESULT / 'verification/ftp-index.html').read_bytes()

def dhcp():
    iface = interface_for('172.28.23.')
    # Only the dedicated disposable container loses its initial Docker address.
    with capture('stand-dhcp', iface, 'udp port 67 or udp port 68 or arp'):
        run('dhcp-initial-address', ['ip', '-4', 'addr', 'show', 'dev', iface])
        run('dhcp-remove-static', ['ip', '-4', 'addr', 'flush', 'dev', iface])
        for cycle in range(1, 3):
            lease = f'/tmp/lab2-leases-{cycle}'
            pid = f'/tmp/lab2-dhclient-{cycle}.pid'
            args = ['dhclient', '-4', '-v', '-cf', '/lab/stand/dhclient.conf',
                    '-lf', lease, '-pf', pid]
            run(f'dhcp-acquire-{cycle}', args + ['-1', iface])
            run(f'dhcp-address-{cycle}', ['ip', '-4', 'addr', 'show', 'dev', iface])
            run(f'dhcp-release-{cycle}', args + ['-r', iface])

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('role', choices=['client', 'dhcp'])
    args = p.parse_args()
    globals()[args.role]()
    print(f'{args.role}: experiments completed at {datetime.now(timezone.utc).isoformat()}')
