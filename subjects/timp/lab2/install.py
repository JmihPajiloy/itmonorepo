#!/usr/bin/env python3
"""Install the trial app and keep the previous trial counters."""

import fcntl
import os
from pathlib import Path
import shutil
import time

from trial import APP_NAME, MAX_SECONDS, MAX_STARTS, load_registry, paths, save_registry, show_limits


def main():
    executable, registry, data = paths()
    data.mkdir(parents=True, exist_ok=True)
    with (data / "trial.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if registry.exists():
            state = load_registry(registry)
            print("Обнаружена предыдущая установка; прежние лимиты сохранены.")
        else:
            now = time.time()
            state = {"first_installed": now, "last_seen": now, "starts": 0}
            print("Первая установка.")
        executable.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).with_name("trial.py"), executable)
        os.chmod(executable, 0o755)
        state["installed"] = True
        state["executable"] = str(executable)
        save_registry(registry, state)
        print(f"Программа: {executable}")
        print(f"Регистрация: {registry}")
        print(f"Данные: {data}")
        show_limits(state, time.time())


if __name__ == "__main__":
    main()
