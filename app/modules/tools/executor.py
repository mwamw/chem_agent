from __future__ import annotations

import asyncio
from time import perf_counter

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import has_permission
from app.db.models import ToolInvocation
from app.modules.tools.base import ToolContext, ToolDefinition, ToolResult


class ToolExecutor:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(
        self,
        tool: ToolDefinition,
        payload: dict,
        context: ToolContext,
        timeout_seconds: int | None = None,
    ) -> ToolResult:
        if not has_permission(context.permissions, tool.permission_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Tool permission denied: {tool.name}"
            )
        validated_payload = payload
        if tool.input_model is not None:
            validated_payload = tool.input_model.model_validate(payload).model_dump(
                exclude_none=True
            )
        started = perf_counter()
        try:
            result = await asyncio.wait_for(
                tool.handler(validated_payload, context),
                timeout=timeout_seconds or tool.timeout_seconds,
            )
            status_value = result.status
            error_message = None
        except Exception as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            await self.session.rollback()
            error_message = str(exc) or type(exc).__name__
            invocation = ToolInvocation(
                tenant_id=context.tenant_id,
                agent_run_id=context.run_id,
                tool_name=tool.name,
                input_json=validated_payload,
                output_json={},
                status="failed",
                error_message=error_message,
                latency_ms=latency_ms,
            )
            self.session.add(invocation)
            await self.session.commit()
            if isinstance(exc, asyncio.TimeoutError):
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Tool timed out: {tool.name}",
                ) from exc
            raise
        latency_ms = int((perf_counter() - started) * 1000)
        invocation = ToolInvocation(
            tenant_id=context.tenant_id,
            agent_run_id=context.run_id,
            tool_name=tool.name,
            input_json=validated_payload,
            output_json={
                "content": result.content,
                "structured_data": result.structured_data,
                "metadata": result.metadata,
            },
            status=status_value,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self.session.add(invocation)
        await self.session.commit()
        return result
