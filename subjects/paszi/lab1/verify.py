#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def require(path: str, fragments: list[str]) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    for fragment in fragments:
        if fragment not in content:
            raise SystemExit(f"{path}: missing required fragment: {fragment!r}")


def require_nonempty(path: str) -> None:
    artifact = ROOT / path
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise SystemExit(f"{path}: missing or empty artifact")


require(
    "verification/baseline.txt",
    [
        'PRETTY_NAME="Parrot Security 7.3 (echo)"',
        "Virtualization: qemu",
        "auditd             inactive",
        "nftables           inactive",
    ],
)
require(
    "verification/result.txt",
    [
        "PASS: PAM uses pam_pwquality",
        "PASS: reader can read",
        "PASS: writer can append",
        "PASS: unrelated subject is denied",
        "PASS: root SSH login disabled",
        "PASS: protected directory audit rule loaded",
        "PASS: nftables input policy is drop",
        "PASS: AppArmor kernel module enabled",
        "PASS: AIDE detects the controlled file change",
        "PASS: backup copies match",
        "ALL IMPLEMENTED CHECKS PASSED",
    ],
)
require(
    "report.typ",
    [
        '#bibliography("references.bib")',
        "@fstec-1992",
        "@parrot-download",
        "@fig:terminal-system",
        "@fig:terminal-access",
        "@fig:terminal-network",
        "@fig:terminal-integrity",
    ],
)
for screenshot in (
    "screenshots/01-system.png",
    "screenshots/02-access.png",
    "screenshots/03-services-network.png",
    "screenshots/04-audit-integrity.png",
):
    require_nonempty(screenshot)

print("PASS: evidence, report references and terminal screenshots are consistent")
