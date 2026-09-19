# Лабораторная работа № 3 по ИББД

Шибаев Иван Дмитриевич, Малышев Григорий Игоревич, N3352.
Тема: «Разработка примитивной системы защиты на уровне СУБД».
База данных — `workshop` из [ЛР2](../lab2/README.md) (PostgreSQL 14).

## Результаты

- `report.pdf` / `report.typ` — отчёт, `references.bib` — источники, `task.pdf` — задание.
- `sql/01_audit.sql` — журнал `change_log`, функция `log_change()` (SECURITY DEFINER), триггеры на 9 таблиц.
- `sql/02_secrets.sql` — таблица `access_secret`, pgcrypto `pgp_sym_encrypt` AES-256,
  ключ = SHA-256 от индивидуального пароля (в БД не хранится).
- `sql/03_roles.sql` — групповые роли `reception_role`, `restorer_role`, учётные записи
  `reception_orlova`, `restorer_smirnov`, `restorer_volkova`; столбцовые привилегии и RLS.
- `demo/` — сценарии демонстраций; `verification/` — их фактические выводы.
- `check.sh` — пересобирает БД ЛР2, применяет ЛР3 и выполняет демонстрации.

## Команды

```sh
make check SUBJECT=ibbd LAB=lab3
make report SUBJECT=ibbd LAB=lab3
```

Пароли задаются переменными окружения (по умолчанию — демонстрационные значения):

| Переменная | Назначение | По умолчанию |
| --- | --- | --- |
| `IBBD_MASTER_PASSWORD` | индивидуальный пароль шифрования | `!stroNgpsw31234` |
| `IBBD_RECEPTION_PASSWORD` | пароль `reception_orlova` | `reception-demo-pass` |
| `IBBD_RESTORER_PASSWORD` | пароль `restorer_smirnov`, `restorer_volkova` | `restorer-demo-pass` |

`IBBD_OUT` перенаправляет выводы проверок (используется ЛР4 и ЛР5, чтобы не перезаписывать
`verification/`). `check.sh` удаляет БД `workshop` и роли ЛР3 в учебном кластере.

## Границы результата

- Расшифровка выполняется на сервере: в момент расшифровки ключ передаётся в тексте запроса
  и может быть перехвачен суперпользователем, включившим протоколирование операторов.
- Суперпользователь `postgres` учебного кластера входит без пароля с 127.0.0.1.
- Демонстрационные пароли по умолчанию не подходят для реального использования.
