from __future__ import annotations

from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    input: str


class AgentRunResponse(BaseModel):
    run_id: str
    trace_id: str
    answer: str
    actions: list[dict]
    citations: list[dict]
