#!/bin/sh
# Строит БД ЛР2, добавляет журнал, шифрование и роли ЛР3,
# выполняет демонстрации и сохраняет выводы в verification/.
set -eu

LAB_DIR=$(cd "$(dirname "$0")" && pwd)
PG="$LAB_DIR/../tools/pg.sh"
DB=workshop
OUT="${IBBD_OUT:-$LAB_DIR/verification}"
PGPORT="${IBBD_PGPORT:-55432}"

# Демонстрационные пароли; для реального стенда задать свои.
MASTER_PASSWORD="${IBBD_MASTER_PASSWORD:-!stroNgpsw31234}"
RECEPTION_PASSWORD="${IBBD_RECEPTION_PASSWORD:-reception-demo-pass}"
RESTORER_PASSWORD="${IBBD_RESTORER_PASSWORD:-restorer-demo-pass}"

"$PG" start
"$PG" psql -d postgres -q -v ON_ERROR_STOP=1 2>/dev/null <<'SQL'
DROP DATABASE IF EXISTS workshop WITH (FORCE);
DROP ROLE IF EXISTS reception_orlova, restorer_smirnov,
    restorer_volkova, reception_role, restorer_role;
SQL
# Выводы ЛР2 здесь не нужны: сохраняются во временный каталог.
LAB2_OUT=$(mktemp -d)
IBBD_OUT="$LAB2_OUT" "$LAB_DIR/../lab2/check.sh" >/dev/null
rm -rf "$LAB2_OUT"

su() {
  "$PG" psql -d "$DB" -v ON_ERROR_STOP=1 -P pager=off "$@"
}
as_user() {
  user=$1 pass=$2
  shift 2
  PGPASSWORD="$pass" psql -X -h 127.0.0.1 -p "$PGPORT" -U "$user" \
    -d "$DB" -P pager=off "$@"
}

su -q -f "$LAB_DIR/sql/01_audit.sql" >/dev/null
su -q -v master_password="$MASTER_PASSWORD" \
  -f "$LAB_DIR/sql/02_secrets.sql" >/dev/null
su -q -v reception_password="$RECEPTION_PASSWORD" \
  -v restorer_password="$RESTORER_PASSWORD" \
  -f "$LAB_DIR/sql/03_roles.sql" >/dev/null

mkdir -p "$OUT"

# Сообщения psql без длинного пути к файлу сценария.
strip() {
  sed -e 's/^psql:.*\.sql:[0-9]*: //' | fold -s -w 62
}

su >"$OUT/triggers.txt" <<'SQL'
SELECT tgname AS trigger,
       substring(pg_get_triggerdef(oid)
                 FROM 'AFTER ([A-Z ]+) ON') AS after_events
FROM pg_trigger WHERE NOT tgisinternal
ORDER BY tgrelid::regclass::text;
SQL

su >"$OUT/roles.txt" <<'SQL'
SELECT r.rolname, r.rolcanlogin AS login, r.rolsuper AS super,
       coalesce(string_agg(g.rolname, ', '), '') AS member_of
FROM pg_roles r
LEFT JOIN pg_auth_members m ON m.member = r.oid
LEFT JOIN pg_roles g ON g.oid = m.roleid
WHERE r.rolname ~ '^(reception|restorer|postgres)'
GROUP BY r.rolname, r.rolcanlogin, r.rolsuper
ORDER BY r.rolname;
SQL

# Журнал до демонстраций содержит только привязку учётных записей.
su -q -c "TRUNCATE change_log RESTART IDENTITY"

for u in reception_orlova restorer_smirnov; do
  case $u in
    reception_*) p=$RECEPTION_PASSWORD ;;
    *) p=$RESTORER_PASSWORD ;;
  esac
  as_user "$u" "$p" -v ON_ERROR_STOP=1 \
    -f "$LAB_DIR/demo/access_matrix.sql" >"$OUT/access-$u.txt"
done

as_user reception_orlova "$RECEPTION_PASSWORD" -e \
  -f "$LAB_DIR/demo/reception.sql" 2>&1 | strip >"$OUT/reception.txt"
as_user restorer_smirnov "$RESTORER_PASSWORD" -e \
  -f "$LAB_DIR/demo/restorer.sql" 2>&1 | strip >"$OUT/restorer.txt"

# Прямой вход без пароля и с чужим паролем отклоняется.
{
  PGPASSWORD=wrong psql -X -h 127.0.0.1 -p "$PGPORT" \
    -U restorer_smirnov -d "$DB" -c 'SELECT 1' 2>&1 || true
} | sed 's/^psql: //' | fold -s -w 60 >"$OUT/login-denied.txt"

su -e -f "$LAB_DIR/demo/admin.sql" >"$OUT/log.txt"
su -f "$LAB_DIR/demo/log_diff.sql" >"$OUT/log-diff.txt"

"$PG" psql -d "$DB" -P pager=off \
  -v master_password="$MASTER_PASSWORD" \
  -v wrong_password="not-the-password" \
  -f "$LAB_DIR/demo/secrets.sql" 2>&1 | strip >"$OUT/secrets.txt"

# Пароль и ключ не должны попасть в БД в открытом виде.
su -t -A >"$OUT/key-not-stored.txt" <<SQL
SELECT 'строк с ключом или паролем в БД: ' || count(*)
FROM (
  SELECT prosrc AS t FROM pg_proc
  UNION ALL SELECT secret_name::text FROM access_secret
  UNION ALL SELECT secret_value::text FROM access_secret
  UNION ALL SELECT coalesce(old_row::text, '')
                   || coalesce(new_row::text, '') FROM change_log
) s
WHERE t LIKE '%' || '$MASTER_PASSWORD' || '%'
   OR t LIKE '%' || encode(digest('$MASTER_PASSWORD', 'sha256'),
                           'hex') || '%';
SQL

echo "ok: $OUT"
