from __future__ import annotations

from pydantic import BaseModel


class TargetSearchRequest(BaseModel):
    query: str


class TargetResponse(BaseModel):
    id: str
    symbol: str
    full_name: str
    organism: str
    summary: str
