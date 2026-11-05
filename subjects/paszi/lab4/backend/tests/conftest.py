"""Тесты на настоящем PostgreSQL в отдельной случайной схеме, без очистки данных приложения."""
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import get_db
from app.main import app


@pytest.fixture(scope="session")
def database():
    schema = "lab4_test_" + uuid.uuid4().hex
    admin = create_engine(settings.database_url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(settings.database_url, connect_args={"options": f"-csearch_path={schema}"})
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            # Схема миграции должна совпадать с ORM; проверяем и обратимость.
            command.check(config)
            command.downgrade(config, "base")
            command.upgrade(config, "head")
        yield engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture()
def client(database):
    with database.begin() as connection:
        connection.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    session_factory = sessionmaker(bind=database, expire_on_commit=False)

    def test_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


PASSWORD = "Lab4-DemoPass1!"


def account(client, login):
    response = client.post("/api/register", json={"login": login, "password": PASSWORD})
    assert response.status_code == 201, response.text
    response = client.post("/api/login", json={"login": login, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture()
def scenario(client):
    owner = account(client, "owner")
    reader = account(client, "reader")
    outsider = account(client, "outsider")
    response = client.post("/api/resources", headers=owner,
                           json={"title": "Учебный документ", "content": "Защищённое содержимое"})
    assert response.status_code == 201
    return owner, reader, outsider, response.json()["id"]
