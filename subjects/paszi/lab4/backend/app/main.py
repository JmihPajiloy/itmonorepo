from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import and_, exists, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .db import get_db
from .logging_config import event
from .models import Resource, ResourcePermission, User
from .schemas import Credentials, PermissionInput, Registration, ResourceInput
from .security import current_user, dummy_hash, hasher, issue_token, verify_password

app = FastAPI(title="ПАСЗИ · Дискреционный доступ", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Стандартное представление ошибок Pydantic может содержать сырой input.
    fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
    event("validation_failed", error=True, method=request.method, fields=fields)
    return JSONResponse(status_code=422, content={
        "message": "Проверьте данные: логин 3–32 символа (A–Z, a–z, 0–9, ., _, -); "
                   "пароль 8–128 символов, заглавная и строчная латинские буквы, цифра и спецсимвол. "
                   "Название и содержимое ресурса не могут быть пустыми.",
        "fields": fields,
    })


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail}, headers=exc.headers)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    event("database_error", error=True, method=request.method)
    return JSONResponse(status_code=503, content={"message": "База данных временно недоступна"})


def public_user(user: User):
    return {"id": user.id, "login": user.login, "created_at": user.created_at}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/api/register", status_code=201)
def register(body: Registration, db: Session = Depends(get_db)):
    user = User(login=body.login, password_hash=hasher.hash(body.password.get_secret_value()))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        event("registration_duplicate", login=body.login)
        raise HTTPException(409, "Этот логин уже занят")
    event("registration_success", user_id=user.id, login=user.login)
    return {"message": "Пользователь создан. Теперь войдите в систему.", "user": public_user(user)}


@app.post("/api/login")
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == body.login))
    valid = verify_password(body.password.get_secret_value(), user.password_hash if user else dummy_hash)
    if not valid or user is None:
        event("login_failed")
        raise HTTPException(401, "Неверный логин или пароль")
    event("login_success", user_id=user.id)
    return {"access_token": issue_token(user), "token_type": "bearer", "user": public_user(user)}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return public_user(user)


def resource_for(db: Session, resource_id: int, user: User, action: str, *, lock=False):
    statement = select(Resource).where(Resource.id == resource_id)
    if lock:
        statement = statement.with_for_update()
    resource = db.scalar(statement)
    if resource is None:
        raise HTTPException(404, "Ресурс не найден")
    if resource.owner_id == user.id:
        return resource
    permission = db.get(ResourcePermission, (user.id, resource.id))
    if action == "manage" or permission is None or not getattr(permission, "can_" + action):
        event("access_denied", user_id=user.id, resource_id=resource.id, action=action)
        raise HTTPException(403, "Доступ запрещён: владелец не выдал это право")
    return resource


def metadata(db: Session, resource: Resource, user: User):
    owner = resource.owner_id == user.id
    p = db.get(ResourcePermission, (user.id, resource.id))
    return {"id": resource.id, "title": resource.title, "owner_id": resource.owner_id,
            "is_owner": owner, "can_read": owner or bool(p and p.can_read),
            "can_update": owner or bool(p and p.can_update),
            "can_delete": owner or bool(p and p.can_delete)}


@app.get("/api/resources")
def resources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    granted = exists().where(and_(
        ResourcePermission.resource_id == Resource.id, ResourcePermission.user_id == user.id,
        or_(ResourcePermission.can_read, ResourcePermission.can_update, ResourcePermission.can_delete),
    ))
    rows = db.scalars(select(Resource).where(or_(Resource.owner_id == user.id, granted)).order_by(Resource.id))
    # Только метаданные доступных объектов. Содержимое выдаёт отдельная проверка can_read.
    return [metadata(db, resource, user) for resource in rows]


@app.post("/api/resources", status_code=201)
def create_resource(body: ResourceInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource = Resource(owner_id=user.id, **body.model_dump())
    db.add(resource)
    db.commit()
    event("resource_created", user_id=user.id, resource_id=resource.id)
    return {**metadata(db, resource, user), "content": resource.content}


@app.get("/api/resources/{resource_id}")
def read_resource(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource = resource_for(db, resource_id, user, "read")
    return {**metadata(db, resource, user), "content": resource.content}


@app.patch("/api/resources/{resource_id}")
def update_resource(resource_id: int, body: ResourceInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource = resource_for(db, resource_id, user, "update", lock=True)
    resource.title, resource.content = body.title, body.content
    db.commit()
    event("resource_updated", user_id=user.id, resource_id=resource.id)
    # Право изменения само по себе не предоставляет чтение.
    return {"message": "Ресурс изменён", "id": resource.id}


@app.delete("/api/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource = resource_for(db, resource_id, user, "delete", lock=True)
    db.delete(resource)
    db.commit()
    event("resource_deleted", user_id=user.id, resource_id=resource_id)
    return Response(status_code=204)


@app.get("/api/resources/{resource_id}/permissions")
def permissions(resource_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource_for(db, resource_id, user, "manage")
    rows = db.execute(select(ResourcePermission, User.login).join(User).where(
        ResourcePermission.resource_id == resource_id).order_by(User.login))
    return [{"login": login, "can_read": p.can_read, "can_update": p.can_update,
             "can_delete": p.can_delete} for p, login in rows]


@app.put("/api/resources/{resource_id}/permissions/{target_login}")
def grant(resource_id: int, target_login: str, body: PermissionInput,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource_for(db, resource_id, user, "manage", lock=True)
    target = db.scalar(select(User).where(User.login == target_login))
    if target is None:
        raise HTTPException(404, "Получатель прав не найден")
    if target.id == user.id:
        raise HTTPException(409, "Владелец уже имеет все права на свой ресурс")
    values = body.model_dump()
    db.execute(insert(ResourcePermission).values(user_id=target.id, resource_id=resource_id, **values)
               .on_conflict_do_update(index_elements=["user_id", "resource_id"], set_=values))
    db.commit()
    event("permissions_changed", user_id=user.id, target_id=target.id, resource_id=resource_id, **values)
    return {"message": "Права сохранены", "login": target.login, **values}


@app.delete("/api/resources/{resource_id}/permissions/{target_login}", status_code=204)
def revoke(resource_id: int, target_login: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    resource_for(db, resource_id, user, "manage", lock=True)
    target = db.scalar(select(User).where(User.login == target_login))
    if target is None:
        raise HTTPException(404, "Получатель прав не найден")
    permission = db.get(ResourcePermission, (target.id, resource_id))
    if permission:
        db.delete(permission)
        db.commit()
    event("permissions_revoked", user_id=user.id, target_id=target.id, resource_id=resource_id)
    return Response(status_code=204)
