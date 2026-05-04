from __future__ import annotations

import httpx


class ChEBIClient:
    async def lookup(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            url = f"https://www.ebi.ac.uk/webservices/chebi/2.0/test/getLiteEntity?search={query}&searchCategory=ALL&maximumResults=5&stars=ALL"
            response = await client.get(url)
            return {"status_code": response.status_code, "text": response.text[:1000]}
