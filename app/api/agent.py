from fastapi import APIRouter, Depends

from app.agent.service import resume_agent, run_agent
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