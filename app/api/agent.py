from fastapi import APIRouter, Depends

from app.agent.service import run_agent
from app.auth.dependencies import get_current_user_id
from app.schemas.agent import AgentRunRequest, AgentRunResponse


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

    thread_id = result["thread_id"]

    if payload.thread_id:
        thread_id = payload.thread_id

    return AgentRunResponse(
        thread_id=thread_id,
        status=result["status"],
        selected_skills=result["selected_skills"],
        findings=result["findings"],
        generated_output=result["generated_output"],
        validation_result=result["validation_result"],
    )