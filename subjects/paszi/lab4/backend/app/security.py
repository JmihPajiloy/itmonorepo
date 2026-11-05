from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

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


def issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=settings.token_ttl_minutes),
         "iss": "paszi-lab4", "aud": "paszi-lab4"},
        settings.secret_key, algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    error = HTTPException(401, "Требуется вход в систему", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=["HS256"],
            issuer="paszi-lab4", audience="paszi-lab4", options={"require": ["sub", "exp", "iat"]},
        )
        user = db.get(User, int(payload["sub"]))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise error
    if user is None:
        raise error
    return user
