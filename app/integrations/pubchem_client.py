from __future__ import annotations

import httpx


class PubChemClient:
    async def fetch_compound_summary(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChI/JSON"
            response = await client.get(url)
            if response.status_code != 200:
                return {"query": query, "found": False}
            return response.json()
