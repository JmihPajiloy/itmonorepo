"""Извлечение исходных изображений из предоставленного примера без ретуши."""
from pathlib import Path
import hashlib
import json
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [('report.example.pdf', 'example'), ('task.pdf', 'task')]

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def main():
    output = ROOT / 'screenshots'
    output.mkdir(exist_ok=True)
    items = []
    sources = []
    for source, prefix in SOURCES:
        document = pymupdf.open(ROOT / source)
        sources.append(dict(file=source, sha256=sha256((ROOT / source).read_bytes())))
        for page_number, page in enumerate(document, 1):
            for index, info in enumerate(page.get_image_info(xrefs=True), 1):
                if min(info['width'], info['height']) < 100:
                    continue
                extracted = document.extract_image(info['xref'])
                name = f'{prefix}-p{page_number:02d}-{index:02d}.{extracted["ext"]}'
                (output / name).write_bytes(extracted['image'])
                items.append(dict(file=name, source=source, page=page_number, image=index,
                                  width=extracted['width'], height=extracted['height'],
                                  sha256=sha256(extracted['image'])))
    manifest = dict(sources=sources,
                    example_authors=['Матвеев Илья Александрович', 'Косинский Эдуард Олегович'],
                    example_year=2023, method='Встроенные изображения PDF, без ретуши и изменения содержимого',
                    images=items)
    (output / 'sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(f'Извлечено {len(items)} изображений из {len(sources)} PDF')

if __name__ == '__main__':
    main()
