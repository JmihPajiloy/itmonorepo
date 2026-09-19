"""Сводные запросы с GROUP BY для каждой группы
пользователей. Параметры отчёта принимают значения
только из заданных списков."""
from dataclasses import dataclass
from pathlib import Path

from psycopg import sql

from .db import order_by, where_filter


@dataclass
class Param:
    name: str
    label: str
    choices: tuple  # (значение, подпись); "" — все


@dataclass
class Report:
    key: str
    kind: str
    title: str
    about: str
    query: str
    params: tuple = ()


SQL_DIR = Path(__file__).parent / "sql"


def load(key):
    return (SQL_DIR / f"{key}.sql").read_text("utf-8")


ORDER_STATUS = Param("ostatus", "Статус заказа", (
    ("", "любой"), ("accepted", "accepted"),
    ("in_progress", "in_progress"), ("ready", "ready"),
    ("closed", "closed"), ("cancelled", "cancelled")))

REPORTS = (
    Report("payments", "reception",
           "Оплаты по типам инструментов",
           "Заказчики, заказы и поступившие оплаты по "
           "типам инструментов (instrument_type, "
           "instrument, restoration_order, payment).",
           load("payments"),
           (ORDER_STATUS,
            Param("method", "Способ оплаты", (
                ("", "любой"), ("cash", "cash"),
                ("card", "card"),
                ("transfer", "transfer"))))),
    Report("workload", "restorer",
           "Работы по исполнителям и услугам",
           "Число работ по статусам и ближайший срок "
           "(order_work, employee, service, "
           "restoration_order).",
           load("workload"),
           (Param("mine", "Исполнитель", (
               ("", "все"), ("1", "только мои"))),
            ORDER_STATUS)),
    Report("employees", "admin",
           "Выработка сотрудников",
           "Заказы, заказчики, работы и согласованная "
           "стоимость по сотрудникам (employee, "
           "order_work, restoration_order, instrument).",
           load("employees"), (ORDER_STATUS,)),
    Report("audit", "admin",
           "Журнал изменений по ролям",
           "Операции из change_log по группам, ролям "
           "входа и таблицам (change_log, pg_roles, "
           "pg_auth_members).",
           load("audit"),
           (Param("op", "Операция", (
               ("", "все"), ("I", "INSERT"),
               ("U", "UPDATE"), ("D", "DELETE"))),)),
)


def for_kind(kind):
    return [r for r in REPORTS if r.kind == kind]


def find(kind, key):
    for r in for_kind(kind):
        if r.key == key:
            return r
    return None


def clean_params(report, args):
    """Значение параметра вне списка заменяется на ""."""
    values = {}
    for p in report.params:
        v = args.get(p.name, "")
        allowed = {c[0] for c in p.choices}
        values[p.name] = v if v in allowed else ""
    return values


def columns(conn, report, params):
    """Имена столбцов результата — белый список для
    сортировки и фильтра."""
    query = sql.SQL("SELECT * FROM ({}) r LIMIT 0").format(
        sql.SQL(report.query))
    cur = conn.execute(query, params)
    return [d.name for d in cur.description]


def run(conn, report, params, flt=None, sort=None):
    query = sql.SQL("SELECT * FROM ({}) r").format(
        sql.SQL(report.query))
    params = dict(params)
    if flt:
        cond, p = where_filter(*flt)
        query += sql.SQL(" WHERE ") + cond
        params.update(p)
    if sort:
        query += order_by(*sort)
    return conn.execute(query, params).fetchall()
