from __future__ import annotations

import asyncio
import json
from queue import Empty

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.event_bus import event_bus
from app.agent.service import (
    _effective_thread_id,
    resume_agent,
    run_agent,
)
from app.auth.dependencies import get_current_user_id
from app.schemas.agent import (
    AgentResumeRequest,
    AgentResumeResponse,
    AgentRunRequest,
    AgentRunResponse,
)


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


@router.post("/run", response_model=AgentRunResponse)
def run_workspace_agent(
    payload: AgentRunRequest,
    user_id: str = Depends(get_current_user_id),
) -> AgentRunResponse:
    """Run the Workspace Consultant for the authenticated user."""

    result = run_agent(
        user_id=user_id,
        request=payload.request,
        thread_id=payload.thread_id,
    )

    return AgentRunResponse(
        thread_id=result["thread_id"],
        status=result["status"],
        selected_skills=result["selected_skills"],
        findings=result["findings"],
        generated_output=result["generated_output"],
        validation_result=result["validation_result"],
        approval_required=result.get("approval_required", False),
        approval_request=result.get("approval_request"),
        approval_decision=result.get("approval_decision"),
        approval_feedback=result.get("approval_feedback"),
    )


@router.post("/resume", response_model=AgentResumeResponse)
def resume_workspace_agent(
    payload: AgentResumeRequest,
    user_id: str = Depends(get_current_user_id),
) -> AgentResumeResponse:
    """Resume an interrupted Workspace Consultant execution."""

    result = resume_agent(
        user_id=user_id,
        thread_id=payload.thread_id,
        decision=payload.decision,
    )

    return AgentResumeResponse(
        thread_id=result["thread_id"],
        status=result["status"],
        approval_required=result.get("approval_required", False),
        approval_request=result.get("approval_request"),
        approval_decision=result.get("approval_decision"),
        generated_output=result["generated_output"],
        validation_result=result["validation_result"],
    )


@router.get("/stream/{thread_id}")
async def stream_agent_events(
    thread_id: str,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """Stream live progress events for the authenticated user's run."""

    if not thread_id or not thread_id.strip():
        raise ValueError("thread_id is required")

    stream_key = _effective_thread_id(
        user_id,
        thread_id,
    )

    async def event_generator():
        queue = event_bus.subscribe(stream_key)

        try:
            while True:
                try:
                    event = await asyncio.to_thread(
                        queue.get,
                        True,
                        15.0,
                    )

                except Empty:
                    yield ": heartbeat\n\n"
                    continue

                payload = event.model_dump(mode="json")

                yield (
                    f"event: {event.event}\n"
                    f"data: {json.dumps(payload)}\n\n"
                )

                if event.event in {
                    "completed",
                    "rejected",
                    "failed",
                }:
                    break

        finally:
            event_bus.unsubscribe(
                stream_key,
                queue,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
