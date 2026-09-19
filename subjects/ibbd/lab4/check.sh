#!/bin/sh
# Пересобирает БД ЛР2–ЛР3, добавляет администратора и
# регистрацию ЛР4, проверяет веб-приложение и сохраняет
# выводы в verification/.
set -eu

LAB_DIR=$(cd "$(dirname "$0")" && pwd)
PG="$LAB_DIR/../tools/pg.sh"
OUT="${IBBD_OUT:-$LAB_DIR/verification}"
PY="$LAB_DIR/.venv/bin/python"
ADMIN_PASSWORD="${IBBD_ADMIN_PASSWORD:-admin-demo-pass}"

[ -x "$PY" ] || { echo "нет .venv: make venv" >&2; exit 1; }

# БД ЛР3 с нуля; её выводы не нужны.
LAB3_OUT=$(mktemp -d)
IBBD_OUT="$LAB3_OUT" "$LAB_DIR/../lab3/check.sh" >/dev/null
rm -rf "$LAB3_OUT"

# Роли ЛР4 (в том числе зарегистрированные) общие для
# кластера: удалить оставшиеся от прошлого запуска.
"$PG" psql -d postgres -q -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT rolname FROM pg_roles
             WHERE shobj_description(oid, 'pg_authid')
                   LIKE 'ibbd-lab4:%'
    LOOP
        EXECUTE format('DROP ROLE %I', r.rolname);
    END LOOP;
END $$;
DROP ROLE IF EXISTS admin_role;
SQL

"$PG" psql -d workshop -q -v ON_ERROR_STOP=1 \
  -v admin_password="$ADMIN_PASSWORD" \
  -f "$LAB_DIR/sql/01_admin.sql" >/dev/null

# В журнале остаются только действия веб-сеансов.
"$PG" psql -d workshop -q -c \
  "TRUNCATE change_log RESTART IDENTITY" >/dev/null

mkdir -p "$OUT"
cd "$LAB_DIR"
"$PY" check.py "$OUT"
