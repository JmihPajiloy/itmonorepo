#!/usr/bin/env python3
"""Remove the executable; retain trial registration for reinstalls."""

import fcntl
from trial import load_registry, paths, save_registry


def main():
    executable, registry, data = paths()
    data.mkdir(parents=True, exist_ok=True)
    with (data / "trial.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not registry.exists():
            print("Установка не найдена.")
            return
        state = load_registry(registry)
        if executable.exists():
            executable.unlink()
        state["installed"] = False
        save_registry(registry, state)
        print("Программа удалена. Регистрация и данные оставлены для контроля лимитов.")
        print(f"Регистрация: {registry}")


if __name__ == "__main__":
    main()
