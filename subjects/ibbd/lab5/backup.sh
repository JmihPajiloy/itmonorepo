#!/bin/sh
# Плановое резервное копирование кластера ЛР5 (задание cron).
# 1) физическая базовая копия pg_basebackup и её проверка;
# 2) логическая копия БД workshop (pg_dump) и ролей;
# 3) хранение KEEP последних копий, очистка архива WAL.
set -eu
LAB_DIR=$(cd "$(dirname "$0")" && pwd)
PGHOST=127.0.0.1
PGPORT="${IBBD_PGPORT:-55433}"
PGUSER=postgres
export PGHOST PGPORT PGUSER
ROOT="${BACKUP_ROOT:-$LAB_DIR/work/backups}"
ARCHIVE="${WAL_ARCHIVE:-$LAB_DIR/work/wal_archive}"
KEEP="${KEEP:-7}"
DB=workshop

umask 077
stamp=$(date +%Y%m%d-%H%M%S)
dest="$ROOT/$stamp"
mkdir -p "$ROOT"
log() { echo "$(date +%H:%M:%S) $*"; }

log "base backup -> $stamp/data"
pg_basebackup -D "$dest/data" -Fp -Xstream \
  --checkpoint=fast --label="lab5 $stamp"
pg_verifybackup -q "$dest/data"
log "manifest verified"

pg_dump -Fc -f "$dest/$DB.dump" "$DB"
# Роли кластера (с хэшами паролей SCRAM).
pg_dumpall --globals-only -f "$dest/globals.sql"
log "pg_dump: $(pg_restore -l "$dest/$DB.dump" \
  | grep -c 'TABLE DATA') tables"

# Удаление копий сверх KEEP последних.
ls -1 "$ROOT" | sort -r | tail -n +"$((KEEP + 1))" |
while read -r old; do
  rm -rf "${ROOT:?}/$old"
  log "removed old backup $old"
done

# WAL старше самой ранней оставшейся копии не нужен.
oldest=$(ls -1 "$ROOT" | sort | head -n 1)
first=$(sed -n 's/^START WAL.*(file \(.*\))$/\1/p' \
  "$ROOT/$oldest/data/backup_label")
pg_archivecleanup "$ARCHIVE" "$first"
log "WAL archive kept from $first"
