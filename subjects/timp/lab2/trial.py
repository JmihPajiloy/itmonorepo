#!/usr/bin/env python3
"""Trial application: five starts or 90 seconds since first installation."""

import argparse
import fcntl
import os
from pathlib import Path
import plistlib
import sys
import tempfile
import time


MAX_STARTS = 5
MAX_SECONDS = 90
APP_NAME = "itmo-timp-trial"


def paths():
    override = os.environ.get("TIMP_TRIAL_HOME")
    if override:
        base = Path(override).expanduser().resolve()
        return base / "bin" / APP_NAME, base / "Library" / "Preferences" / "ru.itmo.timp.trial.plist", base / "Library" / "Application Support" / APP_NAME
    home = Path.home()
    return home / ".local" / "bin" / APP_NAME, home / "Library" / "Preferences" / "ru.itmo.timp.trial.plist", home / "Library" / "Application Support" / APP_NAME


def load_registry(path):
    with path.open("rb") as file:
        return plistlib.load(file)


def save_registry(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".trial-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as file:
            plistlib.dump(state, file)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def limits(state, now):
    remaining_starts = max(0, MAX_STARTS - state["starts"])
    remaining_seconds = max(0, int(MAX_SECONDS - (now - state["first_installed"])))
    rollback = now + 1 < state["last_seen"]
    return remaining_starts, remaining_seconds, rollback


def show_limits(state, now):
    starts, seconds, rollback = limits(state, now)
    print(f"Осталось запусков: {starts} из {MAX_STARTS}; времени: {seconds} с из {MAX_SECONDS} с.")
    if rollback:
        print("Обнаружен перевод системных часов назад.")
    if not starts or not seconds or rollback:
        print("Пробный период окончен. Приобретите полную версию или запустите uninstall.py.")


def normalize_name(value):
    result = " ".join(value.split())
    if len(result.split()) < 2 or len(result) > 150 or "\n" in value or "\r" in value:
        raise ValueError("Введите ФИО не короче двух слов и не длиннее 150 символов")
    return result


def run(name=None):
    executable, registry, data = paths()
    if not registry.exists():
        print("Программа не установлена. Запустите install.py.", file=sys.stderr)
        return 1
    data.mkdir(parents=True, exist_ok=True)
    lock = data / "trial.lock"
    with lock.open("a+b") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        state = load_registry(registry)
        if not state.get("installed") or str(executable) != state.get("executable"):
            print("Программа удалена. Запустите install.py.", file=sys.stderr)
            return 1
        now = time.time()
        starts, seconds, rollback = limits(state, now)
        if not starts or not seconds or rollback:
            show_limits(state, now)
            return 2
        if name is None:
            name = input("Введите ФИО: ")
        try:
            name = normalize_name(name)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        state["starts"] += 1
        state["last_seen"] = now
        save_registry(registry, state)
        names_file = data / "names.txt"
        previous = set(names_file.read_text(encoding="utf-8").splitlines()) if names_file.exists() else set()
        if name in previous:
            print(f"ФИО уже есть в файле: {name}")
        else:
            with names_file.open("a", encoding="utf-8") as file:
                file.write(name + "\n")
            os.chmod(names_file, 0o600)
            print(f"ФИО записано: {name}")
        show_limits(state, now)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="ФИО для автоматической демонстрации")
    args = parser.parse_args()
    raise SystemExit(run(args.name))


if __name__ == "__main__":
    main()
