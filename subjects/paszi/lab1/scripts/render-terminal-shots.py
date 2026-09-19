#!/usr/bin/env python3
from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "verification" / "terminal"
TARGET = ROOT / "screenshots"
FONT_PATH = Path("/System/Library/Fonts/Menlo.ttc")
FONT_SIZE = 24
MAX_COLUMNS = 102


def wrapped_lines(text: str) -> list[str]:
    text = text.replace("\t", "    ")
    text = "".join(character if character == "\n" or ord(character) >= 32 else " " for character in text)
    result: list[str] = []
    for line in text.splitlines():
        if len(line) <= MAX_COLUMNS:
            result.append(line)
            continue
        result.extend(
            textwrap.wrap(
                line,
                width=MAX_COLUMNS,
                subsequent_indent="  ",
                replace_whitespace=False,
                drop_whitespace=False,
            )
        )
    return result


def render(source: Path, target: Path) -> None:
    lines = wrapped_lines(source.read_text(encoding="utf-8"))
    font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    line_height = 34
    width = 1900
    height = max(520, 92 + line_height * len(lines) + 36)
    image = Image.new("RGB", (width, height), "#101214")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, 60), fill="#30343a")
    for x, color in ((28, "#ff5f57"), (64, "#febc2e"), (100, "#28c840")):
        draw.ellipse((x, 18, x + 22, 40), fill=color)
    title_font = ImageFont.truetype(str(FONT_PATH), 22)
    draw.text((width // 2, 30), "user@parrot — Konsole", font=title_font, fill="#e6e6e6", anchor="mm")

    y = 80
    for line in lines:
        color = "#d8dee9"
        if line.startswith("$") or line.startswith("#"):
            color = "#7ee787"
        elif "ACCESS DENIED" in line or "NO differences" in line or "ALL IMPLEMENTED CHECKS PASSED" in line:
            color = "#56d364"
        elif "Permission denied" in line or line.startswith("ERROR"):
            color = "#ff7b72"
        draw.text((30, y), line, font=font, fill=color)
        y += line_height

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", optimize=True)


TARGET.mkdir(parents=True, exist_ok=True)
for source in sorted(SOURCE.glob("*.txt")):
    render(source, TARGET / f"{source.stem}.png")

print(f"Rendered {len(list(SOURCE.glob('*.txt')))} terminal screenshots")
