from __future__ import annotations

import httpx


class PubMedClient:
    async def search(self, query: str, retmax: int = 5) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            response = await client.get(url, params={"db": "pubmed", "retmode": "json", "term": query, "retmax": retmax})
            if response.status_code != 200:
                return {"query": query, "ids": []}
            return response.json()
