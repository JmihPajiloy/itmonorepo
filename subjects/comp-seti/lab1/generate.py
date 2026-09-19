#!/usr/bin/env python3
"""Reproduce all bit transformations, checks, and waveform SVGs for lab 1."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "itmonorepo-matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"
MESSAGE = "Шибаев И.Д."
BIT_RATE = 1_000_000_000

TABLE_4B5B = {
    "0000": "11110", "0001": "01001", "0010": "10100", "0011": "10101",
    "0100": "01010", "0101": "01011", "0110": "01110", "0111": "01111",
    "1000": "10010", "1001": "10011", "1010": "10110", "1011": "10111",
    "1100": "11010", "1101": "11011", "1110": "11100", "1111": "11101",
}


def bits_from_bytes(data: bytes) -> str:
    return "".join(f"{value:08b}" for value in data)


def grouped(value: str, width: int = 8) -> str:
    return " ".join(value[i:i + width] for i in range(0, len(value), width))


def bits_to_hex(value: str) -> tuple[str, int]:
    padding = (-len(value)) % 4
    padded = value + "0" * padding
    return f"{int(padded, 2):0{len(padded)//4}X}", padding


def encode_4b5b(bits: str) -> str:
    assert len(bits) % 4 == 0
    return "".join(TABLE_4B5B[bits[i:i + 4]] for i in range(0, len(bits), 4))


def scramble(bits: str) -> str:
    """Self-synchronizing scrambler Bi = Ai xor B(i-3) xor B(i-5)."""
    result: list[int] = []
    for i, bit in enumerate(map(int, bits)):
        result.append(bit ^ (result[i - 3] if i >= 3 else 0) ^ (result[i - 5] if i >= 5 else 0))
    return "".join(map(str, result))


def descramble(bits: str) -> str:
    source = list(map(int, bits))
    result: list[int] = []
    for i, bit in enumerate(source):
        result.append(bit ^ (source[i - 3] if i >= 3 else 0) ^ (source[i - 5] if i >= 5 else 0))
    return "".join(map(str, result))


def levels(bits: str, method: str) -> list[int]:
    if method == "NRZ":
        return [level for bit in bits for level in ((1 if bit == "1" else -1),) * 2]
    if method == "Manchester":
        return [level for bit in bits for level in ((1, -1) if bit == "1" else (-1, 1))]
    if method == "DiffManchester":
        current = 1
        result: list[int] = []
        for bit in bits:
            if bit == "0":
                current *= -1
            result.append(current)
            current *= -1
            result.append(current)
        return result
    if method == "AMI":
        pulse = -1
        result = []
        for bit in bits:
            if bit == "1":
                pulse *= -1
                result.extend((pulse, pulse))
            else:
                result.extend((0, 0))
        return result
    if method == "MLT-3":
        states = (0, 1, 0, -1)
        index = 0
        result = []
        for bit in bits:
            if bit == "1":
                index = (index + 1) % len(states)
            result.extend((states[index], states[index]))
        return result
    raise ValueError(method)


def runs(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in values:
        if not result or value != values[sum(result) - 1]:
            result.append(1)
        else:
            result[-1] += 1
    return result


def longest_zero_run(bits: str) -> int:
    return max(map(len, bits.split("1")), default=0)


def characteristics(bits: str, method: str) -> dict[str, float]:
    n = len(bits)
    if method in {"Manchester", "DiffManchester"}:
        half_runs = runs(levels(bits, method))
        return {
            "f_min_mhz": BIT_RATE / max(half_runs) / 1e6,
            "f_avg_mhz": len(half_runs) * BIT_RATE / (2 * n) / 1e6,
            "f_max_mhz": BIT_RATE / min(half_runs) / 1e6,
        }
    if method == "NRZ":
        bit_runs = [length // 2 for length in runs(levels(bits, method))]
        return {
            "f_min_mhz": BIT_RATE / (2 * max(bit_runs)) / 1e6,
            "f_avg_mhz": len(bit_runs) * BIT_RATE / (2 * n) / 1e6,
            "f_max_mhz": BIT_RATE / (2 * min(bit_runs)) / 1e6,
        }
    gap = longest_zero_run(bits) + 1
    ones = bits.count("1")
    divisor = 2 if method == "AMI" else 4
    return {
        "f_min_mhz": BIT_RATE / (divisor * gap) / 1e6,
        "f_avg_mhz": ones * BIT_RATE / (divisor * n) / 1e6,
        "f_max_mhz": BIT_RATE / divisor / 1e6,
    }


def waveform_svg(bits: str, methods: list[str], filename: str, title: str) -> None:
    """Render publication-ready, vector timing diagrams with Matplotlib."""
    bits = bits[:32]
    labels = {"Manchester": "Манчестер", "DiffManchester": "Дифф.\nМанчестер"}
    colors = {
        "NRZ": "#2563EB",
        "AMI": "#EA580C",
        "MLT-3": "#7C3AED",
        "Manchester": "#059669",
        "DiffManchester": "#DC2626",
    }
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "svg.fonttype": "none",
        "svg.hashsalt": "itmonorepo-comp-seti-lab1",
    })
    figure_height = 0.65 + 1.05 * len(methods)
    fig, axes = plt.subplots(
        len(methods), 1, figsize=(11.5, figure_height), sharex=True, squeeze=False
    )
    axes = axes[:, 0]
    fig.set_label(title)

    for row, (axis, method) in enumerate(zip(axes, methods)):
        signal = levels(bits, method)
        x = np.arange(len(signal) + 1) / 2
        y = np.asarray(signal + [signal[-1]])

        for byte_start in range(0, len(bits), 8):
            if (byte_start // 8) % 2 == 0:
                axis.axvspan(byte_start, byte_start + 8, color="#F8FAFC", zorder=0)
        axis.step(x, y, where="post", color=colors[method], linewidth=2.4, zorder=3)
        axis.axhline(0, color="#94A3B8", linewidth=0.7, zorder=1)
        for boundary in range(0, len(bits) + 1, 8):
            axis.axvline(boundary, color="#64748B", linewidth=1.1, zorder=2)

        axis.set_xlim(0, len(bits))
        axis.set_ylim(-1.35, 1.35)
        axis.set_yticks((-1, 0, 1), labels=("−1", "0", "+1"))
        axis.set_ylabel(
            labels.get(method, method), rotation=0, ha="right", va="center",
            labelpad=35, fontsize=10, fontweight="medium", color="#1E293B",
        )
        axis.set_xticks(np.arange(0, len(bits) + 1, 4))
        axis.set_xticks(np.arange(0, len(bits) + 1, 1), minor=True)
        axis.grid(axis="x", which="minor", color="#E2E8F0", linewidth=0.55)
        axis.tick_params(axis="y", length=0, labelsize=9, colors="#475569")
        axis.tick_params(axis="x", which="minor", length=0)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#94A3B8")
        if row != len(methods) - 1:
            axis.tick_params(axis="x", labelbottom=False)

    top_axis = axes[0].secondary_xaxis("top")
    top_axis.set_xticks(np.arange(len(bits)) + 0.5, labels=list(bits))
    top_axis.tick_params(axis="x", length=0, pad=3, labelsize=9, colors="#334155")
    top_axis.spines["top"].set_visible(False)
    axes[-1].set_xlabel("Границы битовых интервалов", fontsize=9, color="#475569")
    fig.subplots_adjust(left=0.14, right=0.985, top=0.92, bottom=0.14, hspace=0.28)
    fig.savefig(
        OUT / filename,
        format="svg",
        facecolor="white",
        bbox_inches="tight",
        metadata={"Date": None, "Creator": "Matplotlib 3.9.4"},
    )
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    source_bytes = MESSAGE.encode("cp1251")
    source = bits_from_bytes(source_bytes)
    redundant = encode_4b5b(source)
    scrambled = scramble(source)
    assert descramble(scrambled) == source
    assert len(redundant) * 4 == len(source) * 5
    methods = ["NRZ", "AMI", "MLT-3", "Manchester", "DiffManchester"]
    variants = {"source": source, "4b5b": redundant, "scrambled": scrambled}
    redundant_hex, redundant_padding = bits_to_hex(redundant)
    scrambled_hex, scrambled_padding = bits_to_hex(scrambled)
    data = {
        "message": MESSAGE,
        "source_hex": source_bytes.hex(" ").upper(),
        "source_bits": grouped(source),
        "source_length_bits": len(source),
        "4b5b_bits": grouped(redundant),
        "4b5b_hex": redundant_hex,
        "4b5b_hex_right_padding_bits": redundant_padding,
        "4b5b_length_bits": len(redundant),
        "scrambled_bits": grouped(scrambled),
        "scrambled_hex": scrambled_hex,
        "scrambled_hex_right_padding_bits": scrambled_padding,
        "checks": {"descrambling_restores_source": True, "redundancy_percent": 25},
        "characteristics": {
            name: {method: characteristics(bits, method) for method in methods}
            for name, bits in variants.items()
        },
    }
    (OUT / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    waveform_svg(source, methods, "source-waveforms.svg", "Первые 32 бита исходного сообщения")
    waveform_svg(redundant, ["Manchester", "MLT-3"], "4b5b-waveforms.svg", "Первые 32 бита сообщения 4B/5B")
    waveform_svg(scrambled, ["Manchester", "MLT-3"], "scrambled-waveforms.svg", "Первые 32 бита скремблированного сообщения")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
