from app.agent.models import ValidationResult
from app.agent.state import AgentState


def validate_output(state: AgentState) -> dict:
    """Validate generated output before human approval."""

    issues: list[str] = []

    generated_output = state["generated_output"]

    if not generated_output or not generated_output.strip():
        issues.append("Generated output is empty")

    if state["source_contents"] and not state["findings"]:
        issues.append(
            "Source files were available but no source-grounded findings were produced"
        )

    if generated_output and len(generated_output.strip()) < 20:
        issues.append("Generated output is unexpectedly short")

    result = ValidationResult(
        valid=not issues,
        issues=issues,
    )

    return {
        "validation_result": result.model_dump(),
        "status": (
            "output_validated"
            if result.valid
            else "output_validation_failed"
        ),
        "error": None if result.valid else "; ".join(issues),
    }
