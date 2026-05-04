import asyncio
from app.db.session import SessionFactory
from app.modules.literature.service import LiteratureService

async def main():
    async with SessionFactory() as session:
        service = LiteratureService(session)
        res = await service.search("tenant_demo", "gefitinib", profile="high_recall")
        print(res)

asyncio.run(main())
