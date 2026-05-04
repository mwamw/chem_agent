from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolInvocation
from app.modules.tools.base import ToolContext, ToolDefinition, ToolResult


class ToolExecutor:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, tool: ToolDefinition, payload: dict, context: ToolContext) -> ToolResult:
        result = await tool.handler(payload, context)
        invocation = ToolInvocation(
            tenant_id=context.tenant_id,
            agent_run_id=context.run_id,
            tool_name=tool.name,
            input_json=payload,
            output_json={
                "content": result.content,
                "structured_data": result.structured_data,
                "metadata": result.metadata,
            },
            status=result.status,
        )
        self.session.add(invocation)
        await self.session.flush()
        return result
