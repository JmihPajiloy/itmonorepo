"""Семантическая проверка преобразований и выводов задач 20–21.

Для n терминов достаточно перебрать заполненность всех 2**n областей
диаграммы: универсальные категорические суждения зависят лишь от того,
пуста ли область. Число объектов в непустой области не влияет на истинность.
"""

from itertools import product
from pathlib import Path
import json

from diagrams.generate import generate


def all_models(term_count):
    atoms = tuple(product((False, True), repeat=term_count))
    for mask in range(1, 1 << len(atoms)):
        yield tuple(atom for i, atom in enumerate(atoms) if mask & (1 << i))


def a(model, subject, predicate):
    return all(not atom[subject] or atom[predicate] for atom in model)


def e(model, subject, predicate):
    return all(not (atom[subject] and atom[predicate]) for atom in model)


def main():
    # Задача 20: S=0, M=1, P=2, N («несчастные»)=3.
    # Под допущением N = дополнение M проверяем эквивалентность
    # исходных посылок нормализованным, затем само заключение.
    count20 = count_without_assumption = 0
    counterexample = None
    for model in all_models(4):
        original = e(model, 3, 0) and e(model, 1, 2)
        complementary = all(atom[3] == (not atom[1]) for atom in model)
        if complementary:
            normalized = e(model, 1, 2) and a(model, 0, 1)
            assert original == normalized, ("20: преобразование", model)
            if original:
                count20 += 1
                assert e(model, 0, 2), ("20: заключение", model)
        if original and not e(model, 0, 2):
            count_without_assumption += 1
            if counterexample is None:
                counterexample = model
    assert count20 > 0 and counterexample is not None

    # Задача 21: S=0, M=1, P=2.
    count21 = 0
    for model in all_models(3):
        original_second = all(atom[1] or not atom[0] for atom in model)
        assert original_second == a(model, 0, 1), ("21: преобразование", model)
        if a(model, 1, 2) and original_second:
            count21 += 1
            assert a(model, 0, 2), ("21: заключение", model)
    assert count21 > 0

    result = {
        "method": "Перебор заполненности областей для непустого универсума",
        "task20": {
            "checked_models": 65535,
            "premise_models_with_complement_assumption": count20,
            "equivalent_normalization": True,
            "conclusion": "S e P",
            "valid_under_assumption": True,
            "counterexample_without_assumption": {
                "term_order": ["хохочущие", "счастливые", "стонущие", "несчастные"],
                "occupied_regions": counterexample,
            },
            "models_refuting_conclusion_without_assumption": count_without_assumption,
        },
        "task21": {
            "checked_models": 255,
            "premise_models": count21,
            "equivalent_normalization": True,
            "conclusion": "S a P",
            "valid": True,
        },
        "task22": "Разобрана в отчёте: нет общего среднего термина; автоматическая проверка естественного языка не выполняется",
    }
    root = Path(__file__).resolve().parent
    output = root / "verification" / "logic.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generate()
    print(f"20: Celarent подтверждён в {count20} моделях при допущении о дополнении.")
    print("20: без допущения найден контрпример.")
    print(f"21: Barbara подтверждён во всех {count21} моделях посылок.")
    print("Круги Эйлера пересозданы; результаты: verification/logic.json")


if __name__ == "__main__":
    main()
