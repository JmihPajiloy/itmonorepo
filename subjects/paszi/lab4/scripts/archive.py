"""Архив для сдачи без окружений, секретов и чужих лабораторных."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
repo = root.parents[2]
output = root / "paszi-lab4-variant2.zip"
excluded = {".venv", "node_modules", "dist", "__pycache__", ".pytest_cache"}
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root)
        if (not file.is_file() or excluded.intersection(relative.parts)
                or file.name in {".env", ".DS_Store"} or file == output
                or file.name.startswith("page-") or file.suffix == ".log"):
            continue
        archive.write(file, Path("paszi-lab4") / "subjects/paszi/lab4" / relative)
    archive.write(repo / "templates/title-page.typ", "paszi-lab4/templates/title-page.typ")
print(output)
