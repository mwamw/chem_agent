from __future__ import annotations

import hashlib
import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Permission, Role, User, UserRole
from app.db.session import get_db_session

password_hasher = PasswordHasher()


@dataclass(frozen=True)
class Principal:
    user: User
    tenant_id: str
    token_id: str
    roles: tuple[str, ...]
    permissions: frozenset[str]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _numeric_date(value: datetime) -> int:
    return calendar.timegm(value.utctimetuple())


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_jwt_token(
    *,
    subject: str,
    tenant_id: str,
    roles: list[str],
    token_use: str,
    expires_delta: timedelta,
    token_id: str | None = None,
) -> tuple[str, str, datetime]:
    settings = get_settings()
    issued_at = utcnow()
    expires_at = issued_at + expires_delta
    jwt_id = token_id or uuid4().hex
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": roles,
        "token_use": token_use,
        "iat": _numeric_date(issued_at),
        "nbf": _numeric_date(issued_at),
        "exp": _numeric_date(expires_at),
        "jti": jwt_id,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jwt_id, expires_at


def decode_jwt_token(token: str, expected_use: str = "access") -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    if payload.get("token_use") != expected_use:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token use")
    return payload


async def _load_role_context(
    session: AsyncSession, user_id: str
) -> tuple[tuple[str, ...], frozenset[str]]:
    result = await session.execute(
        select(Role.name, Permission.key)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(Permission, Permission.role_id == Role.id, isouter=True)
        .where(UserRole.user_id == user_id)
    )
    roles: set[str] = set()
    permissions: set[str] = set()
    for role_name, permission_key in result.all():
        roles.add(role_name)
        if permission_key:
            permissions.add(permission_key)
    return tuple(sorted(roles)), frozenset(permissions)


async def get_current_principal(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_jwt_token(token, expected_use="access")
    result = await session.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
    if user.tenant_id != payload.get("tenant_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant mismatch")
    roles, permissions = await _load_role_context(session, user.id)
    return Principal(
        user=user,
        tenant_id=user.tenant_id,
        token_id=str(payload["jti"]),
        roles=roles,
        permissions=permissions,
    )


async def get_current_user(principal: Principal = Depends(get_current_principal)) -> User:
    return principal.user


def require_permission(permission_key: str):
    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if "*" not in principal.permissions and permission_key not in principal.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return principal

    return dependency


def has_permission(permissions: frozenset[str], permission_key: str) -> bool:
    return "*" in permissions or permission_key in permissions
