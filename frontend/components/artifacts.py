from __future__ import annotations

from typing import Any

import streamlit as st


def render_artifact(
    artifact: dict[str, Any] | None,
    generated_output: str | None,
    validation_result: dict[str, Any] | None,
) -> None:
    """Render the generated artifact and validation result."""

    if not artifact and not generated_output:
        return

    st.subheader("Generated Artifact")

    if artifact:
        filename = artifact.get(
            "filename",
            "artifact",
        )

        relative_path = artifact.get(
            "relative_path",
            "",
        )

        artifact_status = artifact.get(
            "status",
            "unknown",
        )

        st.success(
            f"Artifact status: {artifact_status}"
        )

        if relative_path:
            st.caption(
                f"Workspace path: {relative_path}"
            )

        st.markdown(f"**File:** `{filename}`")

    if validation_result:
        valid = validation_result.get(
            "valid",
            False,
        )

        issues = validation_result.get(
            "issues",
            [],
        )

        if valid:
            st.success(
                "Validation passed."
            )
        else:
            st.warning(
                "Validation reported issues."
            )

            for issue in issues:
                st.write(f"- {issue}")

    if generated_output:
        st.markdown("### Report")

        st.markdown(generated_output)

        st.download_button(
            label="Download Report",
            data=generated_output,
            file_name=(
                artifact.get("filename", "report.md")
                if artifact
                else "report.md"
            ),
            mime="text/markdown",
            use_container_width=True,
        )
