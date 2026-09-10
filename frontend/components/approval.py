from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def render_approval(
    approval_request: dict[str, Any],
    on_decision: Callable[..., None],
) -> None:
    """Render the human approval interface."""

    st.subheader("Human Approval Required")

    message = approval_request.get(
        "message",
        "Please review the generated output.",
    )

    st.warning(message)

    generated_output = approval_request.get(
        "generated_output",
        "",
    )

    st.markdown("### Generated Output")

    st.code(
        generated_output,
        language="markdown",
    )

    findings_count = approval_request.get(
        "findings_count",
        0,
    )

    st.caption(
        f"Based on {findings_count} finding(s)."
    )

    st.markdown("### Decision")

    approve_col, edit_col, reject_col = st.columns(3)

    with approve_col:
        if st.button(
            "Approve",
            type="primary",
            use_container_width=True,
        ):
            on_decision(
                decision="approve",
            )

    with edit_col:
        if st.button(
            "Edit",
            use_container_width=True,
        ):
            st.session_state["approval_edit_mode"] = True

    with reject_col:
        if st.button(
            "Reject",
            use_container_width=True,
        ):
            on_decision(
                decision="reject",
            )

    if st.session_state.get(
        "approval_edit_mode",
        False,
    ):
        st.markdown("### Edit Output")

        edited_output = st.text_area(
            "Modify the generated report:",
            value=generated_output,
            height=400,
            key="edited_output",
        )

        feedback = st.text_input(
            "Optional feedback:",
            key="edit_feedback",
        )

        col_submit, col_cancel = st.columns(2)

        with col_submit:
            if st.button(
                "Submit Edited Output",
                type="primary",
                use_container_width=True,
            ):
                if not edited_output.strip():
                    st.error(
                        "Edited output cannot be empty."
                    )
                else:
                    on_decision(
                        decision="edit",
                        edited_output=edited_output,
                        feedback=feedback or None,
                    )

        with col_cancel:
            if st.button(
                "Cancel Edit",
                use_container_width=True,
            ):
                st.session_state[
                    "approval_edit_mode"
                ] = False
                st.rerun()
