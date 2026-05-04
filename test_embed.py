import asyncio
from app.integrations.embedding_client import EmbeddingClient

async def main():
    try:
        client = EmbeddingClient()
        res = await client.embed_text("test")
        print("Dim:", len(res))
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(main())
