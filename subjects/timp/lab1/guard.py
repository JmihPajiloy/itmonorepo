#!/usr/bin/env python3
"""Small macOS file-name guard for a teaching demonstration."""

import argparse
import getpass
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
TABLE = ROOT / "template.tbl"
ITERATIONS = 200_000


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2-sha256:{ITERATIONS}:{salt.hex()}:{digest.hex()}"


def verify(password, encoded):
    try:
        algorithm, count, salt, expected = encoded.split(":")
        if algorithm != "pbkdf2-sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(count))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def flag(path, enabled):
    subprocess.run(["chflags", "uchg" if enabled else "nouchg", str(path)], check=True)


def names():
    lines = TABLE.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("template.tbl пуст")
    result = []
    for name in lines[1:]:
        if not name or name in {".", ".."} or Path(name).name != name or name == TABLE.name:
            raise ValueError(f"Недопустимое имя: {name!r}")
        if name in result:
            raise ValueError(f"Повтор имени: {name}")
        result.append(name)
    return lines[0], result


def secret(args):
    return args.password if args.password is not None else getpass.getpass("Пароль: ")


def init(args):
    if TABLE.exists():
        raise ValueError("template.tbl уже существует")
    if not args.names:
        raise ValueError("Укажите хотя бы одно имя")
    for name in args.names:
        if Path(name).name != name or name in {".", "..", TABLE.name}:
            raise ValueError(f"Недопустимое имя: {name!r}")
    password = secret(args)
    if not password:
        raise ValueError("Пустой пароль не допускается")
    fd = os.open(TABLE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(password_hash(password) + "\n" + "\n".join(args.names) + "\n")
    print("Список создан. Защита выключена.")


def change(args, enabled):
    encoded, protected = names()
    if not verify(secret(args), encoded):
        raise ValueError("Неверный пароль")
    if enabled:
        # An existing regular file keeps its data; an absent name gets a placeholder.
        for name in protected:
            target = ROOT / name
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError(f"Можно защищать только обычный файл: {name}")
        for name in protected:
            target = ROOT / name
            if not target.exists():
                target.touch(mode=0o600)
            flag(target, True)
        flag(TABLE, True)
        print("Защита включена:", ", ".join(protected))
    else:
        flag(TABLE, False)
        for name in protected:
            target = ROOT / name
            if target.exists():
                flag(target, False)
        print("Защита выключена. Файлы и заглушки сохранены.")


def status(_args):
    _, protected = names()
    print("Имена:", ", ".join(protected))
    subprocess.run(["ls", "-lO", str(TABLE), *[str(ROOT / name) for name in protected]], check=False)


def main():
    if sys.platform != "darwin":
        raise ValueError("Эта реализация использует macOS chflags")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("init", help="создать template.tbl")
    create.add_argument("names", nargs="+", help="точные имена в каталоге программы")
    for command in ("init", "on", "off"):
        action = create if command == "init" else sub.add_parser(command)
        action.add_argument("--password", help="для автоматической проверки; в обычной работе не указывать")
    sub.add_parser("status")
    args = parser.parse_args()
    try:
        if args.command == "init":
            init(args)
        elif args.command == "status":
            status(args)
        else:
            change(args, args.command == "on")
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Ошибка: {exc}\n")


if __name__ == "__main__":
    main()
