#!/bin/sh
# Восстановление кластера до точки восстановления (PITR).
# usage: restore.sh BACKUP_DATA NEW_PGDATA [RESTORE_POINT]
# Без RESTORE_POINT WAL из архива применяется до конца.
set -eu
LAB_DIR=$(cd "$(dirname "$0")" && pwd)
ARCHIVE="${WAL_ARCHIVE:-$LAB_DIR/work/wal_archive}"
src=$1 dst=$2 target=${3:-}

test ! -e "$dst"
cp -Rp "$src" "$dst"
chmod 700 "$dst"
# Журнал сервера, скопированный вместе с каталогом данных.
rm -f "$dst/server.log"

{
  echo "# lab5: восстановление из архива WAL"
  echo "restore_command = 'cp \"$ARCHIVE/%f\" \"%p\"'"
  if [ -n "$target" ]; then
    echo "recovery_target_name = '$target'"
    echo "recovery_target_action = 'promote'"
  fi
} >>"$dst/postgresql.conf"
touch "$dst/recovery.signal"
