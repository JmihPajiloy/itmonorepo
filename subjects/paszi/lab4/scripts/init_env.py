"""Создать локальные секреты, не перезаписывая существующую конфигурацию."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
content = (root / ".env.example").read_text()
content = content.replace("replace-with-random-password", secrets.token_hex(24))
content = content.replace("replace-with-a-random-key-at-least-32-characters", secrets.token_hex(32))
try:
    descriptor = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print(".env уже существует; сохранён без изменений")
else:
    with os.fdopen(descriptor, "w") as output:
        output.write(content)
    print("Создан .env со случайными локальными секретами (права 0600)")
