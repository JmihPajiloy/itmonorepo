#!/usr/bin/env python3
"""Audit actual Telemost audio/video captures without decrypting payloads.

Decode As only exposes RTP header fields. Payload types are negotiated values:
saved browser observations identify PT 111 / SSRC 0x6fb51938 and 0xeec9d003 as Opus;
the codec behind PT 98 or PT 49 is deliberately not guessed.
"""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated'
OUT.mkdir(exist_ok=True)
TSHARK = os.environ.get('TSHARK') or shutil.which('tshark') or '/Applications/Wireshark.app/Contents/MacOS/tshark'
SOURCE = ROOT / 'captures/telemost-video.pcapng'
AUDIO_SOURCE = ROOT / 'captures/telemost-audio.pcapng'
TEXT_SOURCE = ROOT / 'captures/telemost-text.pcapng'
FIELDS = ['frame.number', 'frame.time_epoch', 'frame.interface_name', 'frame.len', 'frame.cap_len',
          'frame.encap_type', 'eth.src', 'ip.len', 'tcp.srcport', 'tcp.dstport', 'tcp.len',
          'tls.record.content_type', '_ws.col.protocol',
          'ip.src', 'ip.dst', 'udp.srcport', 'udp.dstport', 'udp.length',
          'rtp.ssrc', 'rtp.p_type', 'rtp.seq', 'rtp.timestamp', 'rtp.marker']

def read(path, decode=False, ports=(21473, 22207, 22950, 22759)):
    args = [TSHARK, '-n', '-r', str(path)]
    if decode:
        for port in ports:
            args.extend(['-d', f'udp.port=={port},rtp'])
        args.extend(['-Y', 'rtp.version == 2'])
    args += ['-T', 'fields', '-E', 'header=y', '-E', 'separator=\t', '-E', 'quote=d', '-E', 'occurrence=f']
    for field in FIELDS:
        args += ['-e', field]
    return list(csv.DictReader(io.StringIO(subprocess.check_output(args, text=True)), delimiter='\t'))

def summarize(rows):
    if not rows:
        return {'packets': 0, 'duration_s': 0, 'frame_bytes': 0}
    start = float(rows[0]['frame.time_epoch'])
    end = float(rows[-1]['frame.time_epoch'])
    size = sum(int(r['frame.len']) for r in rows)
    return {'packets': len(rows), 'duration_s': round(end-start, 6), 'frame_bytes': size,
            'mean_frame_bytes': round(size / len(rows), 3),
            'rate_kbit_s': round(size * 8 / (end-start) / 1000, 3) if end > start else 0,
            'truncated_packets': sum(int(r['frame.cap_len']) < int(r['frame.len']) for r in rows)}

def stream_details(rtp_rows, capture_duration):
    streams = defaultdict(list)
    for row in rtp_rows:
        key = tuple(row[x] for x in ['ip.src', 'udp.srcport', 'ip.dst', 'udp.dstport', 'rtp.ssrc', 'rtp.p_type'])
        streams[key].append(row)
    output = []
    for key, selected in streams.items():
        timestamps = [float(r['frame.time_epoch']) for r in selected]
        seq = [int(r['rtp.seq']) for r in selected]
        delta = [((seq[i]-seq[i-1]) % 65536) for i in range(1, len(seq))]
        src, sport, dst, dport, ssrc, pt = key
        interpretation = ('Opus audio: SSRC and PT were identified in WebRTC Internals'
            if ssrc in ('0x6fb51938', '0xeec9d003') and pt == '111' else
            'PT 111 stream; same conference, exact codec requires its SDP mapping' if pt == '111' else
            'PT 98 stream during camera-on session; video codec is not established by PT alone' if pt == '98' else
            'Other RTP stream; media/repair function and codec are not established')
        output.append({
            'source': f'{src}:{sport}', 'destination': f'{dst}:{dport}', 'ssrc': ssrc,
            'payload_type': int(pt), 'interpretation': interpretation, **summarize(selected),
            'whole_capture_rate_kbit_s': round(sum(int(r['frame.len']) for r in selected) * 8 / capture_duration / 1000, 3),
            'median_interarrival_ms': round(statistics.median(
                [1000*(timestamps[i]-timestamps[i-1]) for i in range(1, len(timestamps))]), 4) if len(timestamps)>1 else None,
            'sequence_first': seq[0], 'sequence_last': seq[-1],
            'rtp_timestamp_first': int(selected[0]['rtp.timestamp']),
            'rtp_timestamp_last': int(selected[-1]['rtp.timestamp']),
            'distinct_rtp_timestamps': len({r['rtp.timestamp'] for r in selected}),
            'max_packets_per_rtp_timestamp': max(Counter(r['rtp.timestamp'] for r in selected).values()),
            'sequence_step_counts': dict(Counter(delta).most_common()),
            'loss_estimate': None,
            'loss_estimate_note': 'No loss estimate: capture starts mid-session; repair/padding/reordering and truncation must be accounted for.',
        })
    return sorted(output, key=lambda x: -x['frame_bytes'])

def interface_details(selected_rows):
    output = defaultdict(list)
    for row in selected_rows:
        output[row['frame.interface_name']].append(row)
    return {name: summarize(selected) for name, selected in output.items()}

rows = read(SOURCE)
rtp = read(SOURCE, decode=True)
start = float(rows[0]['frame.time_epoch'])
duration = float(rows[-1]['frame.time_epoch'])-start
stream_results = stream_details(rtp, duration)
audio_rows = read(AUDIO_SOURCE)
audio_rtp = read(AUDIO_SOURCE, decode=True, ports=(22556, 22335, 21152, 22789))
audio_summary = summarize(audio_rows)
audio_streams = stream_details(audio_rtp, audio_summary['duration_s'])
audio_checks = [
    {'name': 'independent audio trace contains a sustained interval longer than 30 s',
     'passed': audio_summary['duration_s'] > 30},
    {'name': 'audio RTP headers include the browser-confirmed Opus SSRC 4006203395 / PT 111',
     'passed': any(r['rtp.ssrc'] == '0xeec9d003' and r['rtp.p_type'] == '111' for r in audio_rtp)},
    {'name': 'audio RTP payload types are all 111 in the selected conference ports',
     'passed': bool(audio_rtp) and {r['rtp.p_type'] for r in audio_rtp} == {'111'}},
    {'name': 'audio trace contains outgoing and incoming RTP at the verified media server',
     'passed': any(r['ip.src'] == '77.88.42.81' for r in audio_rtp)
           and any(r['ip.dst'] == '77.88.42.81' for r in audio_rtp)},
]
if not all(c['passed'] for c in audio_checks):
    raise SystemExit('Independent audio validation failed: ' + repr(audio_checks))
audio_capture = {
    'source': AUDIO_SOURCE.name, 'summary': audio_summary,
    'interfaces': interface_details(audio_rows), 'rtp_header_packets': len(audio_rtp),
    'streams': audio_streams, 'checks': audio_checks,
    'browser_evidence': 'Camera disabled; organiser microphone enabled. WebRTC Internals: publisher 77.88.42.81:22556; guest receiver 77.88.42.81:22335, inbound Opus PT111 SSRC4006203395 (0xeec9d003).',
    'capture_limitation': 'dumpcap log reports 49 en0 packets flushed at capture completion; this is not a measured network loss rate.',
}
text_rows = read(TEXT_SOURCE)
text_summary = summarize(text_rows)
text_ui_path = ROOT / 'verification/telemost-text-ui-repeat.txt'
text_ui = text_ui_path.read_text()
text_flow = ('172.19.0.1', '58364', '87.250.250.43', '443')
text_outgoing = [r for r in text_rows if tuple(r[k] for k in
    ('ip.src', 'tcp.srcport', 'ip.dst', 'tcp.dstport')) == text_flow]
text_incoming = [r for r in text_rows if tuple(r[k] for k in
    ('ip.dst', 'tcp.dstport', 'ip.src', 'tcp.srcport')) == text_flow]
text_checks = [
    {'name': 'text trace is nonempty and has a nonzero packet timestamp interval',
     'passed': bool(text_rows) and text_summary['duration_s'] > 0},
    {'name': 'all text packets belong to the verified bidirectional TCP 58364 / 443 flow',
     'passed': bool(text_outgoing) and bool(text_incoming)
        and len(text_outgoing)+len(text_incoming) == len(text_rows)},
    {'name': 'text packets are Raw IP on utun4; IP length equals recorded original frame length',
     'passed': all(r['frame.interface_name'] == 'utun4' and not r['eth.src']
        and r['ip.len'] == r['frame.len'] for r in text_rows)},
    {'name': 'text flow has no UDP/RTP and includes encrypted TLS application records',
     'passed': all(not r['udp.srcport'] for r in text_rows)
        and any(r['tls.record.content_type'] == '23' for r in text_rows)},
    {'name': 'text snapshots are limited to 160 bytes after privacy postprocessing',
     'passed': all(int(r['frame.cap_len']) <= 160 for r in text_rows)},
    {'name': 'saved UI transcript confirms both control messages in two local tabs',
     'passed': 'контроль текста 1' in text_ui and 'контроль текста 2' in text_ui
        and 'Two local Chrome tabs of the same account' in text_ui},
]
if not all(c['passed'] for c in text_checks):
    raise SystemExit('Text flow validation failed: ' + repr(text_checks))
text_capture = {
    'source': TEXT_SOURCE.name, 'summary': text_summary,
    'interfaces': interface_details(text_rows), 'outgoing_packets': len(text_outgoing),
    'incoming_packets': len(text_incoming),
    'tcp_payload_bytes': sum(int(r['tcp.len']) for r in text_rows),
    'displayed_protocol_counts': dict(Counter(r['_ws.col.protocol'] for r in text_rows)),
    'capture_filter': 'tcp and host 87.250.250.43 and port 443 and port 58364',
    'verified_websocket': 'wss://ws.push.yandex.ru/v2/subscribe',
    'browser_evidence': 'Chrome DevTools showed WebSocket HTTP 101; lsof matched 172.19.0.1:58364 -> 87.250.250.43:443. Two local same-account tabs exchanged and independently displayed two control messages.',
    'ui_transcript': str(text_ui_path.relative_to(ROOT)),
    'encapsulation': 'Raw IP on utun4; frame.len has no Ethernet header',
    'privacy_postprocessing': 'editcap -s 160 applied to the saved trace; original frame.len and timestamps retained',
    'observed_max_capture_bytes': max(int(r['frame.cap_len']) for r in text_rows),
    'checks': text_checks,
    'limitations': [
        'Only the selected encrypted WebSocket notification flow is recorded; this is not all HTTP API or all messaging traffic.',
        'HTTP 101 and the WebSocket URL were observed in DevTools, not read from encrypted pcap payload.',
        'Packet timestamps span the observed traffic; the capture process had a separate 60-second upper limit.',
        'Raw IP text lengths and Ethernet media lengths have different link-layer accounting.',
        'TLS record labels in a midstream trace do not by themselves prove the negotiated TLS version.',
    ],
}
text_metadata = {
    'phase': 'text', **text_capture,
    'capture_duration_limit_seconds': 60,
    'first_packet_utc': datetime.fromtimestamp(float(text_rows[0]['frame.time_epoch']), timezone.utc).isoformat(),
    'last_packet_utc': datetime.fromtimestamp(float(text_rows[-1]['frame.time_epoch']), timezone.utc).isoformat(),
    'account_scope': 'One account, two local Chrome tabs; no external participants.',
}
(ROOT / 'verification/telemost-text.json').write_text(json.dumps(text_metadata, ensure_ascii=False, indent=2) + '\n')

other = {}
for phase in ('idle', 'audio', 'text'):
    path = ROOT / f'captures/telemost-{phase}.pcapng'
    if path.exists():
        other[phase] = summarize(read(path))

result = {
    'source': SOURCE.name,
    'summary': summarize(rows),
    'interfaces': interface_details(rows),
    'rtp_header_packets': len(rtp),
    'streams': stream_results,
    'other_traces': other,
    'audio_capture': audio_capture,
    'text_capture': text_capture,
    'phase_comparison': {
        'text': text_summary, 'audio': audio_summary, 'video': summarize(rows),
        'video_to_audio_rate_ratio': round(summarize(rows)['rate_kbit_s'] / audio_summary['rate_kbit_s'], 3),
        'scope': 'Text: selected TCP/TLS WebSocket notification flow, Raw IP. Audio/video: selected conference media UDP, both local browser participants and directions, mainly Ethernet en0. Video includes audio.',
        'limitation': 'Different capture windows, selected services, network conditions, and Raw IP / Ethernet length accounting. Descriptive trace comparison, not full message-service accounting or codec-only bandwidth.',
    },
    'observations': [
        'The video trace contains a real mixed audio/video conference; it is not a separate audio-only experiment.',
        'UDP RTP header fields are read with explicit Decode As; SRTP media payload remains encrypted.',
        'Dynamic RTP payload type does not identify a codec without SDP or a corresponding browser observation.',
        'Rates use original frame.len and the actual packet timestamp interval; text snapshots were privacy-truncated to 160 bytes after capture.',
        'The en0 path carries media; utun4 only contains alternate-candidate STUN traffic in this trace.',
    ],
}
(OUT / 'media.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
with (OUT / 'media-streams.csv').open('w', newline='') as stream:
    fields = ['source', 'destination', 'ssrc', 'payload_type', 'packets', 'frame_bytes',
              'mean_frame_bytes', 'whole_capture_rate_kbit_s', 'median_interarrival_ms']
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(stream_results)
with (OUT / 'media-audio-streams.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(audio_streams)

os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.venv/matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 14, 'svg.fonttype': 'none'})
bins = defaultdict(lambda: Counter())
for row in rows:
    bins[row['frame.interface_name']][int(float(row['frame.time_epoch'])-start)] += int(row['frame.len'])
fig, ax = plt.subplots(figsize=(6.3, 3.8), constrained_layout=True)
for interface in ['en0', 'utun4']:
    ax.step(range(int(duration)+1), [bins[interface][i]*8/1000 for i in range(int(duration)+1)],
            where='mid', label=interface, linewidth=2)
ax.set(xlabel='Время от первого пакета, с', ylabel='Объём за интервал 1 с, кбит')
ax.grid(alpha=0.25)
ax.legend()
fig.savefig(OUT / 'media-traffic.svg')
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.3, 5.4), constrained_layout=True)
labels = [f'PT {s["payload_type"]}\n{s["ssrc"]}' for s in stream_results]
values = [s['whole_capture_rate_kbit_s'] for s in stream_results]
colors = ['#194c76' if s['payload_type']==98 else '#4b8b64' if s['payload_type']==111 else '#94733f' for s in stream_results]
ax.barh(range(len(values)), values, color=colors)
ax.set(yticks=range(len(values)), yticklabels=labels, xlabel='Скорость по frame.len, кбит/с')
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.25)
fig.savefig(OUT / 'media-streams.svg')
plt.close(fig)
fig, ax = plt.subplots(figsize=(6.3, 3.8), constrained_layout=True)
phase_rates = [text_summary['rate_kbit_s'], audio_summary['rate_kbit_s'], summarize(rows)['rate_kbit_s']]
phase_bars = ax.barh([0, 1, 2], phase_rates, color=['#94733f', '#4b8b64', '#194c76'])
ax.set(yticks=[0, 1, 2], yticklabels=['Текст\n(WebSocket)', 'Аудио', 'Видео\nс аудио'],
       xlabel='Скорость в выбранных трассах, кбит/с', xlim=(0, max(phase_rates)*1.22))
ax.invert_yaxis()
ax.grid(axis='x', alpha=0.25)
for bar, value in zip(phase_bars, phase_rates):
    ax.text(value+max(phase_rates)*0.02, bar.get_y()+bar.get_height()/2,
            f'{value:.1f}'.replace('.', ','), va='center', fontsize=14)
fig.savefig(OUT / 'media-phases.svg')
plt.close(fig)
print(f'Media audit: {len(rows)} frames, {duration:.6f} s, {len(stream_results)} RTP header streams')
print(f'Independent audio: {len(audio_rows)} frames, {audio_summary["duration_s"]:.6f} s; {len(audio_checks)} checks passed')
print(f'Text flow: {len(text_rows)} frames, {text_summary["duration_s"]:.6f} s; {len(text_checks)} checks passed')
