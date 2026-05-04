from __future__ import annotations

from pydantic import BaseModel


class CompoundResolveRequest(BaseModel):
    query: str


class CompoundResponse(BaseModel):
    id: str
    primary_name: str
    smiles: str | None = None
    inchi: str | None = None
    molecular_formula: str | None = None
    molecular_weight: float | None = None
    summary: str
    properties: dict
    synonyms: list[str]
