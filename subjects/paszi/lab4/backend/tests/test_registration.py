from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from app.security import hasher
from .conftest import PASSWORD, account


def test_successful_registration_hash_and_salt(client, database):
    response = client.post("/api/register", json={"login": "ivan.shibaev", "password": PASSWORD})
    assert response.status_code == 201
    assert "password" not in response.text
    client.post("/api/register", json={"login": "partner", "password": PASSWORD})
    with database.connect() as connection:
        rows = connection.execute(text("SELECT login, password_hash, created_at FROM users ORDER BY id")).all()
    assert rows[0].login == "ivan.shibaev" and rows[0].created_at is not None
    assert rows[0].password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert hasher.verify(rows[0].password_hash, PASSWORD)
    assert rows[0].password_hash != rows[1].password_hash  # случайная соль для одинакового пароля


def test_duplicate_login(client, database):
    body = {"login": "ivan", "password": PASSWORD}
    assert client.post("/api/register", json=body).status_code == 201
    assert client.post("/api/register", json=body).status_code == 409
    with database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == 1


def test_underscore_is_a_special_character(client):
    assert client.post("/api/register", json={"login": "underscore", "password": "Aa1_aaaa"}).status_code == 201


def test_concurrent_duplicate_login(client):
    def register(_):
        return client.post("/api/register", json={"login": "concurrent", "password": PASSWORD}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(register, range(2))) == [201, 409]


@pytest.mark.parametrize("password", ["weak", "alllowercase1!", "ALLUPPERCASE1!", "NoDigitsHere!", "NoSpecial123", "Aa1!aaa"])
def test_weak_password(client, database, password):
    response = client.post("/api/register", json={"login": "ivan", "password": password})
    assert response.status_code == 422
    assert password not in response.text
    with database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users")) == 0


@pytest.mark.parametrize("login", ["ab", "a" * 33, "иван", "a b", "abc\n"])
def test_invalid_login(client, login):
    assert client.post("/api/register", json={"login": login, "password": PASSWORD}).status_code == 422


def test_login_and_protected_endpoint(client):
    auth = account(client, "ivan")
    assert client.get("/api/me", headers=auth).json()["login"] == "ivan"
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer forged"}).status_code == 401
    for login in ("ivan", "unknown"):
        assert client.post("/api/login", json={"login": login, "password": "Wrong-Pass1!"}).status_code == 401


def test_logs_and_errors_do_not_contain_password(client, caplog):
    with caplog.at_level("INFO", logger="lab4"):
        client.post("/api/register", json={"login": "ivan", "password": PASSWORD})
        client.post("/api/register", json={"login": "ivan", "password": PASSWORD})
        response = client.post("/api/register", json={"login": "weak", "password": "RawSecret"})
    records = [record for record in caplog.records if record.name == "lab4"]
    assert {record.message for record in records} >= {
        "registration_success", "registration_duplicate", "validation_failed"}
    assert {record.levelname for record in records} >= {"INFO", "ERROR"}
    serialized = " ".join(str(record.__dict__) for record in records)
    for secret in (PASSWORD, "RawSecret", "password_hash"):
        assert secret not in serialized
        assert secret not in response.text
