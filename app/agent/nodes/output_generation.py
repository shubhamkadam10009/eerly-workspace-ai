from app.agent.state import AgentState
from app.agent.structured_llm import (
    build_report_generation_messages,
    get_report_generation_llm,
)


def _response_to_text(response: object) -> str:
    content = getattr(response, "content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))

        return "\n".join(parts).strip()

    return str(content).strip()


def generate_output(state: AgentState) -> dict:
    """Generate the requested report content from validated findings."""

    skill_instructions = "\n\n".join(
        f"## {name}\n{instructions}"
        for name, instructions in state["loaded_skills"].items()
    )

    finding_lines: list[str] = []

    for finding in state["findings"]:
        confidence = finding["confidence"]
        statement = finding["statement"]
        source_path = finding["source_path"]

        finding_lines.append(
            f"- [{confidence}] "
            f"{statement} "
            f"(source: {source_path})"
        )

    findings = "\n".join(finding_lines)

    messages = build_report_generation_messages(
        request=state["request"],
        skill_instructions=skill_instructions,
        findings=findings,
    )

    response = get_report_generation_llm().invoke(messages)
    generated_output = _response_to_text(response)

    return {
        "generated_output": generated_output,
        "status": "output_generated",
        "error": None,
    }
