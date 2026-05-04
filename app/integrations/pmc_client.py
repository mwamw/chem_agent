from __future__ import annotations

import httpx


class PMCClient:
    async def fetch_article(self, pmcid: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/"
            response = await client.get(url)
            return response.text[:1000]
