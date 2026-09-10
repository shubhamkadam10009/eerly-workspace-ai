from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import streamlit as st

from frontend.api.client import APIClientError, EerlyAPIClient
from frontend.components.approval import render_approval
from frontend.components.artifacts import render_artifact
from frontend.components.progress import render_progress


st.set_page_config(
    page_title="Eerly Workspace AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    """Load the application stylesheet."""

    css_path = (
        Path(__file__).resolve().parent
        / "styles"
        / "main.css"
    )

    if css_path.exists():
        css = css_path.read_text(
            encoding="utf-8"
        )

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )


def initialize_state() -> None:
    """Initialize Streamlit session state."""

    defaults = {
        "token": "",
        "thread_id": None,
        "events": [],
        "result": None,
        "approval_request": None,
        "running": False,
        "error": None,
        "stream_error": None,
        "approval_edit_mode": False,
        "session_history": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _current_session_snapshot() -> dict[str, Any] | None:
    """Capture the current UI state for session-history navigation."""

    thread_id = st.session_state.get("thread_id")
    if not thread_id:
        return None

    return {
        "thread_id": thread_id,
        "events": list(st.session_state.get("events", [])),
        "result": st.session_state.get("result"),
        "approval_request": st.session_state.get("approval_request"),
        "running": st.session_state.get("running", False),
        "error": st.session_state.get("error"),
        "stream_error": st.session_state.get("stream_error"),
        "approval_edit_mode": st.session_state.get(
            "approval_edit_mode",
            False,
        ),
    }


def _save_current_session() -> None:
    """Save the current UI state without deleting the durable backend thread."""

    snapshot = _current_session_snapshot()
    if snapshot is None:
        return

    thread_id = snapshot["thread_id"]
    st.session_state["session_history"][thread_id] = snapshot


def _restore_session(thread_id: str) -> None:
    """Restore a previously viewed session from frontend history."""

    history = st.session_state.get("session_history", {})
    snapshot = history.get(thread_id)

    if snapshot is None:
        return

    st.session_state["thread_id"] = snapshot["thread_id"]
    st.session_state["events"] = list(snapshot["events"])
    st.session_state["result"] = snapshot["result"]
    st.session_state["approval_request"] = snapshot[
        "approval_request"
    ]
    st.session_state["running"] = snapshot["running"]
    st.session_state["error"] = snapshot["error"]
    st.session_state["stream_error"] = snapshot[
        "stream_error"
    ]
    st.session_state["approval_edit_mode"] = snapshot[
        "approval_edit_mode"
    ]


def reset_execution() -> None:
    """Start a new UI session without deleting previous sessions."""

    _save_current_session()

    st.session_state["thread_id"] = None
    st.session_state["events"] = []
    st.session_state["result"] = None
    st.session_state["approval_request"] = None
    st.session_state["running"] = False
    st.session_state["error"] = None
    st.session_state["stream_error"] = None
    st.session_state["approval_edit_mode"] = False


def render_header() -> None:
    """Render application header."""

    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">EERLY.AI</div>
            <h1>Workspace Consultant</h1>
            <p>
                Analyze workspace documents, generate insights,
                and deliver validated artifacts with human approval.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    """Render authentication and session controls."""

    with st.sidebar:
        st.markdown("## Configuration")

        token = st.text_input(
            "Bearer Token",
            value=st.session_state["token"],
            type="password",
            help=(
                "JWT issued for the authenticated workspace user."
            ),
        )

        st.session_state["token"] = token

        st.divider()

        st.markdown("### Session")

        current_thread = st.session_state.get("thread_id")

        if current_thread:
            st.caption("Current thread")
            st.code(current_thread)

        new_session_disabled = (
            st.session_state.get("running", False)
        )

        if st.button(
            "New Session",
            use_container_width=True,
            disabled=new_session_disabled,
        ):
            reset_execution()
            st.rerun()

        history = st.session_state.get(
            "session_history",
            {},
        )

        if history:
            st.divider()
            st.markdown("### Previous Sessions")

            for thread_id, snapshot in reversed(
                list(history.items())
            ):
                if thread_id == current_thread:
                    continue

                result = snapshot.get("result") or {}
                status = result.get(
                    "status",
                    "saved",
                )

                label = (
                    f"{thread_id[:8]}... "
                    f"· {status}"
                )

                if st.button(
                    label,
                    key=f"session_{thread_id}",
                    use_container_width=True,
                ):
                    _save_current_session()
                    _restore_session(thread_id)
                    st.rerun()

        st.divider()

        st.caption(
            "Previous sessions remain available in this "
            "browser session. Durable agent state is stored "
            "by LangGraph/PostgreSQL."
        )

    return token

def _consume_events(
    client: EerlyAPIClient,
    thread_id: str,
    event_queue: queue.Queue[dict[str, Any]],
    connected: threading.Event,
    finished: threading.Event,
    errors: list[Exception],
    stop_events: set[str],
) -> None:
    """Consume SSE events in a background I/O thread."""

    try:
        for event in client.stream_events(
            thread_id=thread_id,
            on_connected=connected.set,
            stop_events=stop_events,
        ):
            event_queue.put(event)

    except Exception as exc:
        errors.append(exc)

    finally:
        finished.set()


def _execute_with_live_progress(
    *,
    client: EerlyAPIClient,
    thread_id: str,
    operation: Callable[[], dict[str, Any]],
    stop_events: set[str],
) -> dict[str, Any]:
    """
    Establish SSE first, then execute the API operation.

    The SSE and API request use background threads because both
    operations are blocking HTTP I/O. Streamlit rendering remains
    on the main script thread.
    """

    event_queue: queue.Queue[
        dict[str, Any]
    ] = queue.Queue()

    connected = threading.Event()
    stream_finished = threading.Event()
    operation_finished = threading.Event()

    stream_errors: list[Exception] = []
    operation_result: dict[str, Any] = {}
    operation_errors: list[Exception] = []

    stream_thread = threading.Thread(
        target=_consume_events,
        kwargs={
            "client": client,
            "thread_id": thread_id,
            "event_queue": event_queue,
            "connected": connected,
            "finished": stream_finished,
            "errors": stream_errors,
            "stop_events": stop_events,
        },
        daemon=True,
        name="eerly-sse-stream",
    )

    def run_operation() -> None:
        try:
            operation_result.update(
                operation()
            )
        except Exception as exc:
            operation_errors.append(exc)
        finally:
            operation_finished.set()

    operation_thread = threading.Thread(
        target=run_operation,
        daemon=True,
        name="eerly-agent-operation",
    )

    stream_thread.start()

    if not connected.wait(timeout=10):
        if stream_errors:
            raise stream_errors[0]

        raise APIClientError(
            "SSE connection could not be established "
            "before starting the agent."
        )

    operation_thread.start()

    progress_placeholder = st.empty()

    while (
        not operation_finished.is_set()
        or not event_queue.empty()
    ):
        drained = False

        while True:
            try:
                event = event_queue.get_nowait()
            except queue.Empty:
                break

            drained = True

            st.session_state["events"].append(
                event
            )

        if drained:
            with progress_placeholder.container():
                render_progress(
                    st.session_state["events"]
                )

        if operation_errors:
            raise operation_errors[0]

        time.sleep(0.05)

    operation_thread.join(timeout=1)

    while True:
        try:
            event = event_queue.get_nowait()
        except queue.Empty:
            break

        st.session_state["events"].append(
            event
        )

    if stream_errors:
        st.session_state["stream_error"] = str(
            stream_errors[0]
        )

    if operation_errors:
        raise operation_errors[0]

    return operation_result


def handle_decision(
    client: EerlyAPIClient,
    *,
    thread_id: str,
    decision: str,
    edited_output: str | None = None,
    feedback: str | None = None,
) -> None:
    """Submit an approval decision with live progress."""

    try:
        st.session_state["running"] = True
        st.session_state["error"] = None
        st.session_state["stream_error"] = None

        result = _execute_with_live_progress(
            client=client,
            thread_id=thread_id,
            operation=lambda: client.resume_agent(
                thread_id=thread_id,
                decision=decision,
                edited_output=edited_output,
                feedback=feedback,
            ),
            stop_events={
                "completed",
                "rejected",
                "failed",
            },
        )

        st.session_state["result"] = result

        if result.get("approval_required"):
            st.session_state["approval_request"] = (
                result.get("approval_request")
            )
        else:
            st.session_state["approval_request"] = None

        st.session_state["approval_edit_mode"] = False
        st.session_state["running"] = False

        st.rerun()

    except APIClientError as exc:
        st.session_state["running"] = False
        st.session_state["error"] = str(exc)

    except Exception as exc:
        st.session_state["running"] = False
        st.session_state["error"] = (
            f"Unexpected frontend error: {exc}"
        )


def render_request_form(
    client: EerlyAPIClient,
) -> None:
    """Render the agent request form."""

    st.markdown("## Workspace Request")

    request = st.text_area(
        "What would you like the Workspace Consultant to do?",
        placeholder=(
            "Example: Analyze the documents in my workspace "
            "and prepare a concise report of the key findings."
        ),
        height=150,
        disabled=st.session_state["running"],
    )

    col_run, col_clear = st.columns([3, 1])

    with col_run:
        run_clicked = st.button(
            "Run Workspace Consultant",
            type="primary",
            use_container_width=True,
            disabled=(
                st.session_state["running"]
                or not st.session_state["token"]
            ),
        )

    with col_clear:
        clear_clicked = st.button(
            "Clear",
            use_container_width=True,
            disabled=st.session_state["running"],
        )

    if clear_clicked:
        st.session_state["events"] = []
        st.session_state["result"] = None
        st.session_state["approval_request"] = None
        st.session_state["error"] = None
        st.session_state["stream_error"] = None
        st.rerun()

    if not run_clicked:
        return

    if not request.strip():
        st.warning(
            "Please enter a workspace request."
        )
        return

    thread_id = str(uuid4())

    st.session_state["thread_id"] = thread_id
    st.session_state["events"] = []
    st.session_state["result"] = None
    st.session_state["approval_request"] = None
    st.session_state["error"] = None
    st.session_state["stream_error"] = None
    st.session_state["running"] = True

    try:
        result = _execute_with_live_progress(
            client=client,
            thread_id=thread_id,
            operation=lambda: client.run_agent(
                request=request.strip(),
                thread_id=thread_id,
            ),
            stop_events={
                "approval_required",
                "completed",
                "rejected",
                "failed",
            },
        )

        st.session_state["result"] = result

        if result.get("approval_required"):
            st.session_state["approval_request"] = (
                result.get("approval_request")
            )

        st.session_state["running"] = False

        st.rerun()

    except APIClientError as exc:
        st.session_state["running"] = False
        st.session_state["error"] = str(exc)

    except Exception as exc:
        st.session_state["running"] = False
        st.session_state["error"] = (
            f"Unexpected frontend error: {exc}"
        )


def render_results() -> None:
    """Render analysis, approval, and artifact results."""

    result = st.session_state.get("result")

    if not result:
        return

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("## Analysis")

        selected_skills = result.get(
            "selected_skills",
            [],
        )

        if selected_skills:
            st.markdown("### Skills Used")

            for skill in selected_skills:
                st.write(f"• `{skill}`")

        findings = result.get(
            "findings",
            [],
        )

        if findings:
            st.markdown("### Findings")

            for index, finding in enumerate(
                findings,
                start=1,
            ):
                statement = finding.get(
                    "statement",
                    "",
                )

                source_path = finding.get(
                    "source_path",
                    "",
                )

                confidence = finding.get(
                    "confidence",
                    "",
                )

                with st.expander(
                    f"Finding {index}: {confidence}"
                ):
                    st.write(statement)

                    if source_path:
                        st.caption(
                            f"Source: {source_path}"
                        )

    with right:
        approval_request = st.session_state.get(
            "approval_request"
        )

        if approval_request:
            render_approval(
                approval_request,
                lambda **kwargs: handle_decision(
                    EerlyAPIClient(
                        st.session_state["token"]
                    ),
                    thread_id=result["thread_id"],
                    **kwargs,
                ),
            )

        else:
            render_artifact(
                artifact=result.get(
                    "generated_artifact"
                ),
                generated_output=result.get(
                    "generated_output"
                ),
                validation_result=result.get(
                    "validation_result"
                ),
            )


def main() -> None:
    """Run the Streamlit application."""

    initialize_state()
    load_css()

    render_header()

    token = render_sidebar()

    if not token:
        st.info(
            "Enter a valid bearer token in the sidebar "
            "to connect to the Workspace AI API."
        )
        return

    client = EerlyAPIClient(token)

    render_request_form(client)

    if st.session_state.get("stream_error"):
        st.warning(
            "Live progress stream reported an error: "
            f"{st.session_state['stream_error']}"
        )

    events = st.session_state.get("events", [])

    if events:
        st.divider()
        render_progress(events)

    render_results()


if __name__ == "__main__":
    main()
