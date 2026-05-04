from __future__ import annotations

import httpx


class ChEMBLClient:
    async def search_target(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            url = "https://www.ebi.ac.uk/chembl/api/data/target/search.json"
            response = await client.get(url, params={"q": query})
            if response.status_code != 200:
                return {"query": query, "found": False}
            return response.json()
