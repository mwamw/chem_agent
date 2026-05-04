from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal, get_current_principal
from app.db.models import AgentRun, AgentStep
from app.db.session import get_db_session
from app.modules.agents.schemas import AgentRunRequest, AgentRunResponse
from app.modules.agents.service import AgentRunService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/{agent_id}/runs", response_model=AgentRunResponse)
async def run_agent(
    agent_id: str,
    payload: AgentRunRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRunResponse:
    run = await AgentRunService(session).run(
        agent_id,
        principal.tenant_id,
        principal.user.id,
        payload.input,
        principal.permissions,
    )
    await session.commit()
    return AgentRunResponse(
        run_id=run.id,
        trace_id=run.trace_id,
        answer=run.final_answer,
        actions=run.actions_json,
        citations=run.citations_json,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.tenant_id == principal.tenant_id)
    )
    run = result.scalar_one()
    return {
        "run_id": run.id,
        "trace_id": run.trace_id,
        "agent_id": run.agent_id,
        "input": run.input_text,
        "answer": run.final_answer,
        "actions": run.actions_json,
        "citations": run.citations_json,
        "status": run.status,
    }


@router.get("/runs/{run_id}/steps")
async def get_run_steps(
    run_id: str,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(AgentStep)
        .join(AgentRun, AgentRun.id == AgentStep.agent_run_id)
        .where(
            AgentRun.id == run_id,
            AgentRun.tenant_id == principal.tenant_id,
        )
        .order_by(AgentStep.step_index.asc())
    )
    steps = result.scalars().all()
    return [
        {
            "step_index": row.step_index,
            "step_type": row.step_type,
            "thought_summary": row.thought_summary,
            "tool_name": row.tool_name,
            "tool_input": row.tool_input,
            "tool_output": row.tool_output,
            "status": row.status,
        }
        for row in steps
    ]
