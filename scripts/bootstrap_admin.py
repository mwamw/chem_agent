from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Permission, Role, Tenant, User, UserRole
from app.db.session import SessionFactory

DEFAULT_PERMISSIONS = [
    "*",
    "tool:compound:resolve",
    "tool:compound:get",
    "tool:target:search",
    "tool:target:get",
    "tool:bioactivity:search",
    "tool:literature:search",
    "tool:report:generate",
]


async def bootstrap(username: str, password: str, email: str | None, tenant_id: str) -> None:
    async with SessionFactory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=tenant_id, name=tenant_id)
            session.add(tenant)
            await session.flush()

        user_result = await session.execute(select(User).where(User.username == username))
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                username=username,
                email=email,
                password_hash=hash_password(password),
                display_name=username,
            )
            session.add(user)
            await session.flush()
        else:
            user.email = email or user.email
            user.password_hash = hash_password(password)

        role_result = await session.execute(
            select(Role).where(Role.tenant_id == tenant.id, Role.name == "admin")
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(tenant_id=tenant.id, name="admin")
            session.add(role)
            await session.flush()

        for permission_key in DEFAULT_PERMISSIONS:
            existing = await session.execute(
                select(Permission).where(
                    Permission.role_id == role.id, Permission.key == permission_key
                )
            )
            if existing.scalar_one_or_none() is None:
                session.add(Permission(role_id=role.id, key=permission_key))

        link_result = await session.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if link_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        print(f"Bootstrapped admin user '{username}' in tenant '{tenant.id}'.")


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Create or update the local ChemIntel admin user.")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--email", default=None)
    parser.add_argument("--tenant-id", default=settings.default_tenant_id)
    args = parser.parse_args()
    asyncio.run(bootstrap(args.username, args.password, args.email, args.tenant_id))


if __name__ == "__main__":
    main()
