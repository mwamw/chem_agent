from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.models import Target, Tenant
from app.db.session import SessionFactory, init_db


async def main() -> None:
    await init_db()
    settings = get_settings()
    targets = json.loads(Path("data/seeds/chemicals/targets.json").read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        await session.merge(Tenant(id=settings.default_tenant_id, name=settings.default_tenant_id))
        for row in targets:
            await session.merge(
                Target(
                    id=row["id"],
                    tenant_id=settings.default_tenant_id,
                    symbol=row["symbol"],
                    full_name=row["full_name"],
                    organism=row["organism"],
                    summary=row["summary"],
                    source_name="seed_chebi",
                )
            )
        await session.commit()
    print("Seeded targets.")


if __name__ == "__main__":
    asyncio.run(main())
