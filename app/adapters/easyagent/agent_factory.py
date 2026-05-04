from __future__ import annotations

from app.modules.agents.service import AgentRunService


def build_agent_runtime(session):
    return AgentRunService(session)
