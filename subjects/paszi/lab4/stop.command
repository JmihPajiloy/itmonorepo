#!/bin/sh
# Finder: остановка без удаления данных PostgreSQL.
LAB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
"$LAB_DIR/start.command" --stop "$@"
