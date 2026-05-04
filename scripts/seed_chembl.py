from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.models import Bioactivity
from app.db.session import SessionFactory, init_db


async def main() -> None:
    await init_db()
    settings = get_settings()
    rows = json.loads(Path("data/seeds/chemicals/bioactivities.json").read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        for row in rows:
            await session.merge(
                Bioactivity(
                    id=row["id"],
                    tenant_id=settings.default_tenant_id,
                    compound_id=row["compound_id"],
                    target_id=row["target_id"],
                    activity_type=row["activity_type"],
                    activity_value=row["activity_value"],
                    activity_unit=row["activity_unit"],
                    evidence_summary=row["evidence_summary"],
                )
            )
        await session.commit()
    print("Seeded bioactivities.")


if __name__ == "__main__":
    asyncio.run(main())
