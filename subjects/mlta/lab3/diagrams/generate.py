"""Векторные круги Эйлера для задач 20 и 21; только стандартная библиотека."""

from pathlib import Path


def circle(cx, cy, radius, label, x, y):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" '
        'fill="none" stroke="#111111" stroke-width="2"/>'
        f'<text x="{x}" y="{y}" font-style="italic">{label}</text>'
    )


def generate():
    folder = Path(__file__).resolve().parent
    diagrams = {
        "task20.svg": (
            "Круги Эйлера: S входит в M; M и P не пересекаются",
            circle(155, 132, 115, "M", 155, 58)
            + circle(155, 155, 62, "S", 155, 162)
            + circle(420, 132, 90, "P", 420, 139),
        ),
        "task21.svg": (
            "Круги Эйлера: S входит в M, M входит в P",
            circle(275, 155, 142, "P", 275, 55)
            + circle(275, 181, 100, "M", 275, 119)
            + circle(275, 207, 56, "S", 275, 214),
        ),
    }
    for name, (description, body) in diagrams.items():
        (folder / name).write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="550" height="310" viewBox="0 0 550 310">'
            f'<title>{description}</title>'
            '<g font-family="Times New Roman, serif" font-size="30" '
            f'text-anchor="middle" fill="#111111">{body}</g></svg>\n',
            encoding="utf-8",
        )


if __name__ == "__main__":
    generate()
