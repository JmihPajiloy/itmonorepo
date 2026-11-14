from datetime import datetime, timezone

from sqlalchemy import text

from .conftest import PASSWORD


def login(client):
    credentials = {"login": "cookie_user", "password": PASSWORD}
    assert client.post("/api/register", json=credentials).status_code == 201
    response = client.post("/api/login", json=credentials)
    assert response.status_code == 200
    assert "access_token" not in response.json()
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("HttpOnly" in cookie and "SameSite=strict" in cookie for cookie in cookies)
    return client.cookies.get("lab4_access"), client.cookies.get("lab4_refresh")


def test_cookie_session_refresh_and_logout(client):
    access, refresh = login(client)
    assert client.get("/api/me").json()["login"] == "cookie_user"
    client.cookies.delete("lab4_access")

    assert client.get("/api/me").status_code == 401
    assert client.post("/api/auth/refresh").status_code == 204
    assert client.get("/api/me").json()["login"] == "cookie_user"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/auth/refresh", headers={"Cookie": f"lab4_refresh={refresh}"}).status_code == 401
    assert client.get("/api/me", headers={"Cookie": f"lab4_access={access}"}).status_code == 401


def test_expired_session_and_cross_site_mutations(client, database):
    login(client)
    assert client.post("/api/auth/logout", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/api/me").status_code == 200

    with database.begin() as connection:
        connection.execute(text("UPDATE auth_sessions SET expires_at = :now"), {"now": datetime.now(timezone.utc)})
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401
