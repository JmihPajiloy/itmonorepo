"""Вход через СУБД, серверные сессии, CSRF, SCRAM."""
import base64
import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field

import psycopg

# Групповые роли СУБД и соответствующие им виды
# интерфейса; порядок задаёт приоритет.
GROUPS = (
    ("admin_role", "admin"),
    ("reception_role", "reception"),
    ("restorer_role", "restorer"),
)
LOGIN_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
IDLE_TIMEOUT = 15 * 60
ABSOLUTE_TIMEOUT = 8 * 3600
MAX_FAILS = 5
FAIL_WINDOW = 5 * 60
BAD_LOGIN = "Неверное имя пользователя или пароль"


class LoginError(Exception):
    pass


@dataclass
class UserSession:
    conn: psycopg.Connection
    login: str
    kind: str
    created: float = field(default_factory=time.time)
    seen: float = field(default_factory=time.time)
    lock: threading.Lock = field(
        default_factory=threading.Lock)

    def expired(self, now):
        return (now - self.seen > IDLE_TIMEOUT
                or now - self.created > ABSOLUTE_TIMEOUT)


class SessionStore:
    """Сессии и неудачные попытки хранятся в памяти
    процесса; в cookie попадает только случайный sid."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items = {}
        self._fails = {}

    def add(self, us):
        sid = secrets.token_urlsafe(32)
        with self._lock:
            self._items[sid] = us
        return sid

    def get(self, sid):
        if not sid:
            return None
        now = time.time()
        with self._lock:
            us = self._items.get(sid)
            if us is None:
                return None
            if us.expired(now) or us.conn.closed:
                del self._items[sid]
            else:
                us.seen = now
                return us
        us.conn.close()
        return None

    def drop(self, sid):
        with self._lock:
            us = self._items.pop(sid, None)
        if us is not None:
            us.conn.close()

    def locked(self, key):
        now = time.time()
        with self._lock:
            recent = [t for t in self._fails.get(key, ())
                      if now - t < FAIL_WINDOW]
            self._fails[key] = recent
            return len(recent) >= MAX_FAILS

    def fail(self, key):
        with self._lock:
            self._fails.setdefault(key, []).append(
                time.time())

    def reset(self, key):
        with self._lock:
            self._fails.pop(key, None)


def login(store, cfg, username, password, addr):
    """Открывает соединение с СУБД от имени пользователя.
    Пароль проверяет PostgreSQL (SCRAM-SHA-256)."""
    key = (username, addr)
    if store.locked(key):
        raise LoginError("Слишком много неудачных попыток; "
                         "повторите вход позже")
    if not LOGIN_RE.match(username) or not password:
        store.fail(key)
        raise LoginError(BAD_LOGIN)
    try:
        conn = psycopg.connect(
            host=cfg["PGHOST"], port=cfg["PGPORT"],
            dbname=cfg["PGDATABASE"], user=username,
            password=password, connect_timeout=5,
            application_name="ibbd-lab4", autocommit=True)
    except psycopg.OperationalError:
        store.fail(key)
        raise LoginError(BAD_LOGIN) from None
    try:
        kind = check_account(conn)
    except Exception:
        conn.close()
        raise
    if kind is None:
        conn.close()
        store.fail(key)
        raise LoginError(BAD_LOGIN)
    conn.execute("SET statement_timeout = '5s'")
    store.reset(key)
    return store.add(UserSession(conn, username, kind))


def check_account(conn):
    """Вид интерфейса или None, если вход не допускается."""
    # Вход без пароля (trust) и суперпользователь
    # в веб-приложение не допускаются.
    if not conn.pgconn.used_password:
        return None
    row = conn.execute(
        "SELECT rolsuper FROM pg_roles"
        " WHERE rolname = current_user").fetchone()
    if row is None or row[0]:
        return None
    for group, kind in GROUPS:
        member = conn.execute(
            "SELECT pg_has_role(current_user, %s, 'MEMBER')",
            (group,)).fetchone()[0]
        if member:
            return kind
    return None


def new_csrf():
    return secrets.token_urlsafe(32)


def csrf_ok(expected, got):
    return bool(expected) and bool(got) and \
        hmac.compare_digest(expected, got)


def scram_verifier(password, iterations=4096):
    """SCRAM-SHA-256-верификатор в формате PostgreSQL
    (RFC 5802, RFC 7677): открытый пароль не
    передаётся серверу."""
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, iterations)
    client = hmac.new(salted, b"Client Key",
                      "sha256").digest()
    stored = hashlib.sha256(client).digest()
    server = hmac.new(salted, b"Server Key",
                      "sha256").digest()

    def b64(b):
        return base64.b64encode(b).decode()

    return (f"SCRAM-SHA-256${iterations}:{b64(salt)}"
            f"${b64(stored)}:{b64(server)}")
