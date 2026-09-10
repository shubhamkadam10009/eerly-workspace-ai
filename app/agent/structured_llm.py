from typing import Any

from langchain_openai import ChatOpenAI

from app.agent.llm import get_llm
from app.agent.models import FindingCollection, RequestAnalysis
from app.agent.prompts import (
    CONTENT_ANALYSIS_SYSTEM_PROMPT,
    CONTENT_ANALYSIS_USER_PROMPT_TEMPLATE,
    REPORT_GENERATION_SYSTEM_PROMPT,
    REPORT_GENERATION_USER_PROMPT_TEMPLATE,
    REQUEST_ANALYSIS_SYSTEM_PROMPT,
    REQUEST_ANALYSIS_USER_PROMPT_TEMPLATE,
)


def get_request_analysis_llm() -> Any:
    """Return an LLM configured for structured request analysis."""

    llm: ChatOpenAI = get_llm()

    return llm.with_structured_output(
        RequestAnalysis,
        method="json_schema",
        strict=True,
    )


def get_content_analysis_llm() -> Any:
    """Return an LLM configured for structured content analysis."""

    llm: ChatOpenAI = get_llm()

    return llm.with_structured_output(
        FindingCollection,
        method="json_schema",
        strict=True,
    )


def get_report_generation_llm() -> ChatOpenAI:
    """Return the configured LLM for report generation."""

    return get_llm()


def build_request_analysis_messages(
    request: str,
    available_skills: str,
) -> list[tuple[str, str]]:
    """Build messages for request analysis."""

    return [
        ("system", REQUEST_ANALYSIS_SYSTEM_PROMPT),
        (
            "human",
            REQUEST_ANALYSIS_USER_PROMPT_TEMPLATE.format(
                request=request,
                available_skills=available_skills,
            ),
        ),
    ]


def build_content_analysis_messages(
    request: str,
    skill_instructions: str,
    source_material: str,
) -> list[tuple[str, str]]:
    """Build messages for source-grounded content analysis."""

    return [
        ("system", CONTENT_ANALYSIS_SYSTEM_PROMPT),
        (
            "human",
            CONTENT_ANALYSIS_USER_PROMPT_TEMPLATE.format(
                request=request,
                skill_instructions=skill_instructions,
                source_material=source_material,
            ),
        ),
    ]


def build_report_generation_messages(
    request: str,
    skill_instructions: str,
    findings: str,
) -> list[tuple[str, str]]:
    """Build messages for report generation."""

    return [
        ("system", REPORT_GENERATION_SYSTEM_PROMPT),
        (
            "human",
            REPORT_GENERATION_USER_PROMPT_TEMPLATE.format(
                request=request,
                skill_instructions=skill_instructions,
                findings=findings,
            ),
        ),
    ]