"""Проверка веб-приложения на настоящей БД workshop.
Запросы выполняются тестовым клиентом Flask, вход —
настоящими учётными записями PostgreSQL."""
import csv
import html
import os
import re
import sys
import textwrap
import time
from html.parser import HTMLParser
from pathlib import Path

import psycopg

from webapp import create_app

OUT = Path(sys.argv[1] if len(sys.argv) > 1
           else "verification")
PW = {
    "reception_orlova": os.environ.get(
        "IBBD_RECEPTION_PASSWORD", "reception-demo-pass"),
    "restorer_smirnov": os.environ.get(
        "IBBD_RESTORER_PASSWORD", "restorer-demo-pass"),
    "workshop_admin": os.environ.get(
        "IBBD_ADMIN_PASSWORD", "admin-demo-pass"),
}
NEW_PW = "new-user-demo-pass"
PG = dict(host="127.0.0.1",
          port=int(os.environ.get("IBBD_PGPORT", "55432")),
          dbname="workshop")
results = []


class Cells(HTMLParser):
    """Строки всех таблиц HTML-страницы: списки ячеек."""

    def __init__(self, page):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def text(resp):
    return resp.get_data(as_text=True)


def flashes(resp):
    found = re.findall(r'class="flash[^"]*">([^<]*)<',
                       text(resp))
    return [html.unescape(f) for f in found]


def check(name, ok, detail=""):
    results.append((ok, name, detail))
    print("ok  " if ok else "FAIL", name, detail)


def csrf(client):
    page = text(client.get("/login"))
    m = re.search(r'name="csrf" value="([^"]+)"', page)
    return m.group(1) if m else None


def token(client, path):
    m = re.search(r'name="csrf" value="([^"]+)"',
                  text(client.get(path)))
    return m.group(1)


def login(client, user, password):
    return client.post("/login", data={
        "username": user, "password": password,
        "csrf": csrf(client)})


def post(client, path, data, page="/tables"):
    data = dict(data, csrf=token(client, page))
    return client.post(path, data=data,
                       follow_redirects=True)


def save(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


def save_csv(name, rows, drop=()):
    """Результат страницы в CSV для таблиц отчёта."""
    keep = [i for i, h in enumerate(rows[0])
            if h not in drop]
    with open(OUT / name, "w", newline="",
              encoding="utf-8") as f:
        csv.writer(f).writerows(
            [[r[i] for i in keep] for r in rows])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = create_app({"TESTING": True})
    store = app.extensions["ibbd_store"]

    # 1. Аутентификация.
    c = app.test_client()
    r = login(c, "reception_orlova", "wrong-password")
    check("неверный пароль отклонён", r.status_code == 401,
          f"HTTP {r.status_code}")
    r = login(c, "postgres", "anything")
    check("postgres (trust) не допускается",
          r.status_code == 401, f"HTTP {r.status_code}")
    r = login(c, "no_such_user", "whatever-pass")
    check("несуществующий пользователь",
          r.status_code == 401, f"HTTP {r.status_code}")
    r = c.post("/login", data={
        "username": "reception_orlova",
        "password": PW["reception_orlova"]})
    check("вход без CSRF-токена", r.status_code == 400,
          f"HTTP {r.status_code}")
    c2 = create_app({"TESTING": True}).test_client()
    codes = [login(c2, "restorer_volkova", "bad-pass-"
                   + str(i)).status_code for i in range(5)]
    r = login(c2, "restorer_volkova",
              PW["restorer_smirnov"])
    check("блокировка после 5 неудач",
          "Слишком много" in text(r),
          f"HTTP {codes[-1]}, затем {r.status_code}")

    clients = {}
    for user, pw in PW.items():
        cl = app.test_client()
        r = login(cl, user, pw)
        check(f"вход {user}", r.status_code == 302,
              f"HTTP {r.status_code}")
        clients[user] = cl
    rec = clients["reception_orlova"]
    res = clients["restorer_smirnov"]
    adm = clients["workshop_admin"]

    r = rec.get("/tables")
    h = r.headers
    check("заголовки безопасности",
          "default-src 'self'" in h["Content-Security-Policy"]
          and h["X-Frame-Options"] == "DENY"
          and h["Cache-Control"] == "no-store")
    cookie = rec.get_cookie("session")
    check("cookie HttpOnly, SameSite=Strict",
          cookie.http_only and cookie.same_site == "Strict")

    # 2. Списки отношений по ролям.
    counts = {}
    for user, cl in clients.items():
        rows = Cells(text(cl.get("/tables"))).rows
        rows = [r for r in rows if len(r) == 6]
        counts[user] = len(rows) - 1
        save_csv(f"tables-{user}.csv", rows)
    check("отношений у приёмщика", counts[
        "reception_orlova"] == 8,
        str(counts["reception_orlova"]))
    check("отношений у реставратора", counts[
        "restorer_smirnov"] == 9,
        str(counts["restorer_smirnov"]))
    check("отношений у администратора", counts[
        "workshop_admin"] == 15,
        str(counts["workshop_admin"]))

    # 3. Просмотр, сортировка, фильтр, скрытые столбцы.
    r = rec.get("/t/customer?fcol=full_name&fop=like"
                "&fval=ова&sort=full_name&dir=desc")
    rows = Cells(text(r)).rows
    names = [x[1] for x in rows[1:]]
    check("фильтр и сортировка customer",
          names == sorted(names, reverse=True)
          and all("ова" in n for n in names),
          f"{len(names)} строк")
    save_csv("customer-filter.csv",
             [x[:3] for x in rows])
    r = res.get("/t/instrument")
    check("скрыт instrument.customer_id у реставратора",
          "Скрыты столбцы без права чтения:" in text(r)
          and "customer_id" not in Cells(text(r)).rows[0])
    for path in ("/t/payment", "/t/change_log",
                 "/t/customer%3B--", "/r/payments"):
        code = res.get(path).status_code
        check(f"реставратор {path}", code == 404,
              f"HTTP {code}")
    r = rec.get("/t/customer?sort=full_name;DROP"
                "&fcol=phone&fval=' OR 1=1 --")
    n = len(Cells(text(r)).rows) - 1
    check("попытка SQL-инъекции в фильтре",
          r.status_code == 200 and n == 0, f"{n} строк")

    # 4. Вставка, изменение, удаление; решает СУБД.
    r = post(rec, "/t/customer/insert", {
        "col_full_name": "Тестова Вера Ивановна",
        "col_phone": "+7 900 000-00-99",
        "col_email": "vera@example.test"})
    check("приёмщик добавил заказчика",
          "Добавлено строк: 1" in flashes(r))
    new_id = next(x[0] for x in Cells(text(
        rec.get("/t/customer?fcol=full_name&fop=eq"
                "&fval=Тестова Вера Ивановна"))).rows[1:])
    r = post(rec, "/t/customer/delete",
             {"key_customer_id": new_id})
    check("приёмщик не может удалить", any(
        "42501" in f for f in flashes(r)), flashes(r)[0])
    r = rec.post("/t/customer/insert", data={
        "col_full_name": "X", "col_phone": "1",
        "csrf": "forged"})
    check("POST с чужим CSRF-токеном",
          r.status_code == 400, f"HTTP {r.status_code}")
    r = post(res, "/t/order_work/update", {
        "key_order_id": "1", "key_line_no": "1",
        "column": "status", "value": "in_progress"})
    check("реставратор изменил свою работу",
          "Изменено строк: 1" in flashes(r))
    r = post(res, "/t/order_work/update", {
        "key_order_id": "2", "key_line_no": "1",
        "column": "status", "value": "done"})
    check("чужая работа не изменена (RLS)",
          "Изменено строк: 0" in flashes(r))
    r = post(res, "/t/order_work/update", {
        "key_order_id": "1", "key_line_no": "1",
        "column": "agreed_price_kopecks", "value": "0"})
    check("цена недоступна для изменения",
          r.status_code == 400, f"HTTP {r.status_code}")
    r = post(res, "/t/inspection/insert", {
        "col_order_id": "2", "col_employee_id": "2",
        "col_inspected_on": "2026-09-19",
        "col_conclusion": "Подпись чужим именем"})
    check("осмотр от чужого имени (RLS)", any(
        "42501" in f for f in flashes(r)), flashes(r)[0])
    r = post(res, "/t/inspection/insert", {
        "col_order_id": "1", "col_employee_id": "1",
        "col_inspected_on": "2026-09-19",
        "col_conclusion": "Проверка через веб-интерфейс"})
    check("осмотр от своего имени",
          "Добавлено строк: 1" in flashes(r))
    r = post(adm, "/t/customer/delete",
             {"key_customer_id": new_id})
    check("администратор удалил заказчика",
          "Удалено строк: 1" in flashes(r))
    r = post(adm, "/t/customer/delete",
             {"key_customer_id": "1"})
    check("удаление связанной строки (FK)", any(
        "23503" in f for f in flashes(r)), flashes(r)[0])

    # 5. Сводные отчёты с GROUP BY.
    specs = [
        (rec, "payments", "?sort=paid_rub&dir=desc", ()),
        (res, "workload",
         "?ostatus=&sort=works&dir=desc", ()),
        (adm, "employees",
         "?sort=agreed_rub&dir=desc", ()),
        (adm, "audit", "?sort=total&dir=desc",
         ("app_group", "last_change")),
    ]
    for cl, key, qs, drop in specs:
        rows = Cells(text(cl.get("/r/" + key + qs))).rows
        check(f"отчёт {key}", len(rows) > 1,
              f"{len(rows) - 1} групп")
        save_csv(f"report-{key}.csv", rows, drop)
    rows = Cells(text(rec.get(
        "/r/payments?method=card&fcol=instrument_type"
        "&fval=к&sort=instrument_type"))).rows
    check("отчёт payments: фильтр и сортировка",
          len(rows) > 1 and all(
              "к" in x[0].lower() for x in rows[1:]),
          f"{len(rows) - 1} групп")
    save_csv("report-payments-card.csv", rows)
    rows = Cells(text(res.get(
        "/r/workload?mine=1&sort=service"))).rows
    check("отчёт workload: только мои",
          len(rows) > 1 and all(
              x[0].startswith("Смирнов") for x in rows[1:]),
          f"{len(rows) - 1} групп")
    save_csv("report-workload-mine.csv", rows)
    r = rec.get("/r/audit")
    check("приёмщику отчёт audit недоступен",
          r.status_code == 404, f"HTTP {r.status_code}")

    # 6. Регистрация пользователей.
    r = post(adm, "/register", {
        "login": "reception_petrova",
        "group": "reception_role",
        "password": NEW_PW}, "/register")
    check("регистрация reception_petrova",
          "Создан пользователь reception_petrova"
          in flashes(r))
    r = post(adm, "/register", {
        "login": "restorer_kozlov",
        "group": "restorer_role", "employee_id": "3",
        "password": NEW_PW}, "/register")
    check("регистрация restorer_kozlov",
          "Создан пользователь restorer_kozlov"
          in flashes(r))
    r = post(adm, "/register", {
        "login": "hacker", "group": "admin_role",
        "password": NEW_PW}, "/register")
    check("регистрация в admin_role отклонена", any(
        "недопустимая роль" in f for f in flashes(r)),
        flashes(r)[0])
    code = rec.get("/register").status_code
    check("приёмщику регистрация недоступна",
          code == 403, f"HTTP {code}")
    rows = Cells(text(adm.get("/register"))).rows
    save_csv("users.csv", rows)
    for user in ("reception_petrova", "restorer_kozlov"):
        cl = app.test_client()
        r = login(cl, user, NEW_PW)
        check(f"вход {user}", r.status_code == 302,
              f"HTTP {r.status_code}")
    r = post(cl, "/t/order_work/update", {
        "key_order_id": "4", "key_line_no": "1",
        "column": "status", "value": "done"})
    check("restorer_kozlov изменил свою работу",
          "Изменено строк: 1" in flashes(r))

    with psycopg.connect(**PG, user="reception_orlova",
                         password=PW["reception_orlova"],
                         autocommit=True) as conn:
        try:
            conn.execute("SELECT app_register_user("
                         "'x_user', 'reception_role', "
                         "'SCRAM-SHA-256$4096:x')")
            check("функция регистрации закрыта", False)
        except psycopg.errors.InsufficientPrivilege as e:
            check("функция регистрации закрыта", True,
                  e.sqlstate)
    with psycopg.connect(**PG, user="postgres") as conn:
        rows = conn.execute(
            "SELECT rolname, left(rolpassword, 19)"
            " FROM pg_authid WHERE rolname IN"
            " ('reception_petrova', 'restorer_kozlov',"
            "  'workshop_admin') ORDER BY 1").fetchall()
        check("пароли хранятся как SCRAM", all(
            p == "SCRAM-SHA-256$4096:" for _, p in rows))
        save_csv("scram.csv",
                 [["rolname", "rolpassword"]]
                 + [list(x) for x in rows])

    # 7. Журнал и завершение сеанса.
    rows = Cells(text(adm.get(
        "/t/change_log?sort=log_id"))).rows
    head = rows[0]
    keep = ["log_id", "db_role", "operation",
            "table_name", "row_key"]
    log = [[r[head.index(k)] for k in keep] for r in rows]
    roles = {r[1] for r in log[1:]}
    check("журнал: роли входа из веб-сеансов",
          {"reception_orlova", "restorer_smirnov",
           "workshop_admin", "restorer_kozlov"} <= roles,
          f"{len(log) - 1} записей")
    save_csv("change-log.csv", log)

    old = rec.get_cookie("session").value
    post(rec, "/logout", {})
    rec.set_cookie("session", old)
    r = rec.get("/tables")
    check("старая cookie после выхода",
          r.status_code == 302, f"HTTP {r.status_code}")
    for us in list(store._items.values()):
        if us.login == "restorer_smirnov":
            us.seen = time.time() - 16 * 60
    r = res.get("/tables")
    check("истечение сеанса (15 мин)",
          r.status_code == 302, f"HTTP {r.status_code}")

    failed = [n for ok, n, _ in results if not ok]
    summary = (f"Проверок: {len(results)}, успешно: "
               f"{len(results) - len(failed)}")
    lines = []
    for ok, n, d in results:
        line = f"{'ok  ' if ok else 'FAIL'} {n}"
        if d and len(line) + len(d) + 3 <= 62:
            lines.append(f"{line} [{d}]")
            continue
        lines.append(line)
        lines += textwrap.wrap(d, 56, initial_indent=" " * 6,
                               subsequent_indent=" " * 6)
    save("check.txt", "\n".join(lines + ["", summary])
         + "\n")
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
