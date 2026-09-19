#!/bin/sh
# archive_command: копирует сегмент WAL в архив.
# Вызов из PostgreSQL: archive_wal.sh %p %f
# Существующий файл не перезаписывается: при повторе
# PostgreSQL получит ошибку и повторит попытку позже.
set -eu
ARCHIVE="${WAL_ARCHIVE:-$(dirname "$0")/work/wal_archive}"
test ! -f "$ARCHIVE/$2"
cp "$1" "$ARCHIVE/$2.tmp"
mv "$ARCHIVE/$2.tmp" "$ARCHIVE/$2"
