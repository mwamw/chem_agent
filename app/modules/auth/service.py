from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models import Tenant, User


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, username: str, display_name: str | None = None) -> dict:
        settings = get_settings()
        tenant = await self._get_or_create_tenant(settings.default_tenant_id)
        result = await self.session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                username=username,
                display_name=display_name or username,
            )
            self.session.add(user)
            await self.session.flush()
        token = create_access_token(subject=user.id, tenant_id=user.tenant_id)
        return {"access_token": token, "user_id": user.id, "tenant_id": user.tenant_id}

    async def _get_or_create_tenant(self, tenant_name: str) -> Tenant:
        result = await self.session.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=tenant_name)
            self.session.add(tenant)
            await self.session.flush()
        return tenant
