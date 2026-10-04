"""Build the tree and circular classification schemes with Matplotlib.

The two SVG files are the print artifacts; this script is their editable source.
Text placement is checked with Matplotlib's actual renderer before export.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(OUT.parent / ".venv" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Wedge


BLUE = "#286fbd"
ORANGE = "#cc7425"
GREEN = "#238451"
INK = "#1d2d3d"
MUTED = "#526273"

plt.rcParams.update(
    {
        "font.family": "Times New Roman",
        "font.size": 9.5,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    }
)


def write_figure(fig: plt.Figure, name: str) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    frame = fig.bbox
    for artist in fig.findobj(match=plt.Text):
        if not artist.get_visible() or not artist.get_text():
            continue
        bbox = artist.get_window_extent(renderer)
        if not frame.contains(bbox.x0, bbox.y0) or not frame.contains(bbox.x1, bbox.y1):
            raise ValueError(f"Text exceeds {name} canvas: {artist.get_text()}")
    fig.savefig(OUT / name, format="svg", facecolor="white")
    plt.close(fig)


def tree() -> None:
    fig, ax = plt.subplots(figsize=(6.55, 5.8))
    fig.subplots_adjust(left=0.025, right=0.975, top=0.985, bottom=0.025)
    ax.set(xlim=(0, 100), ylim=(0, 100))
    ax.axis("off")
    ax.text(50, 97, "Классификация игральных карт", ha="center", va="center",
            fontsize=13, fontweight="bold", color=INK)

    def connector(points: list[tuple[float, float]], color: str) -> None:
        xs, ys = zip(*points)
        ax.plot(xs, ys, color=color, lw=1.5, solid_capstyle="round", zorder=1)

    def node(x: float, y: float, w: float, h: float, number: str,
             label: str, color: str, face: str, font_size: float = 10) -> None:
        patch = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.01,rounding_size=1.6",
            facecolor=face, edgecolor=color, linewidth=1.4, zorder=3,
        )
        ax.add_patch(patch)
        label_artist = ax.text(
            x, y, f"{number}  {label}", ha="center", va="center",
            fontsize=font_size, color=INK, zorder=4,
        )
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        if not patch.get_window_extent(renderer).contains(
            *label_artist.get_window_extent(renderer).get_points()[0]
        ) or not patch.get_window_extent(renderer).contains(
            *label_artist.get_window_extent(renderer).get_points()[1]
        ):
            raise ValueError(f"Node label does not fit: {label}")

    def basis(x: float, y: float, w: float, value: str, color: str) -> None:
        label = ax.text(x, y, value, ha="center", va="center", color=color,
                        fontsize=8.7, fontweight="bold", zorder=5)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        boundary_x0 = ax.transData.transform((x - w / 2, y))[0]
        boundary_x1 = ax.transData.transform((x + w / 2, y))[0]
        label_bounds = label.get_window_extent(renderer)
        if label_bounds.x0 < boundary_x0 or label_bounds.x1 > boundary_x1:
            raise ValueError(f"Basis label does not fit: {value}")

    # Short gaps around the free-standing basis labels keep lines off the text.
    connector([(50, 81.5), (50, 79.5)], BLUE)
    connector([(50, 71.5), (50, 70.5), (23, 70.5), (23, 68.5)], BLUE)
    connector([(50, 70.5), (77, 70.5), (77, 68.5)], BLUE)
    connector([(77, 58.5), (77, 56.5)], ORANGE)
    connector([(77, 49.5), (77, 48.5), (62, 48.5), (62, 46)], ORANGE)
    connector([(77, 48.5), (88, 48.5), (88, 46)], ORANGE)
    connector([(62, 36), (62, 34.5)], GREEN)
    connector([(62, 26.5), (62, 25.5), (45, 25.5), (45, 23)], GREEN)
    connector([(62, 25.5), (67, 25.5), (67, 23)], GREEN)
    connector([(67, 25.5), (89, 25.5), (89, 23)], GREEN)

    node(50, 86, 33, 9, "1", "Карты колоды (52)", INK, "#f1f4f6", 11)
    basis(50, 75.5, 79, "Шаг 1 · цвет масти · дихотомическое деление", BLUE)
    node(23, 63.5, 40, 10, "3", "Чёрные масти", BLUE, "#e8f2fc")
    node(77, 63.5, 40, 10, "2", "Красные масти", BLUE, "#e8f2fc")

    basis(75, 53, 49, "Шаг 2 · масть · видоизменение признака", ORANGE)
    node(62, 41, 23, 10, "4", "Черви", ORANGE, "#fff0e0", 9.5)
    node(88, 41, 23, 10, "5", "Бубны", ORANGE, "#fff0e0", 9.5)

    basis(76, 30, 47, "Шаг 3 · достоинство · видоизменение признака", GREEN)
    node(45, 18, 20, 10, "6", "Числовые 2–10", GREEN, "#e6f3ea", 8.5)
    node(67, 18, 20, 10, "7", "Фигурные J–K", GREEN, "#e6f3ea", 8.5)
    node(89, 18, 20, 10, "8", "Туз (A)", GREEN, "#e6f3ea", 9)
    write_figure(fig, "tree.svg")


def circular() -> None:
    fig, ax = plt.subplots(figsize=(6.55, 4.8))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.975, bottom=0.025)
    ax.set(xlim=(-1.1, 4.95), ylim=(-2.35, 2.35), aspect="equal")
    ax.axis("off")
    ax.text(1.8, 2.18, "Круговая схема классификации", ha="center",
            va="center", fontsize=13, color=INK, fontweight="bold")

    def ring(r0: float, r1: float, a0: float, a1: float,
             face: str, edge: str) -> None:
        ax.add_patch(Wedge((0, 0), r1, a0, a1, width=r1-r0,
                           facecolor=face, edgecolor=edge, linewidth=1.25))

    ax.add_patch(Circle((0, 0), 0.43, facecolor="#f1f4f6",
                        edgecolor=INK, linewidth=1.25))
    ax.text(0, 0, "1", ha="center", va="center", fontsize=13,
            fontweight="bold", color=INK)

    # Each ring appears only around the branch divided at that step.
    ring(.46, .95, 90, 270, "#e7f1fc", BLUE)
    ring(.46, .95, -90, 90, "#d5e8fa", BLUE)
    ring(.99, 1.48, 0, 90, "#ffe9d2", ORANGE)
    ring(.99, 1.48, -90, 0, "#fff0df", ORANGE)
    for a0, a1, face in [(0, 30, "#e9f5ed"),
                         (30, 60, "#d8ebdf"),
                         (60, 90, "#c8e3d0")]:
        ring(1.52, 2.01, a0, a1, face, GREEN)

    def number(value: str, radius: float, angle: float, color: str) -> None:
        rad = math.radians(angle)
        ax.text(radius * math.cos(rad), radius * math.sin(rad), value,
                ha="center", va="center", fontsize=11,
                fontweight="bold", color=color)

    for value, radius, angle, color in [
        ("3", .7, 180, BLUE), ("2", .7, 0, BLUE),
        ("4", 1.23, 45, ORANGE), ("5", 1.23, -45, ORANGE),
        ("6", 1.75, 75, GREEN), ("7", 1.75, 45, GREEN),
        ("8", 1.75, 15, GREEN),
    ]:
        number(value, radius, angle, color)

    x = 2.26
    ax.text(x, 1.76, "Понятия", ha="left", va="center", fontsize=10.5,
            color=INK, fontweight="bold")
    names = [
        "1  Карты колоды (52)", "2  Красные масти",
        "3  Чёрные масти", "4  Черви",
        "5  Бубны", "6  Числовые 2–10",
        "7  Фигурные J–K", "8  Туз (A)",
    ]
    for i, name in enumerate(names):
        ax.text(x, 1.43 - i * .38, name, ha="left", va="center",
                fontsize=9.3, color=INK)

    ax.text(x, -1.58, "Основания деления", ha="left", va="center",
            fontsize=9.5, color=INK, fontweight="bold")
    for i, (color, label) in enumerate([
        (BLUE, "1  цвет масти"),
        (ORANGE, "2  масть красной карты"),
        (GREEN, "3  группа достоинств"),
    ]):
        y = -1.82 - i * .18
        ax.plot([x, x + .18], [y, y], color=color, lw=2.5,
                solid_capstyle="round")
        ax.text(x + .25, y, label, ha="left", va="center",
                fontsize=7.8, color=MUTED)
    write_figure(fig, "circle.svg")


def verify_partition() -> None:
    suits = ("черви", "бубны", "трефы", "пики")
    ranks = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
    deck = {(suit, rank) for suit in suits for rank in ranks}
    red = {card for card in deck if card[0] in {"черви", "бубны"}}
    black = deck - red
    hearts = {card for card in red if card[0] == "черви"}
    diamonds = red - hearts
    numbered = {card for card in hearts if card[1] in ranks[1:10]}
    pictured = {card for card in hearts if card[1] in {"J", "Q", "K"}}
    aces = hearts - numbered - pictured

    assert (len(deck), len(red), len(black)) == (52, 26, 26)
    assert (len(hearts), len(diamonds)) == (13, 13)
    assert (len(numbered), len(pictured), len(aces)) == (9, 3, 1)
    assert not (red & black or hearts & diamonds or numbered & pictured
                or numbered & aces or pictured & aces)
    assert red | black == deck
    assert hearts | diamonds == red
    assert numbered | pictured | aces == hearts


if __name__ == "__main__":
    verify_partition()
    tree()
    circular()
    print("Колода: 52 = 26 + 26; 26 = 13 + 13; 13 = 9 + 3 + 1.")
    print("Matplotlib diagrams generated; all text fits the drawing areas")
