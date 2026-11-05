#!/bin/sh
# Запуск из любой папки. Приложение и БД работают в Docker.
set -eu

LAB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$LAB_DIR"
OPEN_BROWSER=1
STOP=0

usage() {
    printf '%s\n' \
        'Запуск: ./start.sh [--no-browser]' \
        'Остановка с сохранением данных: ./start.sh --stop'
}

for argument in "$@"; do
    case "$argument" in
        --no-browser) OPEN_BROWSER=0 ;;
        --stop) STOP=1 ;;
        --help|-h) usage; exit 0 ;;
        *) printf 'Неизвестный параметр: %s\n' "$argument" >&2; usage >&2; exit 2 ;;
    esac
done

# При запуске из Finder пользовательский PATH может не содержать Docker CLI.
if ! command -v docker >/dev/null 2>&1; then
    for docker_bin in "$HOME/.docker/bin" /Applications/Docker.app/Contents/Resources/bin /usr/local/bin /opt/homebrew/bin; do
        if [ -x "$docker_bin/docker" ]; then
            PATH="$docker_bin:$PATH"
            export PATH
            break
        fi
    done
fi
if ! command -v docker >/dev/null 2>&1; then
    printf '%s\n' 'Docker не найден. Установите Docker Desktop и повторите запуск.' >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    printf '%s\n' 'Не найден Docker Compose. Нужен Docker Desktop или Docker Engine с Compose v2+.' >&2
    exit 1
fi

if [ "$STOP" -eq 1 ]; then
    if [ ! -f .env ]; then
        printf '%s\n' 'Лабораторная ещё не запускалась: конфигурации .env нет.'
    elif ! docker info >/dev/null 2>&1; then
        printf '%s\n' 'Docker сейчас не запущен.'
    else
        docker compose down
        printf '\n%s\n' 'Лабораторная остановлена. Пользователи и документы сохранены.'
    fi
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Нужен Python 3 для создания конфигурации и проверки готовности.' >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    if [ "$(uname -s)" = Darwin ]; then
        printf '%s\n' 'Запускаю Docker Desktop…'
        if ! open -a Docker; then
            printf '%s\n' 'Не удалось открыть Docker Desktop. Запустите его вручную и повторите.' >&2
            exit 1
        fi
        attempt=0
        until docker info >/dev/null 2>&1; do
            attempt=$((attempt + 1))
            if [ "$attempt" -ge 90 ]; then
                printf '\n%s\n' 'Docker не стал доступен за 3 минуты. Проверьте окно Docker Desktop и повторите запуск.' >&2
                exit 1
            fi
            if [ $((attempt % 5)) -eq 1 ]; then
                printf '%s\n' 'Ожидаю готовности Docker Desktop…'
            fi
            sleep 2
        done
    else
        printf '%s\n' 'Docker не запущен или недоступен. Запустите Docker Engine и повторите.' >&2
        exit 1
    fi
fi

printf '\n%s\n' 'ПАСЗИ · лабораторная 4 · вариант 2'
python3 scripts/init_env.py
printf '\n%s\n' 'Собираю и запускаю приложение. Первый запуск может занять несколько минут.'
if ! docker compose up --build -d --wait --wait-timeout 180; then
    printf '\n%s\n' \
        'Запуск не завершён. Сообщение Docker находится выше.' \
        'Для просмотра журнала из папки лабораторной: docker compose logs backend frontend' >&2
    exit 1
fi

# Используем фактически опубликованный адрес, в том числе при изменённом FRONTEND_PORT.
APP_ADDRESS=$(docker compose port frontend 80)
APP_URL="http://$APP_ADDRESS/register"
python3 - "http://$APP_ADDRESS/api/health" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

for attempt in range(30):
    try:
        with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
            if response.status == 200 and json.load(response).get("status") == "ok":
                break
    except (urllib.error.URLError, TimeoutError, ValueError):
        pass
    time.sleep(1)
else:
    sys.exit("Контейнеры запущены, но приложение не ответило. Выполните docker compose logs backend frontend.")
PY

printf '\nГотово! Откройте: %s\n' "$APP_URL"
printf '%s\n' \
    'Зарегистрируйтесь или войдите в существующую учётную запись.' \
    'Окно терминала можно закрыть: приложение продолжит работать.' \
    'Для остановки запустите stop.command или ./start.sh --stop.'

if [ "$OPEN_BROWSER" -eq 1 ]; then
    case "$(uname -s)" in
        Darwin) open "$APP_URL" || printf '%s\n' 'Откройте ссылку выше вручную.' ;;
        Linux)
            if command -v xdg-open >/dev/null 2>&1; then
                xdg-open "$APP_URL" >/dev/null 2>&1 || printf '%s\n' 'Откройте ссылку выше вручную.'
            fi
            ;;
    esac
fi
