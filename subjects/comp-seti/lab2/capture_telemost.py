#!/usr/bin/env python3
"""Capture one bounded Telemost experiment using selected IPv4 endpoints.

Only the dedicated conference's WebRTC socket candidates and Telemost / push
server addresses are selected. TLS keys and decoded user data are not saved.
"""
import argparse
import ipaddress
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('phase', choices=['text', 'audio', 'video', 'probe'])
p.add_argument('--seconds', type=int, default=60)
p.add_argument('--media-host', default='77.88.42.102',
               help='IPv4 media server verified in WebRTC Internals for this session')
p.add_argument('--chat-host', help='IPv4 of the chat WebSocket verified in DevTools and DNS')
p.add_argument('--chat-local-port', type=int, help='Local TCP port of that verified WebSocket')
p.add_argument('--endpoint-evidence', default='',
               help='Observed ICE endpoint and codec information for this session')
a = p.parse_args()
if not 1 <= a.seconds <= 60:
    p.error('Duration must be between 1 and 60 seconds')
root = Path(__file__).resolve().parent
out = root / 'captures' / f'telemost-{a.phase}.pcapng'
if out.exists():
    p.error('Refusing to overwrite existing evidence')
# These remote endpoints were read from chrome://webrtc-internals for the
# two specific Telemost PeerConnections. Never collect all browser sockets.
media_host = str(ipaddress.IPv4Address(a.media_host))
expr = f'ip and udp and host {media_host}'
if a.phase == 'text':
    if not a.chat_host or not a.chat_local_port or not 1 <= a.chat_local_port <= 65535:
        p.error('For text, supply the verified --chat-host and --chat-local-port')
    chat_host = str(ipaddress.IPv4Address(a.chat_host))
    expr = f'ip and tcp and host {chat_host} and port 443 and port {a.chat_local_port}'
started = datetime.now(timezone.utc).isoformat()
cmd = ['/Applications/Wireshark.app/Contents/MacOS/dumpcap',
       '-i', 'utun4', '-s', '160', '-f', expr,
       '-i', 'en0', '-s', '160', '-f', expr,
       '-a', f'duration:{a.seconds}', '-w', str(out)]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=a.seconds + 10)
(root / 'verification' / f'telemost-{a.phase}.json').write_text(json.dumps({
    'phase': a.phase, 'started_utc': started,
    'finished_utc': datetime.now(timezone.utc).isoformat(),
    'seconds': a.seconds, 'snapshot_bytes': 160, 'interfaces': ['utun4', 'en0'],
    'verified_media_host': media_host, 'capture_filter': expr,
    'endpoint_evidence': a.endpoint_evidence,
    'verified_chat_host': a.chat_host if a.phase == 'text' else None,
    'verified_chat_local_port': a.chat_local_port if a.phase == 'text' else None,
    'returncode': result.returncode, 'capture_stderr': result.stderr,
    'method': 'Two local browser sessions in a private test conference; encrypted traffic only.',
}, ensure_ascii=False, indent=2) + '\n')
print(f'{out.name}: capture exit {result.returncode}')
raise SystemExit(result.returncode)
