from __future__ import annotations

from typing import Any

import streamlit as st


EVENT_LABELS: dict[str, str] = {
    "request_received": "Request received",
    "request_analyzed": "Request analyzed",
    "skills_discovered": "Skills discovered",
    "skills_loaded": "Skills loaded",
    "workspace_inspected": "Workspace inspected",
    "sources_read": "Sources read",
    "analysis_completed": "Analysis completed",
    "output_generated": "Output generated",
    "validation_completed": "Output validated",
    "approval_required": "Waiting for approval",
    "approval_received": "Approval received",
    "artifact_delivered": "Artifact delivered",
    "completed": "Completed",
    "rejected": "Rejected",
    "failed": "Failed",
}


def render_progress(events: list[dict[str, Any]]) -> None:
    """Render the agent execution timeline."""

    st.subheader("Agent Progress")

    if not events:
        st.info("Waiting for agent activity...")
        return

    for event in events:
        event_type = event.get("event", "unknown")
        label = EVENT_LABELS.get(
            event_type,
            event_type.replace("_", " ").title(),
        )

        status = event.get("status", "")
        message = event.get("message", "")

        if event_type == "failed":
            st.error(f"❌ {label}: {message}")

        elif event_type == "rejected":
            st.warning(f"⚠️ {label}: {message}")

        elif event_type == "completed":
            st.success(f"✅ {label}: {message}")

        elif event_type == "approval_required":
            st.warning(f"⏸️ {label}: {message}")

        else:
            st.write(f"**{label}** — {message}")

        if status:
            st.caption(f"Status: {status}")


def render_current_progress(
    event: dict[str, Any] | None,
) -> None:
    """Render the latest progress event."""

    if not event:
        return

    event_type = event.get("event", "unknown")
    label = EVENT_LABELS.get(
        event_type,
        event_type.replace("_", " ").title(),
    )
    message = event.get("message", "")

    st.info(f"**{label}** — {message}")
