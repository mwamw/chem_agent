from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.models import Compound, CompoundSynonym, Tenant
from app.db.session import SessionFactory, init_db


async def main() -> None:
    await init_db()
    settings = get_settings()
    compounds = json.loads(Path("data/seeds/chemicals/compounds.json").read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        tenant = Tenant(id=settings.default_tenant_id, name=settings.default_tenant_id)
        await session.merge(tenant)
        for row in compounds:
            compound = Compound(
                id=row["id"],
                tenant_id=settings.default_tenant_id,
                primary_name=row["primary_name"],
                smiles=row.get("smiles"),
                inchi=row.get("inchi"),
                molecular_formula=row.get("molecular_formula"),
                molecular_weight=row.get("molecular_weight"),
                summary=row.get("summary", ""),
                properties_json=row.get("properties_json", {}),
                source_name="seed_pubchem",
            )
            await session.merge(compound)
            for synonym in row.get("synonyms", []):
                await session.merge(CompoundSynonym(compound_id=row["id"], synonym=synonym))
        await session.commit()
    print("Seeded compounds.")


if __name__ == "__main__":
    asyncio.run(main())
