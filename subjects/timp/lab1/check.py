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

    call("init", "protected.txt", "--password", "test-secret")
    target = root / "protected.txt"
    target.write_text("исходный текст", encoding="utf-8")
    assert "Неверный пароль" in subprocess.run(
        [sys.executable, str(guard), "on", "--password", "wrong"], capture_output=True, text=True
    ).stderr
    call("on", "--password", "test-secret")
    assert (root / "template.tbl").stat().st_mode & 0o777 == 0o600
    assert subprocess.run(["cp", str(guard), str(target)], capture_output=True).returncode != 0
    try:
        target.open("x")
    except FileExistsError:
        pass
    else:
        raise AssertionError("Защищённое имя осталось свободным")
    for action in (
        lambda: target.write_text("новый текст", encoding="utf-8"),
        lambda: target.rename(root / "renamed.txt"),
        lambda: target.unlink(),
        lambda: (root / "template.tbl").unlink(),
    ):
        try:
            action()
        except PermissionError:
            pass
        else:
            raise AssertionError("Операция над защищённым файлом не была заблокирована")
    call("off", "--password", "test-secret")
    target.rename(root / "renamed.txt")
    assert (root / "renamed.txt").read_text(encoding="utf-8") == "исходный текст"
print("Проверены пароль, изменение, удаление, переименование и выключение защиты.")
