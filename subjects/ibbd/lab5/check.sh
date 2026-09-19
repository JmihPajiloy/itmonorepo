#!/bin/sh
# ЛР5: резервное копирование по расписанию, случайные изменения,
# откат к точке восстановления (PITR) и анализ откаченных
# изменений. Все кластеры и копии создаются заново в work/,
# выводы сохраняются в verification/.
set -eu

LAB_DIR=$(cd "$(dirname "$0")" && pwd)
PG="$LAB_DIR/../tools/pg.sh"
WORK="$LAB_DIR/work"
OUT="${IBBD_OUT:-$LAB_DIR/verification}"
ARCHIVE="$WORK/wal_archive"
PRIMARY="$WORK/pgdata"
COPY="$WORK/pitr-latest"
PORT=55433
COPY_PORT=55434
DB=workshop
RP=lab5_before_changes
RECEPTION_PASSWORD="${IBBD_RECEPTION_PASSWORD:-reception-demo-pass}"

# Собственный кластер ЛР5, общий кластер 55432 не затрагивается.
IBBD_PGDATA="$PRIMARY"
IBBD_PGPORT=$PORT
export IBBD_PGDATA IBBD_PGPORT
unset WAL_ARCHIVE BACKUP_ROOT KEEP || true

stop_all() {
  for d in "$PRIMARY" "$COPY" "$WORK/pgdata.before-restore"; do
    if [ -f "$d/postmaster.pid" ]; then
      pg_ctl -D "$d" -w stop -m fast >/dev/null 2>&1 || true
    fi
  done
}
trap stop_all EXIT

# Длинный путь к работе заменяется на «…/lab5».
short() { sed "s|$LAB_DIR|…/lab5|g"; }
su() { "$PG" psql -d "$DB" -v ON_ERROR_STOP=1 -P pager=off "$@"; }
su_copy() {
  psql -X -h 127.0.0.1 -p "$COPY_PORT" -U postgres -d "$DB" \
    -v ON_ERROR_STOP=1 -P pager=off "$@"
}
# Ждёт окончания восстановления (сервер принимает запросы
# уже во время восстановления, hot_standby = on).
wait_promoted() {
  i=0
  until [ "$(psql -X -h 127.0.0.1 -p "$1" -U postgres -d postgres \
      -tAc 'SELECT pg_is_in_recovery()' 2>/dev/null)" = f ]; do
    i=$((i + 1))
    [ $i -le 120 ] || { echo "recovery timeout" >&2; exit 1; }
    sleep 0.5
  done
}
# Сравнение двух выводов sql/state.sql по таблицам.
compare() {
  awk -F'|' -v a="$3" -v b="$4" '
    function t(s) { gsub(/^ +| +$/, "", s); return s }
    FNR == 1 { f++ }
    NF == 3 && t($2) ~ /^[0-9]+$/ {
      k = t($1); r[f, k] = t($2); m[f, k] = t($3)
      if (f == 1) keys[++n] = k
    }
    END {
      printf "%-18s %8s %8s  %s\n", "table", a, b, "md5"
      for (i = 1; i <= n; i++) {
        k = keys[i]
        s = (m[1, k] == m[2, k]) ? "совпадает" : "ОТЛИЧАЕТСЯ"
        printf "%-18s %8s %8s  %s\n", k, r[1, k], r[2, k], s
      }
    }' "$1" "$2"
}
# Строки журнала сервера без даты и номера процесса.
log_lines() {
  short | sed -E \
    -e 's/^[0-9-]+ ([0-9:]+)\.[0-9]+ [A-Z+0-9]+ \[[0-9]+\] /\1 /' \
    -e 's/^([0-9:]+) @ /\1 /' -e 's/LOG:  /LOG: /' -e 's/^	/  /' \
    | fold -s -w 62
}

# 1. Чистый кластер с архивированием WAL и БД ЛР2 + ЛР3.
stop_all
rm -rf "$WORK"
mkdir -p "$WORK" "$ARCHIVE" "$OUT"
"$PG" init
sed "s|@LAB5@|$LAB_DIR|g" "$LAB_DIR/conf/lab5.conf.in" \
  >>"$PRIMARY/postgresql.conf"
"$PG" start
L3_OUT=$(mktemp -d)
IBBD_OUT="$L3_OUT" "$LAB_DIR/../lab3/check.sh" >/dev/null
rm -rf "$L3_OUT"
# Протоколирование операторов изменения включается после сборки
# ЛР3, иначе пароли ролей и ключ шифрования попали бы в журнал.
"$PG" psql -d postgres -q -v ON_ERROR_STOP=1 \
  -c "ALTER SYSTEM SET log_statement = 'mod'" \
  -c "SELECT pg_reload_conf()" >/dev/null

su -v lab="$LAB_DIR" >"$OUT/settings.txt" <<'SQL'
SELECT name, replace(setting, :'lab', '…/lab5') AS setting
FROM pg_settings
WHERE name IN ('wal_level', 'archive_mode', 'archive_command',
               'archive_timeout', 'log_statement')
ORDER BY name;
SQL

# 2. Плановое задание, запущенное вручную два раза подряд
# (имитация двух ночных запусков) с хранением одной копии.
{
  echo "== запуск 1"
  KEEP=1 "$LAB_DIR/backup.sh" 2>&1
  sleep 1
  echo "== запуск 2"
  KEEP=1 "$LAB_DIR/backup.sh" 2>&1
} | short >"$OUT/backup-run.txt"
LATEST=$(ls -1 "$WORK/backups" | sort | tail -n 1)
{
  echo "== work/backups"
  (cd "$WORK/backups" && du -sh -- */data */*.dump */globals.sql \
    | tr '\t' ' ')
  echo "== права доступа"
  (cd "$WORK/backups" && ls -ld "$LATEST" "$LATEST"/* \
    | awk '{ sub(/@$/, "", $1); print $1, $NF }')
  echo "== work/wal_archive"
  ls -1 "$ARCHIVE"
} >"$OUT/backups.txt"

# 3. Контрольная точка: состояние и точка восстановления.
su -f "$LAB_DIR/sql/state.sql" >"$OUT/state-before.txt"
LOG_MAX=$(su -tAc "SELECT max(log_id) FROM change_log")
su >"$OUT/restore-point.txt" <<SQL
SELECT '$RP' AS name,
       pg_create_restore_point('$RP') AS lsn,
       now()::timestamp(0) AS created_at;
SQL
RP_LSN=$(awk -F'|' 'NR == 3 { gsub(/ /, "", $2); print $2 }' \
  "$OUT/restore-point.txt")
RP_SEG=$(su -tAc "SELECT pg_walfile_name('$RP_LSN')")
DB_OID=$(su -tAc "SELECT oid FROM pg_database WHERE datname='$DB'")

# 4. Случайные изменения от двух ролей.
su -f "$LAB_DIR/sql/random_admin.sql" >"$OUT/changes-admin.txt"
PGPASSWORD="$RECEPTION_PASSWORD" psql -X -h 127.0.0.1 -p "$PORT" \
  -U reception_orlova -d "$DB" -v ON_ERROR_STOP=1 -P pager=off \
  -f "$LAB_DIR/sql/random_reception.sql" \
  >"$OUT/changes-reception.txt"
su -f "$LAB_DIR/sql/state.sql" >"$OUT/state-after.txt"
compare "$OUT/state-before.txt" "$OUT/state-after.txt" \
  before after >"$OUT/compare-before-after.txt"

# Сегмент с изменениями закрывается и попадает в архив.
END_LSN=$(su -tAc "SELECT pg_switch_wal()")
END_SEG=$(su -tAc "SELECT pg_walfile_name('$END_LSN')")
i=0
until [ -f "$ARCHIVE/$END_SEG" ]; do
  i=$((i + 1))
  [ $i -le 60 ] || { echo "archive timeout" >&2; exit 1; }
  sleep 0.5
done

# 5. Откат: остановка, сохранение повреждённого каталога,
# восстановление последней базовой копии до точки RP.
"$PG" stop
mv "$PRIMARY" "$WORK/pgdata.before-restore"
"$LAB_DIR/restore.sh" "$WORK/backups/$LATEST/data" "$PRIMARY" "$RP"
"$PG" start
wait_promoted "$PORT"
grep -v -e 'statement:' -e 'starting PostgreSQL' \
  -e 'listening on' "$PRIMARY/server.log" | log_lines \
  >"$OUT/recovery-log.txt"

su -f "$LAB_DIR/sql/state.sql" >"$OUT/state-restored.txt"
compare "$OUT/state-before.txt" "$OUT/state-restored.txt" \
  before restored >"$OUT/compare-before-restored.txt"
su >"$OUT/restored-check.txt" <<SQL
SELECT pg_is_in_recovery() AS in_recovery,
       (SELECT timeline_id FROM pg_control_checkpoint())
         AS timeline;
SELECT
  (SELECT count(*) FROM customer
   WHERE full_name LIKE 'Случайный%') AS rnd_customers,
  (SELECT count(*) FROM payment
   WHERE receipt_no LIKE 'RND-%') AS rnd_payments,
  (SELECT count(*) FROM change_log
   WHERE log_id > $LOG_MAX) AS new_log_rows;
SQL

# 6а. WAL архива после точки восстановления (линия времени 1).
pg_waldump -p "$ARCHIVE" -e "$END_LSN" "$RP_SEG" \
  >"$WORK/waldump.txt" 2>&1 || true
awk -v db="$DB_OID" '
  /RESTORE_POINT/ { on = 1; next }
  on && $2 == "Heap" && index($0, "rel 1663/" db "/") {
    op = $0; sub(/.*desc: /, "", op); sub(/ .*/, "", op)
    sub(/\+INIT/, "", op)
    rel = $0; sub(/.*rel 1663\/[0-9]+\//, "", rel)
    sub(/ .*/, "", rel)
    n[rel " " op]++
  }
  END { for (k in n) print k, n[k] }' "$WORK/waldump.txt" \
  >"$WORK/waldump-heap.txt"
su -q -c "CREATE TEMP TABLE w (fn oid, op text, n int)" \
  -c "COPY w FROM STDIN (DELIMITER ' ')" \
  -c "SELECT coalesce(c.relname, w.fn::text) AS relation,
             w.op, w.n AS records
      FROM w LEFT JOIN pg_class c ON c.relfilenode = w.fn
      ORDER BY 1, 2" \
  <"$WORK/waldump-heap.txt" >"$OUT/waldump-heap.txt"
{
  grep 'RESTORE_POINT' "$WORK/waldump.txt"
  awk '/RESTORE_POINT/ { on = 1 }
       on && $2 == "Heap" && ++k <= 2' "$WORK/waldump.txt"
} | sed -E 's/  +/ /g' | fold -s -w 62 >"$OUT/waldump-sample.txt"
awk '/RESTORE_POINT/ { on = 1 }
  on && $2 == "Transaction" && /COMMIT/ {
    tx = $0; sub(/.*tx: +/, "", tx); sub(/,.*/, "", tx)
    ts = $0; sub(/.*COMMIT /, "", ts)
    print "tx " tx "  COMMIT " ts
  }' "$WORK/waldump.txt" | cut -c 1-62 >"$OUT/waldump-commits.txt"

# 6б. Копия на конец WAL линии времени 1 (состояние до отката).
"$LAB_DIR/restore.sh" "$WORK/backups/$LATEST/data" "$COPY"
cat >>"$COPY/postgresql.conf" <<EOF
# lab5: копия для анализа — свой порт, без архивации,
# ветвь WAL до отката (линия времени 1).
port = $COPY_PORT
archive_mode = off
recovery_target_timeline = '1'
EOF
IBBD_PGDATA="$COPY" IBBD_PGPORT=$COPY_PORT "$PG" start
wait_promoted "$COPY_PORT"
su_copy -f "$LAB_DIR/sql/state.sql" >"$OUT/state-latest.txt"
compare "$OUT/state-after.txt" "$OUT/state-latest.txt" \
  after copy >"$OUT/compare-after-copy.txt"
su_copy -v since="$LOG_MAX" -f "$LAB_DIR/sql/log_new.sql" \
  >"$OUT/log-rolled-back.txt"

# 6в. Журнал операторов сервера до отката.
awk '/^[0-9][0-9][0-9][0-9]-/ { on = /statement:/ } on' \
  "$WORK/pgdata.before-restore/server.log" \
  | log_lines >"$OUT/server-statements.txt"

# 7. Логическая копия pg_dump восстанавливается в отдельную БД.
"$PG" psql -d postgres -q -c "CREATE DATABASE workshop_dump"
pg_restore -h 127.0.0.1 -p "$PORT" -U postgres -d workshop_dump \
  --exit-on-error "$WORK/backups/$LATEST/$DB.dump"
"$PG" psql -d workshop_dump -P pager=off \
  -f "$LAB_DIR/sql/state.sql" >"$OUT/state-dump.txt"
compare "$OUT/state-before.txt" "$OUT/state-dump.txt" \
  before dump >"$OUT/compare-before-dump.txt"
"$PG" psql -d postgres -q -c "DROP DATABASE workshop_dump"

ls -1 "$ARCHIVE" >"$OUT/archive-final.txt"
stop_all
echo "ok: $OUT"
