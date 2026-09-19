"""Снимки экрана работающего приложения: сервер на
127.0.0.1, браузер Google Chrome под управлением
Playwright входит через форму, как пользователь."""
import logging
import os
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from webapp import create_app

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "shots")
PW = {
    "reception_orlova": os.environ.get(
        "IBBD_RECEPTION_PASSWORD", "reception-demo-pass"),
    "restorer_smirnov": os.environ.get(
        "IBBD_RESTORER_PASSWORD", "restorer-demo-pass"),
    "workshop_admin": os.environ.get(
        "IBBD_ADMIN_PASSWORD", "admin-demo-pass"),
}


def main():
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    OUT.mkdir(parents=True, exist_ok=True)
    server = make_server("127.0.0.1", 0, create_app(),
                         threaded=True)
    base = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever,
                     daemon=True).start()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(
            viewport={"width": 1100, "height": 700},
            locale="ru-RU")
        page = ctx.new_page()

        def shot(name, path=None):
            if path:
                page.goto(base + path)
            page.screenshot(path=OUT / f"{name}.png",
                            full_page=True)

        def login(user, password):
            page.goto(base + "/login")
            page.fill("input[name=username]", user)
            page.fill("input[name=password]", password)
            page.click("form.card button")

        def logout():
            page.click("header form button")

        login("reception_orlova", "wrong-password")
        page.screenshot(path=OUT / "01-login-failed.png",
                        clip={"x": 0, "y": 0,
                              "width": 1100, "height": 330})
        login("reception_orlova", PW["reception_orlova"])
        shot("02-reception-tables")
        shot("03-reception-customer",
             "/t/customer?fcol=full_name&fop=like"
             "&fval=ова&sort=full_name&dir=desc")
        shot("04-reception-report",
             "/r/payments?sort=paid_rub&dir=desc")
        logout()

        login("restorer_smirnov", PW["restorer_smirnov"])
        shot("05-restorer-tables")
        shot("06-restorer-instrument", "/t/instrument")
        page.goto(base + "/t/inspection")
        form = "form[action$='/insert'] "
        page.fill(form + "[name=col_order_id]", "2")
        page.fill(form + "[name=col_employee_id]", "2")
        page.fill(form + "[name=col_inspected_on]",
                  "2026-09-19")
        page.fill(form + "[name=col_conclusion]",
                  "Подпись чужим именем")
        page.click(form + "button")
        page.screenshot(path=OUT / "07-restorer-rls.png",
                        clip={"x": 0, "y": 0,
                              "width": 1100, "height": 330})
        shot("08-restorer-report",
             "/r/workload?sort=works&dir=desc")
        logout()

        login("workshop_admin", PW["workshop_admin"])
        shot("09-admin-tables")
        shot("10-admin-audit",
             "/r/audit?sort=total&dir=desc")
        shot("11-admin-users", "/register")
        logout()
        browser.close()
    server.shutdown()
    print("ok:", OUT)


if __name__ == "__main__":
    main()
