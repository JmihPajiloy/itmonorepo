from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import AuthSession, User

hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
    salt_len=16,
    hash_len=32,
    type=Type.ID,
)
dummy_hash = hasher.hash("dummy-value-never-used-as-a-password")
bearer = HTTPBearer(auto_error=False)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except VerificationError:
        return False


ACCESS_COOKIE = "lab4_access"
REFRESH_COOKIE = "lab4_refresh"
ACCESS_PATH = "/api"
REFRESH_PATH = "/api/auth"
REFRESH_TTL = timedelta(days=7)
COOKIE_OPTIONS = {"httponly": True, "secure": settings.app_env == "production", "samesite": "strict"}


def issue_token(user: User, session_id: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=settings.token_ttl_minutes),
         "iss": "paszi-lab4", "aud": "paszi-lab4", **({"sid": session_id} if session_id else {})},
        settings.secret_key, algorithm="HS256",
    )


def unauthorized():
    return HTTPException(401, "Требуется вход в систему", headers={"WWW-Authenticate": "Bearer"})


def refresh_digest(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def set_access_cookie(response: Response, user: User, session: AuthSession):
    response.set_cookie(ACCESS_COOKIE, issue_token(user, session.id), path=ACCESS_PATH,
                        max_age=settings.token_ttl_minutes * 60, **COOKIE_OPTIONS)


def start_session(response: Response, user: User, db: Session):
    refresh_token = token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now))
    session = AuthSession(id=uuid4().hex, user_id=user.id, refresh_hash=refresh_digest(refresh_token),
                          expires_at=now + REFRESH_TTL)
    db.add(session)
    db.commit()
    set_access_cookie(response, user, session)
    response.set_cookie(REFRESH_COOKIE, refresh_token, path=REFRESH_PATH,
                        max_age=int(REFRESH_TTL.total_seconds()), **COOKIE_OPTIONS)


def refresh_session(request: Request, response: Response, db: Session):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise unauthorized()
    session = db.scalar(select(AuthSession).where(
        AuthSession.refresh_hash == refresh_digest(token),
        AuthSession.expires_at > datetime.now(timezone.utc),
    ))
    if session is None:
        raise unauthorized()
    user = db.get(User, session.user_id)
    if user is None:
        raise unauthorized()
    set_access_cookie(response, user, session)


def end_session(request: Request, db: Session):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.refresh_hash == refresh_digest(token)))


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise unauthorized()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=["HS256"],
            issuer="paszi-lab4", audience="paszi-lab4", options={"require": ["sub", "exp", "iat"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized()
    session_id = payload.get("sid")
    if session_id or credentials is None:
        session = db.get(AuthSession, session_id) if session_id else None
        if session is None or session.user_id != user_id or session.expires_at <= datetime.now(timezone.utc):
            raise unauthorized()
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user
