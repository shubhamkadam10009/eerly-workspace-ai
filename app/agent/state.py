from typing import TypedDict


class AgentState(TypedDict):
    user_id: str
    thread_id: str
    request: str

    request_analysis: dict | None

    discovered_skills: list[dict]
    selected_skills: list[str]
    loaded_skills: dict[str, str]

    workspace_files: list[dict]
    source_contents: dict[str, str]

    findings: list[dict]

    generated_output: str | None
    generated_artifact: dict | None

    validation_result: dict | None

    approval_request: dict | None
    approval_status: str | None
    approval_decision: str | None
    approval_feedback: str | None

    status: str
    error: str | None
