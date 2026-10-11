#!/usr/bin/env python3
"""Integration check in a disposable installation directory."""

import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent


def call(script, env, *arguments, expected=0):
    result = subprocess.run([sys.executable, str(script), *arguments], env=env, text=True, capture_output=True)
    assert result.returncode == expected, (script, result.returncode, result.stdout, result.stderr)
    return result.stdout


with tempfile.TemporaryDirectory(prefix="timp-trial-") as temp:
    env = {**os.environ, "TIMP_TRIAL_HOME": temp}
    installed = Path(temp) / "bin" / "itmo-timp-trial"
    registry = Path(temp) / "Library" / "Preferences" / "ru.itmo.timp.trial.plist"
    names = Path(temp) / "Library" / "Application Support" / "itmo-timp-trial" / "names.txt"
    assert "Первая установка" in call(ROOT / "install.py", env)
    for index in range(5):
        output = call(installed, env, "--name", "Иван Шибаев")
        assert ("ФИО записано" if index == 0 else "ФИО уже есть") in output
    assert names.read_text(encoding="utf-8").splitlines() == ["Иван Шибаев"]
    assert "Пробный период окончен" in call(installed, env, "--name", "Анна Иванова", expected=2)
    call(ROOT / "uninstall.py", env)
    assert "предыдущая установка" in call(ROOT / "install.py", env)
    assert "Пробный период окончен" in call(installed, env, "--name", "Анна Иванова", expected=2)
    with registry.open("rb") as file:
        state = plistlib.load(file)
    assert state["starts"] == 5
    # Simulate an expired 90-second period for the time-limit branch.
    state["starts"] = 0
    state["first_installed"] -= 91
    with registry.open("wb") as file:
        plistlib.dump(state, file)
    assert "Пробный период окончен" in call(installed, env, "--name", "Анна Иванова", expected=2)
print("Проверены повторы ФИО, 5 запусков, переустановка и ветка истечения времени через изменение метки в тестовом plist.")
