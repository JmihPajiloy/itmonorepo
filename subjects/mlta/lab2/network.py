"""Validate the selected judgments and draw their semantic network."""

from collections import Counter
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# The excerpt is from the published folk tale "Колобок", collected by A. N.
# Afanasyev. Its title and collection are identified in report.typ.
NODES = {
    "S1": ("Колобок", 700, 600),
    "S2": ("Заяц", 1180, 220),
    "S3": ("Волк", 1180, 580),
    "S4": ("Дедушка", 230, 180),
    "S5": ("Бабушка", 230, 470),
    "S6": ("Короб", 170, 1030),
    "S7": ("Сусек", 435, 1030),
    "S8": ("Сметана", 700, 1030),
    "S9": ("Масло", 965, 1030),
    "S10": ("Окошко", 1230, 1030),
}

RELATIONS = {
    "R1": "угрожает съесть",
    "R2": "обещает спеть",
    "R3": "ушёл от",
    "R4": "скребен по",
    "R5": "метен по",
    "R6": "мешон на",
    "R7": "пряжон в",
    "R8": "стужон на",
}

# Every edge is supported by a statement in the excerpt. The last two
# coordinates are the position of its label in the SVG.
EDGES = [
    ("S2", "R1", "S1", "M 1080 215 C 960 230 860 360 780 565", 925, 295),
    ("S3", "R1", "S1", "M 1080 555 C 950 530 865 550 800 580", 935, 510),
    ("S1", "R2", "S2", "M 790 575 C 960 465 1030 340 1080 230", 1050, 405),
    ("S1", "R2", "S3", "M 800 625 C 900 655 970 640 1080 605", 945, 685),
    ("S1", "R3", "S4", "M 620 565 C 505 420 400 290 315 205", 455, 350),
    ("S1", "R3", "S5", "M 600 600 C 470 555 390 515 325 485", 445, 535),
    ("S1", "R4", "S6", "M 625 635 C 505 800 375 930 250 990", 350, 805),
    ("S1", "R5", "S7", "M 665 645 C 600 805 535 920 445 990", 520, 850),
    ("S1", "R6", "S8", "M 700 650 L 700 990", 700, 830),
    ("S1", "R7", "S9", "M 735 645 C 800 805 865 920 955 990", 880, 850),
    ("S1", "R8", "S10", "M 775 635 C 895 800 1025 930 1150 990", 1050, 805),
]


def check():
    report = (ROOT / "report.typ").read_text(encoding="utf-8")
    assert len(NODES) >= 10
    assert list(NODES) == [f"S{i}" for i in range(1, len(NODES) + 1)]
    assert list(RELATIONS) == [f"R{i}" for i in range(1, len(RELATIONS) + 1)]
    assert len({(s, r, t) for s, r, t, *_ in EDGES}) == len(EDGES)
    assert all(s in NODES and t in NODES and r in RELATIONS
               for s, r, t, *_ in EDGES)
    counts = Counter(r for _, r, _, *_ in EDGES)
    assert sum(n >= 2 for n in counts.values()) >= 3
    assert report.index("= Опубликованный текст") < report.index('image("network.svg"') < report.index("== Суждения отношения")
    assert report.count("Я тебя съем") == 2
    assert report.count("Я тебе песенку спою") == 2
    assert report.count("Я у дедушки ушел") == 2
    assert report.count("Я у бабушки ушел") == 2
    assert "по коробу скребен" in report
    assert "По сусеку метен" in report
    assert "На сметане мешон" in report
    assert "Да в масле пряжон" in report
    assert "На окошке стужон" in report
    for s, r, t, *_ in EDGES:
        assert f"{s} {r} {t}:" in report, f"Нет суждения {s} {r} {t}"
    assert "«Колобок»" in report and "А. Н. Афанасьева" in report
    assert "@afanasyev-colobok" in report


def render_svg():
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 1250">',
        '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M 0 1 L 11 6 L 0 11 Z" fill="#345c7e"/></marker></defs>',
        '<rect width="1400" height="1250" fill="white"/>',
        '<style>text{font-family:"Times New Roman",serif}.node{fill:#edf4f8;stroke:#345c7e;stroke-width:2.4}.center{fill:#dcebf5}.edge{fill:none;stroke:#345c7e;stroke-width:2.7;marker-end:url(#arrow)}.id{font-size:28px;font-weight:bold;fill:#193b56}.name{font-size:28px;fill:#183850}.label{font-size:24px;fill:#193b56}</style>',
    ]
    for source, relation, target, path, lx, ly in EDGES:
        lines.append(f'<path class="edge" d="{path}"/>')
    for source, relation, target, path, lx, ly in EDGES:
        label = f"{relation} {RELATIONS[relation]}"
        width = max(135, len(label) * 12.5)
        lines.append(f'<rect x="{lx-width/2:.1f}" y="{ly-21}" width="{width:.1f}" height="42" rx="7" fill="white" stroke="#c8dce8"/>')
        lines.append(f'<text class="label" x="{lx}" y="{ly+8}" text-anchor="middle">{escape(label)}</text>')
    for node_id, (name, x, y) in NODES.items():
        width = 200 if node_id == "S1" else 190
        lines.append(f'<rect class="node{" center" if node_id == "S1" else ""}" x="{x-width/2}" y="{y-46}" width="{width}" height="92" rx="14"/>')
        lines.append(f'<text class="id" x="{x}" y="{y-7}" text-anchor="middle">{node_id}</text>')
        lines.append(f'<text class="name" x="{x}" y="{y+28}" text-anchor="middle">{escape(name)}</text>')
    lines.append('</svg>')
    (ROOT / "network.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    check()
    render_svg()
    print(f"Проверено: {len(NODES)} узлов, {len(EDGES)} связей, "
          f"{sum(n >= 2 for n in Counter(r for _, r, _, *_ in EDGES).values())} повторяющихся отношения.")
