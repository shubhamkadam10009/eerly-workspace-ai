from __future__ import annotations

import threading
import time

from fastapi.testclient import TestClient

from app.agent.event_bus import event_bus
from app.agent.events import AgentEvent
from app.auth.dependencies import get_current_user_id
from app.main import app


TEST_THREAD = "sse-test-thread"


def make_event(
    event: str,
    thread_id: str = TEST_THREAD,
    status: str = "running",
    message: str = "Test event",
) -> AgentEvent:
    return AgentEvent(
        event=event,
        thread_id=thread_id,
        status=status,
        message=message,
        data={"test": True},
    )


def setup_auth(user_id: str):
    app.dependency_overrides[get_current_user_id] = (
        lambda: user_id
    )


def teardown_auth():
    app.dependency_overrides.pop(
        get_current_user_id,
        None,
    )


def test_sse_endpoint_requires_authentication():
    teardown_auth()

    with TestClient(app) as client:
        response = client.get(
            f"/agent/stream/{TEST_THREAD}"
        )

    assert response.status_code == 401


def test_sse_endpoint_returns_event_stream():
    setup_auth("user_a")

    try:
        with TestClient(app) as client:

            def publish_events():
                time.sleep(0.2)

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "request_received",
                        status="running",
                        message="Request received",
                    ),
                )

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "completed",
                        status="completed",
                        message="Execution completed",
                    ),
                )

            publisher = threading.Thread(
                target=publish_events,
                daemon=True,
            )
            publisher.start()

            with client.stream(
                "GET",
                f"/agent/stream/{TEST_THREAD}",
            ) as response:

                assert response.status_code == 200
                assert response.headers["content-type"].startswith(
                    "text/event-stream"
                )

                body = ""
                for chunk in response.iter_text():
                    body += chunk

                assert "event: request_received" in body
                assert "event: completed" in body
                assert '"thread_id": "sse-test-thread"' in body
                assert '"status": "completed"' in body

            publisher.join(timeout=2)

    finally:
        teardown_auth()


def test_sse_event_contains_structured_json_data():
    setup_auth("user_a")

    try:
        with TestClient(app) as client:

            def publish():
                time.sleep(0.2)

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "completed",
                        status="completed",
                        message="Done",
                    ),
                )

            thread = threading.Thread(
                target=publish,
                daemon=True,
            )
            thread.start()

            with client.stream(
                "GET",
                f"/agent/stream/{TEST_THREAD}",
            ) as response:

                body = ""
                for chunk in response.iter_text():
                    body += chunk

                assert "event: completed\n" in body
                assert "data: {" in body
                assert '"event": "completed"' in body
                assert '"status": "completed"' in body
                assert '"message": "Done"' in body
                assert '"test": true' in body

            thread.join(timeout=2)

    finally:
        teardown_auth()


def test_sse_user_isolation():
    user_a_key = "user_a:sse-isolation-thread"
    user_b_key = "user_b:sse-isolation-thread"

    queue_a = event_bus.subscribe(user_a_key)
    queue_b = event_bus.subscribe(user_b_key)

    try:
        event_a = make_event(
            "analysis_completed",
            thread_id="sse-isolation-thread",
            message="User A event",
        )

        event_b = make_event(
            "analysis_completed",
            thread_id="sse-isolation-thread",
            message="User B event",
        )

        event_bus.publish(user_a_key, event_a)
        event_bus.publish(user_b_key, event_b)

        received_a = queue_a.get(timeout=1)
        received_b = queue_b.get(timeout=1)

        assert received_a.message == "User A event"
        assert received_b.message == "User B event"

        assert received_a.message != received_b.message

    finally:
        event_bus.unsubscribe(
            user_a_key,
            queue_a,
        )
        event_bus.unsubscribe(
            user_b_key,
            queue_b,
        )


def test_sse_does_not_cross_user_stream_keys():
    user_a_key = "user_a:shared-thread"
    user_b_key = "user_b:shared-thread"

    queue_a = event_bus.subscribe(user_a_key)
    queue_b = event_bus.subscribe(user_b_key)

    try:
        event_a = make_event(
            "completed",
            thread_id="shared-thread",
            status="completed",
            message="Only User A",
        )

        event_bus.publish(
            user_a_key,
            event_a,
        )

        received_a = queue_a.get(timeout=1)

        assert received_a.message == "Only User A"
        assert queue_b.empty()

    finally:
        event_bus.unsubscribe(
            user_a_key,
            queue_a,
        )
        event_bus.unsubscribe(
            user_b_key,
            queue_b,
        )


def test_sse_completed_event_terminates_stream():
    setup_auth("user_a")

    try:
        with TestClient(app) as client:

            def publish():
                time.sleep(0.2)

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "completed",
                        status="completed",
                        message="Finished",
                    ),
                )

            thread = threading.Thread(
                target=publish,
                daemon=True,
            )
            thread.start()

            start = time.monotonic()

            with client.stream(
                "GET",
                f"/agent/stream/{TEST_THREAD}",
            ) as response:
                body = ""
                for chunk in response.iter_text():
                    body += chunk

            elapsed = time.monotonic() - start

            assert "event: completed" in body

            # The stream should terminate immediately after the
            # terminal event rather than waiting for heartbeat timeout.
            assert elapsed < 5

            thread.join(timeout=2)

    finally:
        teardown_auth()


def test_sse_rejected_event_terminates_stream():
    setup_auth("user_a")

    try:
        with TestClient(app) as client:

            def publish():
                time.sleep(0.2)

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "rejected",
                        status="rejected",
                        message="Rejected by reviewer",
                    ),
                )

            thread = threading.Thread(
                target=publish,
                daemon=True,
            )
            thread.start()

            with client.stream(
                "GET",
                f"/agent/stream/{TEST_THREAD}",
            ) as response:
                body = ""
                for chunk in response.iter_text():
                    body += chunk

            assert "event: rejected" in body
            assert "Rejected by reviewer" in body

            thread.join(timeout=2)

    finally:
        teardown_auth()


def test_sse_failed_event_terminates_stream():
    setup_auth("user_a")

    try:
        with TestClient(app) as client:

            def publish():
                time.sleep(0.2)

                event_bus.publish(
                    "user_a:sse-test-thread",
                    make_event(
                        "failed",
                        status="failed",
                        message="Execution failed",
                    ),
                )

            thread = threading.Thread(
                target=publish,
                daemon=True,
            )
            thread.start()

            with client.stream(
                "GET",
                f"/agent/stream/{TEST_THREAD}",
            ) as response:
                body = ""
                for chunk in response.iter_text():
                    body += chunk

            assert "event: failed" in body
            assert "Execution failed" in body

            thread.join(timeout=2)

    finally:
        teardown_auth()


def test_event_bus_cleanup_after_terminal_event():
    key = "user_a:cleanup-test"

    queue = event_bus.subscribe(key)

    event_bus.publish(
        key,
        make_event(
            "completed",
            thread_id="cleanup-test",
            status="completed",
        ),
    )

    received = queue.get(timeout=1)

    assert received.event == "completed"

    event_bus.unsubscribe(
        key,
        queue,
    )

    replacement = event_bus.subscribe(key)

    try:
        assert replacement is not queue
    finally:
        event_bus.unsubscribe(
            key,
            replacement,
        )
