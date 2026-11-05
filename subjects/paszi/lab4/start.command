#!/bin/sh
# Finder: двойной щелчок запускает лабораторную и открывает браузер.
LAB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
"$LAB_DIR/start.sh" "$@"
result=$?
if [ "$result" -ne 0 ] && [ -t 0 ]; then
    printf '\n%s\n' 'Запуск не удался. Нажмите Enter, чтобы закрыть это окно.'
    read -r answer
fi
exit "$result"
