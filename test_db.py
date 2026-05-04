import asyncio
from app.db.session import SessionFactory
from sqlalchemy import text

async def main():
    async with SessionFactory() as session:
        try:
            em = "[0.1, 0.2, 0.3]"
            await session.execute(text("SELECT 1.0 / (1.0 + (pc.embedding <=> CAST(:embedding AS vector))) AS score FROM paper_chunks pc LIMIT 1"), {"embedding": em})
        except Exception as e:
            print("DB Error:", type(e), str(e))

asyncio.run(main())
