import jwt
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from app.config import settings


def grant(client, owner, resource_id, **rights):
    return client.put(f"/api/resources/{resource_id}/permissions/reader", headers=owner, json=rights)


def test_owner_has_all_rights(client, scenario):
    owner, _, _, rid = scenario
    assert client.get(f"/api/resources/{rid}", headers=owner).status_code == 200
    assert client.patch(f"/api/resources/{rid}", headers=owner,
                        json={"title": "Изменено", "content": "Новая версия"}).status_code == 200
    assert client.delete(f"/api/resources/{rid}", headers=owner).status_code == 204
    assert client.get(f"/api/resources/{rid}", headers=owner).status_code == 404


def test_owner_grants_reader_and_outsider_is_denied(client, scenario):
    owner, reader, outsider, rid = scenario
    assert grant(client, owner, rid, can_read=True).status_code == 200
    assert client.get(f"/api/resources/{rid}", headers=reader).json()["content"] == "Защищённое содержимое"
    denied = client.get(f"/api/resources/{rid}", headers=outsider)
    assert denied.status_code == 403 and "Защищённое содержимое" not in denied.text
    assert client.get("/api/resources", headers=outsider).json() == []


@pytest.mark.parametrize("allowed", ["read", "update", "delete"])
def test_permissions_are_independent(client, scenario, allowed):
    owner, reader, _, rid = scenario
    assert grant(client, owner, rid, **{"can_" + allowed: True}).status_code == 200
    expected = lambda action: 200 if action == allowed else 403
    assert client.get(f"/api/resources/{rid}", headers=reader).status_code == expected("read")
    assert client.patch(f"/api/resources/{rid}", headers=reader,
                        json={"title": "Заменено", "content": "Обновлённое содержимое"}).status_code == expected("update")
    result = client.delete(f"/api/resources/{rid}", headers=reader)
    assert result.status_code == (204 if allowed == "delete" else 403)


def test_nonowner_cannot_manage_permissions_even_with_all_rights(client, scenario):
    owner, reader, outsider, rid = scenario
    grant(client, owner, rid, can_read=True, can_update=True, can_delete=True)
    for auth in (reader, outsider):
        assert client.put(f"/api/resources/{rid}/permissions/outsider", headers=auth,
                          json={"can_read": True}).status_code == 403
        assert client.delete(f"/api/resources/{rid}/permissions/reader", headers=auth).status_code == 403
        assert client.get(f"/api/resources/{rid}/permissions", headers=auth).status_code == 403


def test_revocation_takes_effect_for_existing_token(client, scenario):
    owner, reader, _, rid = scenario
    grant(client, owner, rid, can_read=True)
    assert client.get(f"/api/resources/{rid}", headers=reader).status_code == 200
    assert client.delete(f"/api/resources/{rid}/permissions/reader", headers=owner).status_code == 204
    assert client.get(f"/api/resources/{rid}", headers=reader).status_code == 403


def test_grant_is_upsert_and_false_revokes(client, scenario, database):
    owner, reader, _, rid = scenario
    grant(client, owner, rid, can_read=True)
    grant(client, owner, rid, can_update=True)
    assert client.get(f"/api/resources/{rid}", headers=reader).status_code == 403
    with database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM resource_permissions")) == 1
    grant(client, owner, rid)
    assert client.get("/api/resources", headers=reader).json() == []


def test_delete_cascades_permissions(client, scenario, database):
    owner, _, _, rid = scenario
    grant(client, owner, rid, can_read=True)
    assert client.delete(f"/api/resources/{rid}", headers=owner).status_code == 204
    with database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM resource_permissions")) == 0


def test_cannot_forge_owner_or_request_extra_fields(client, scenario):
    owner, _, outsider, rid = scenario
    assert client.post("/api/resources", headers=outsider,
                       json={"title": "Подмена", "content": "Текст", "owner_id": 1}).status_code == 422
    assert client.patch(f"/api/resources/{rid}", headers=owner,
                        json={"title": "Подмена", "content": "Текст", "owner_id": 2}).status_code == 422


def test_all_resource_routes_require_authentication(client, scenario):
    _, _, _, rid = scenario
    assert client.get("/api/resources").status_code == 401
    assert client.get(f"/api/resources/{rid}").status_code == 401
    assert client.post("/api/resources", json={"title": "Текст", "content": "Текст"}).status_code == 401
    assert client.patch(f"/api/resources/{rid}", json={"title": "Текст", "content": "Текст"}).status_code == 401
    assert client.delete(f"/api/resources/{rid}").status_code == 401
    assert client.put(f"/api/resources/{rid}/permissions/reader", json={"can_read": True}).status_code == 401


def test_expired_and_wrongly_signed_tokens(client, scenario):
    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1),
               "iss": "paszi-lab4", "aud": "paszi-lab4"}
    expired = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    assert client.get("/api/resources", headers={"Authorization": "Bearer " + expired}).status_code == 401
    payload["exp"] = now + timedelta(hours=1)
    forged = jwt.encode(payload, "wrong-key-" * 8, algorithm="HS256")
    assert client.get("/api/resources", headers={"Authorization": "Bearer " + forged}).status_code == 401


def test_no_content_in_resource_list_and_no_rights_in_token(client, scenario):
    owner, reader, _, rid = scenario
    grant(client, owner, rid, can_update=True)
    rows = client.get("/api/resources", headers=reader).json()
    assert len(rows) == 1 and "content" not in rows[0]
    assert not rows[0]["can_read"] and rows[0]["can_update"]
    payload = jwt.decode(reader["Authorization"].split()[1], settings.secret_key, algorithms=["HS256"],
                         issuer="paszi-lab4", audience="paszi-lab4")
    assert not ({"can_read", "can_update", "can_delete", "owner_id"} & payload.keys())
