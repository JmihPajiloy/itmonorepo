"""Веб-интерфейс БД workshop: маршруты Flask."""
import functools
import os
import re
import secrets

import psycopg
from flask import (Flask, abort, flash, g, redirect,
                   render_template, request, session,
                   url_for)

from . import auth, db, reports

KIND_TITLE = {"admin": "администратор",
              "reception": "приёмщик",
              "restorer": "реставратор"}
PASSWORD_RE = re.compile(r"^[\x21-\x7e]{12,64}$")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("IBBD_SECRET_KEY")
        or secrets.token_bytes(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get(
            "IBBD_COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=64 * 1024,
        PGHOST=os.environ.get("IBBD_PGHOST", "127.0.0.1"),
        PGPORT=int(os.environ.get("IBBD_PGPORT", "55432")),
        PGDATABASE=os.environ.get("IBBD_DB", "workshop"),
    )
    if test_config:
        app.config.update(test_config)
    store = auth.SessionStore()
    app.extensions["ibbd_store"] = store

    @app.before_request
    def load_user():
        g.us = store.get(session.get("sid"))
        if session.get("sid") and g.us is None:
            session.pop("sid")
        if "csrf" not in session:
            session["csrf"] = auth.new_csrf()
        if request.method == "POST" and not auth.csrf_ok(
                session["csrf"], request.form.get("csrf")):
            abort(400, "Неверный CSRF-токен")

    @app.after_request
    def headers(resp):
        h = resp.headers
        h["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'")
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def common():
        us = g.get("us")
        return {"us": us, "csrf": session.get("csrf"),
                "kind_title": KIND_TITLE,
                "reports": reports.for_kind(us.kind)
                if us else []}

    def login_required(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if g.us is None:
                return redirect(url_for("login_form"))
            with g.us.lock:
                try:
                    return view(*args, **kwargs)
                except psycopg.OperationalError:
                    store.drop(session.pop("sid", None))
                    flash("Соединение с СУБД потеряно")
                    return redirect(url_for("login_form"))
        return wrapper

    def db_error(e):
        msg = e.diag.message_primary or str(e)
        flash(f"Ошибка СУБД ({e.sqlstate}): {msg}", "error")

    @app.get("/")
    def index():
        if g.us is None:
            return redirect(url_for("login_form"))
        return redirect(url_for("home"))

    @app.get("/login")
    def login_form():
        return render_template("login.html")

    @app.post("/login")
    def login():
        name = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            sid = auth.login(store, app.config, name,
                             password, request.remote_addr)
        except auth.LoginError as e:
            flash(str(e), "error")
            return render_template("login.html",
                                   username=name), 401
        # Новая сессия и новый CSRF-токен после входа.
        store.drop(session.get("sid"))
        session.clear()
        session["sid"] = sid
        session["csrf"] = auth.new_csrf()
        return redirect(url_for("home"))

    @app.post("/logout")
    def logout():
        store.drop(session.pop("sid", None))
        session.clear()
        flash("Сеанс завершён")
        return redirect(url_for("login_form"))

    @app.get("/tables")
    @login_required
    def home():
        return render_template(
            "home.html", relations=db.relations(g.us.conn))

    def table_context(name):
        rel = db.find_relation(g.us.conn, name)
        if rel is None:
            abort(404)
        cols = db.columns(g.us.conn, name)
        visible = [c for c in cols if c.can_select]
        return rel, cols, visible

    def filter_sort(names):
        fcol = request.args.get("fcol", "")
        fop = request.args.get("fop", "like")
        fval = request.args.get("fval", "")
        sort = request.args.get("sort", "")
        desc = request.args.get("dir") == "desc"
        flt = None
        if fcol in names and fval:
            flt = (fcol, "eq" if fop == "eq" else "like",
                   fval)
        srt = (sort, desc) if sort in names else None
        return flt, srt

    @app.get("/t/<name>")
    @login_required
    def table(name):
        rel, cols, visible = table_context(name)
        names = [c.name for c in visible]
        flt, srt = filter_sort(names)
        rows = []
        try:
            rows = db.select_rows(g.us.conn, name, names,
                                  flt, srt)
        except psycopg.Error as e:
            db_error(e)
        keys = [c.name for c in cols if c.is_pk]
        deletable = (rel.can_delete and keys
                     and set(keys) <= set(names))
        return render_template(
            "table.html", rel=rel, cols=cols,
            visible=visible, rows=rows, keys=keys,
            key_idx=[names.index(k) for k in keys]
            if deletable else [],
            deletable=deletable, args=request.args,
            limit=db.ROW_LIMIT)

    def key_values(cols):
        keys = [c.name for c in cols if c.is_pk]
        return {k: request.form.get("key_" + k, "")
                for k in keys}

    @app.post("/t/<name>/insert")
    @login_required
    def insert(name):
        rel, cols, _ = table_context(name)
        values = {c.name: request.form.get("col_" + c.name)
                  for c in cols if c.can_insert}
        values = {k: v for k, v in values.items() if v}
        if not values:
            flash("Не заполнено ни одного поля", "error")
        else:
            try:
                n = db.insert_row(g.us.conn, name, values)
                flash(f"Добавлено строк: {n}")
            except psycopg.Error as e:
                db_error(e)
        return redirect(url_for("table", name=name))

    @app.post("/t/<name>/delete")
    @login_required
    def delete(name):
        _, cols, _ = table_context(name)
        key = key_values(cols)
        if not key or not all(key.values()):
            abort(400)
        try:
            n = db.delete_row(g.us.conn, name, key)
            flash(f"Удалено строк: {n}")
        except psycopg.Error as e:
            db_error(e)
        return redirect(url_for("table", name=name))

    @app.post("/t/<name>/update")
    @login_required
    def update(name):
        _, cols, _ = table_context(name)
        key = key_values(cols)
        col = request.form.get("column", "")
        allowed = {c.name for c in cols if c.can_update}
        if not key or not all(key.values()) \
                or col not in allowed:
            abort(400)
        value = request.form.get("value") or None
        try:
            n = db.update_value(g.us.conn, name, key, col,
                                value)
            flash(f"Изменено строк: {n}")
        except psycopg.Error as e:
            db_error(e)
        return redirect(url_for("table", name=name))

    @app.get("/r/<key>")
    @login_required
    def report(key):
        rep = reports.find(g.us.kind, key)
        if rep is None:
            abort(404)
        params = reports.clean_params(rep, request.args)
        names, rows = [], []
        try:
            names = reports.columns(g.us.conn, rep, params)
            flt, srt = filter_sort(names)
            rows = reports.run(g.us.conn, rep, params,
                               flt, srt)
        except psycopg.Error as e:
            db_error(e)
        return render_template(
            "report.html", rep=rep, names=names, rows=rows,
            params=params, args=request.args)

    @app.route("/register", methods=["GET", "POST"])
    @login_required
    def register():
        if g.us.kind != "admin":
            abort(403)
        conn = g.us.conn
        if request.method == "POST":
            login_ = request.form.get("login", "")
            group = request.form.get("group", "")
            pw = request.form.get("password", "")
            emp = request.form.get("employee_id") or None
            if not PASSWORD_RE.match(pw):
                flash("Пароль: 12–64 печатных символа "
                      "ASCII без пробелов", "error")
            else:
                try:
                    conn.execute(
                        "SELECT app_register_user("
                        "%s, %s, %s, %s)",
                        (login_, group,
                         auth.scram_verifier(pw), emp))
                    flash(f"Создан пользователь {login_}")
                    return redirect(url_for("register"))
                except psycopg.Error as e:
                    db_error(e)
        users = conn.execute(
            "SELECT r.rolname, g.rolname"
            " FROM pg_roles r"
            " JOIN pg_auth_members m ON m.member = r.oid"
            " JOIN pg_roles g ON g.oid = m.roleid"
            " WHERE g.rolname IN ('reception_role',"
            " 'restorer_role', 'admin_role')"
            " ORDER BY 2, 1").fetchall()
        free = conn.execute(
            "SELECT employee_id, full_name FROM employee"
            " WHERE db_login IS NULL"
            " ORDER BY employee_id").fetchall()
        return render_template("register.html",
                               users=users, free=free)

    return app
