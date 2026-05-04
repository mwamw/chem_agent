from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_token,
    utcnow,
    verify_password,
)
from app.db.models import RefreshToken, Tenant, User


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, username: str, password: str) -> dict:
        user = await self._load_user(username)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        roles = await self._load_roles(user.id)
        tokens = await self._issue_tokens(user, roles)
        user.last_login_at = utcnow()
        await self.session.flush()
        return tokens

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_jwt_token(refresh_token, expected_use="refresh")
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.jwt_id == payload["jti"],
                RefreshToken.token_hash == hash_token(refresh_token),
            )
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked_at is not None or stored.expires_at < utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        user_result = await self.session.execute(select(User).where(User.id == stored.user_id))
        user = user_result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
        roles = await self._load_roles(user.id)
        tokens = await self._issue_tokens(user, roles)
        stored.revoked_at = utcnow()
        stored.replaced_by_token_id = tokens["refresh_token_id"]
        await self.session.flush()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_jwt_token(refresh_token, expected_use="refresh")
        except HTTPException:
            return
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.jwt_id == payload["jti"])
        )
        stored = result.scalar_one_or_none()
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow()
            await self.session.flush()

    async def _load_user(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def _load_roles(self, user_id: str) -> list[str]:
        from app.db.models import Role, UserRole

        result = await self.session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return sorted({row[0] for row in result.all()})

    async def _issue_tokens(self, user: User, roles: list[str]) -> dict:
        settings = get_settings()
        access_token, _, access_expires_at = create_jwt_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=roles,
            token_use="access",
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        )
        refresh_token, refresh_jti, refresh_expires_at = create_jwt_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=roles,
            token_use="refresh",
            expires_delta=timedelta(days=settings.jwt_refresh_expire_days),
        )
        stored = RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            jwt_id=refresh_jti,
            expires_at=refresh_expires_at,
        )
        self.session.add(stored)
        await self.session.flush()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "refresh_token_id": stored.id,
            "expires_in": int((access_expires_at - utcnow()).total_seconds()),
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "roles": roles,
        }

    async def get_or_create_tenant(self, tenant_name: str) -> Tenant:
        result = await self.session.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=tenant_name, name=tenant_name)
            self.session.add(tenant)
            await self.session.flush()
        return tenant
