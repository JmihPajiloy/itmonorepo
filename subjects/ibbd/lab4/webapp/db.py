"""Каталог доступных отношений и операции с таблицами.
Имена отношений и столбцов берутся только из каталога
PostgreSQL для текущей роли и подставляются через
psycopg.sql.Identifier; значения — только параметрами."""
from dataclasses import dataclass

from psycopg import sql

ROW_LIMIT = 200

RELATIONS_SQL = """
SELECT c.relname, c.relkind = 'v',
       has_any_column_privilege(c.oid, 'INSERT'),
       has_any_column_privilege(c.oid, 'UPDATE'),
       has_table_privilege(c.oid, 'DELETE'),
       has_table_privilege(c.oid, 'SELECT')
FROM pg_class c
WHERE c.relnamespace = 'public'::regnamespace
  AND c.relkind IN ('r', 'v')
  AND has_any_column_privilege(c.oid, 'SELECT')
ORDER BY c.relkind, c.relname
"""

COLUMNS_SQL = """
SELECT a.attname, format_type(a.atttypid, a.atttypmod),
       has_column_privilege(c.oid, a.attnum, 'SELECT'),
       has_column_privilege(c.oid, a.attnum, 'INSERT'),
       has_column_privilege(c.oid, a.attnum, 'UPDATE'),
       a.attidentity <> '' OR a.atthasdef,
       coalesce(a.attnum = ANY (i.indkey), false)
FROM pg_class c
JOIN pg_attribute a ON a.attrelid = c.oid
LEFT JOIN pg_index i
       ON i.indrelid = c.oid AND i.indisprimary
WHERE c.relnamespace = 'public'::regnamespace
  AND c.relname = %s
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum
"""


@dataclass
class Relation:
    name: str
    is_view: bool
    can_insert: bool
    can_update: bool
    can_delete: bool
    full_select: bool


@dataclass
class Column:
    name: str
    type: str
    can_select: bool
    can_insert: bool
    can_update: bool
    has_default: bool
    is_pk: bool


def relations(conn):
    """Отношения, на которые у роли есть право SELECT
    хотя бы на один столбец."""
    rows = conn.execute(RELATIONS_SQL).fetchall()
    return [Relation(*r) for r in rows]


def find_relation(conn, name):
    for rel in relations(conn):
        if rel.name == name:
            return rel
    return None


def columns(conn, rel):
    rows = conn.execute(COLUMNS_SQL, (rel,)).fetchall()
    return [Column(*r) for r in rows]


def where_filter(col, op, value):
    """Условие фильтра: столбец из белого списка,
    значение — параметр."""
    ident = sql.Identifier(col)
    if op == "eq":
        return (sql.SQL("{}::text = %(fval)s").format(ident),
                {"fval": value})
    pattern = "%" + value.replace("\\", "\\\\") \
        .replace("%", "\\%").replace("_", "\\_") + "%"
    return (sql.SQL("{}::text ILIKE %(fval)s")
            .format(ident), {"fval": pattern})


def order_by(col, desc):
    direction = sql.SQL("DESC" if desc else "ASC")
    return sql.SQL(" ORDER BY {} {} NULLS LAST").format(
        sql.Identifier(col), direction)


def select_rows(conn, rel, cols, flt=None, sort=None):
    """flt = (столбец, операция, значение),
    sort = (столбец, по убыванию)."""
    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(map(sql.Identifier, cols)),
        sql.Identifier(rel))
    params = {"limit": ROW_LIMIT}
    if flt:
        cond, p = where_filter(*flt)
        query += sql.SQL(" WHERE ") + cond
        params.update(p)
    if sort:
        query += order_by(*sort)
    query += sql.SQL(" LIMIT %(limit)s")
    return conn.execute(query, params).fetchall()


def key_condition(keys):
    return sql.SQL(" AND ").join(
        sql.SQL("{} = %s").format(sql.Identifier(k))
        for k in keys)


def insert_row(conn, rel, values):
    """values: {столбец: строка}; пустые поля не
    передаются, и СУБД подставляет значения по
    умолчанию."""
    names = list(values)
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(rel),
        sql.SQL(", ").join(map(sql.Identifier, names)),
        sql.SQL(", ").join(sql.Placeholder() * len(names)))
    return conn.execute(query, list(values.values())).rowcount


def delete_row(conn, rel, key):
    query = sql.SQL("DELETE FROM {} WHERE ").format(
        sql.Identifier(rel)) + key_condition(key)
    return conn.execute(query, list(key.values())).rowcount


def update_value(conn, rel, key, col, value):
    query = sql.SQL("UPDATE {} SET {} = %s WHERE ").format(
        sql.Identifier(rel), sql.Identifier(col)) \
        + key_condition(key)
    params = [value] + list(key.values())
    return conn.execute(query, params).rowcount
