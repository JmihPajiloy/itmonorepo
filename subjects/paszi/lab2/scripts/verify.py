"""Проверка целостности исходных PDF и иллюстраций; не тест СЗИ Windows."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise SystemExit(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest = json.loads((ROOT / 'screenshots/sources.json').read_text())
    for entry in manifest['sources']:
        path = ROOT / entry['file']
        require(path.is_file(), f'Нет источника: {path}')
        require(digest(path) == entry['sha256'], f'Исходный PDF изменился: {path.name}')
    images = {x['file']: x for x in manifest['images']}
    for name, entry in images.items():
        path = ROOT / 'screenshots' / name
        require(path.is_file(), f'Нет иллюстрации: {name}')
        require(digest(path) == entry['sha256'], f'Изображение изменилось: {name}')
    report = (ROOT / 'report.typ').read_text()
    used = re.findall(r'#shot\("([^"]+)"', report)
    for name in used:
        require(name in images, f'Нет происхождения иллюстрации: {name}')
    labels = re.findall(r'<((?:fig|tab):[^>]+)>', report)
    require(len(labels) == len(set(labels)), 'Повторяющиеся метки иллюстраций или таблиц')
    for label in labels:
        require('@' + label in report, f'Нет ссылки на {label}')
    for label in re.findall(r'@((?:fig|tab):[\w-]+)', report):
        require(label in labels, f'Не определена метка {label}')
    bibliography = (ROOT / 'references.bib').read_text()
    for key in re.findall(r'@\w+\{([^,]+),', bibliography):
        require('@' + key in report, f'Нет ссылки на источник {key}')
    require('= Dallas Lock' in report and '= Secret Net' in report, 'Отсутствует часть работы')
    print(f'Проверено: {len(manifest["sources"])} исходных PDF, {len(images)} изображений, '
          f'{len(used)} иллюстрации отчёта, ссылки и обе части работы.')
    print('Проверки Dallas Lock и Secret Net на Windows этой командой не выполняются.')

if __name__ == '__main__':
    main()
