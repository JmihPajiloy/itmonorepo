#!/usr/bin/env python3
"""Exercise the macOS immutable-file guard in a temporary directory."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


if sys.platform != "darwin":
    raise SystemExit("Проверка файловой части требует macOS")

with tempfile.TemporaryDirectory(prefix="timp-guard-") as directory:
    root = Path(directory)
    guard = root / "guard.py"
    shutil.copyfile(Path(__file__).with_name("guard.py"), guard)

    def call(*args, expected=0):
        result = subprocess.run([sys.executable, str(guard), *args], capture_output=True, text=True)
        assert result.returncode == expected, (args, result.stdout, result.stderr)
        return result.stdout

    call("init", "protected.txt", "archive.txt", "--password", "test-secret")
    target = root / "protected.txt"
    table = root / "template.tbl"
    target.write_text("исходный текст", encoding="utf-8")
    target.write_text("до защиты", encoding="utf-8")
    assert "Неверный пароль" in subprocess.run(
        [sys.executable, str(guard), "on", "--password", "wrong"], capture_output=True, text=True
    ).stderr
    assert "Неверный пароль" in subprocess.run(
        [sys.executable, str(guard), "status", "--password", "wrong"], capture_output=True, text=True
    ).stderr
    assert table.stat().st_mode & 0o777 == 0o600
    assert "protected.txt" in call("status", "--password", "test-secret")

    def denied(action):
        try:
            action()
        except PermissionError:
            return
        raise AssertionError("Операция над защищённым файлом не была заблокирована")

    call("on", "--password", "test-secret")
    try:
        assert not (root / "archive.txt").stat().st_size
        assert target.read_text(encoding="utf-8") == "до защиты"
        assert subprocess.run(["cp", str(guard), str(target)], capture_output=True).returncode != 0
        denied(lambda: target.write_text("новый текст", encoding="utf-8"))
        denied(lambda: target.rename(root / "renamed.txt"))
        denied(target.unlink)
        denied(lambda: table.write_text("подмена", encoding="utf-8"))
        denied(table.unlink)
        try:
            (root / "archive.txt").open("x")
        except FileExistsError:
            pass
        else:
            raise AssertionError("Защищённое имя осталось свободным")
        assert "Неверный пароль" in subprocess.run(
            [sys.executable, str(guard), "off", "--password", "wrong"], capture_output=True, text=True
        ).stderr
        assert target.read_text(encoding="utf-8") == "до защиты"
    finally:
        call("off", "--password", "test-secret")

    target.write_text("после защиты", encoding="utf-8")
    target.rename(root / "renamed.txt")
    assert (root / "renamed.txt").read_text(encoding="utf-8") == "после защиты"
    table.unlink()
print("Проверены операции до, во время и после защиты, пароль и сохранность таблицы.")
