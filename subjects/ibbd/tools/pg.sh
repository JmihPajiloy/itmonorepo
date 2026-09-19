#!/bin/sh
# Учебный кластер PostgreSQL для лабораторных ИББД № 2–5.
# Кластер слушает только 127.0.0.1 и не затрагивает системный сервер.
set -eu

SUBJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PGDATA="${IBBD_PGDATA:-$SUBJECT_DIR/.pgdata}"
PGPORT="${IBBD_PGPORT:-55432}"
export PGDATA PGPORT

usage() {
  echo "usage: $0 init|start|stop|status|psql [psql args]|reset-db <name>" >&2
  exit 2
}

[ $# -ge 1 ] || usage
cmd=$1
shift

case "$cmd" in
  init)
    if [ -f "$PGDATA/PG_VERSION" ]; then
      exit 0
    fi
    initdb -D "$PGDATA" -U postgres -A trust --encoding=UTF8 --locale=ru_RU.UTF-8 >/dev/null
    cat >>"$PGDATA/postgresql.conf" <<EOF

# ibbd
port = $PGPORT
listen_addresses = '127.0.0.1'
unix_socket_directories = ''
password_encryption = 'scram-sha-256'
log_timezone = 'Europe/Moscow'
timezone = 'Europe/Moscow'
EOF
    cat >"$PGDATA/pg_hba.conf" <<'EOF'
# Суперпользователь postgres — только с loopback без пароля (учебный стенд).
host    all             postgres        127.0.0.1/32            trust
host    replication     postgres        127.0.0.1/32            trust
# Все прикладные роли входят только по паролю SCRAM-SHA-256.
host    all             all             127.0.0.1/32            scram-sha-256
EOF
    ;;
  start)
    "$0" init
    if ! pg_ctl status >/dev/null 2>&1; then
      pg_ctl -w -l "$PGDATA/server.log" start >/dev/null
    fi
    ;;
  stop)
    pg_ctl status >/dev/null 2>&1 && pg_ctl -w stop -m fast >/dev/null || true
    ;;
  status)
    pg_ctl status
    ;;
  psql)
    exec psql -X -h 127.0.0.1 -p "$PGPORT" -U postgres "$@"
    ;;
  reset-db)
    [ $# -eq 1 ] || usage
    psql -X -q -h 127.0.0.1 -p "$PGPORT" -U postgres -d postgres -v ON_ERROR_STOP=1 \
      -c "DROP DATABASE IF EXISTS \"$1\" WITH (FORCE)" \
      -c "CREATE DATABASE \"$1\" ENCODING 'UTF8' TEMPLATE template0"
    ;;
  *)
    usage
    ;;
esac
