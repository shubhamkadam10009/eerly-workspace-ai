import uuid

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from app.core.config import get_settings


class CheckpointState(TypedDict):
    message: str
    approval: str | None


def ask_for_approval(state: CheckpointState):
    decision = interrupt({
        "type": "approval",
        "message": "Approve this test execution?",
    })

    return {
        "approval": decision,
    }


def finish(state: CheckpointState):
    return {
        "message": f"completed:{state['approval']}",
    }


def build_graph(checkpointer):
    builder = StateGraph(CheckpointState)

    builder.add_node("approval", ask_for_approval)
    builder.add_node("finish", finish)

    builder.add_edge(START, "approval")
    builder.add_edge("approval", "finish")
    builder.add_edge("finish", END)

    return builder.compile(checkpointer=checkpointer)


def main():
    settings = get_settings()

    conninfo = (
        settings.database_url
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )

    thread_id = f"stage8-real-test-{uuid.uuid4()}"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    print("=" * 70)
    print("STAGE 8 REAL POSTGRESQL INTERRUPT/RESUME TEST")
    print("=" * 70)
    print(f"Thread ID: {thread_id}")
    print()

    # ------------------------------------------------------------------
    # Execution 1: start the workflow and persist the interrupted state.
    # ------------------------------------------------------------------
    with PostgresSaver.from_conn_string(conninfo) as checkpointer:
        checkpointer.setup()

        graph = build_graph(checkpointer)

        print("[1/6] Starting graph...")
        first_result = graph.invoke(
            {
                "message": "Stage 8 durability test",
                "approval": None,
            },
            config,
        )

        interrupts = first_result.get("__interrupt__", [])

        assert interrupts, "FAIL: No interrupt was created."

        print("      PASS: Interrupt detected.")
        print(f"      Interrupt payload: {interrupts[0].value}")
        print()

        print("[2/6] Checking persisted PostgreSQL state...")

        checkpoint_state = graph.get_state(config)

        assert checkpoint_state is not None, \
            "FAIL: No checkpoint state returned."

        assert checkpoint_state.values["message"] == \
            "Stage 8 durability test", \
            "FAIL: Persisted state does not contain expected message."

        assert checkpoint_state.values["approval"] is None, \
            "FAIL: Unexpected approval value before resume."

        print("      PASS: Checkpoint exists in PostgreSQL.")
        print(f"      Persisted values: {checkpoint_state.values}")
        print()

    # ------------------------------------------------------------------
    # Execution 1 is now completely closed.
    #
    # We deliberately create a NEW checkpointer and NEW graph below.
    # The workflow must recover from PostgreSQL rather than relying on
    # the original in-memory graph/checkpointer objects.
    # ------------------------------------------------------------------

    print("[3/6] Simulating execution restart...")
    print("      Original graph and checkpointer have been closed.")
    print()

    # ------------------------------------------------------------------
    # Execution 2: create completely new graph/checkpointer instances
    # and resume the same persisted thread.
    # ------------------------------------------------------------------
    with PostgresSaver.from_conn_string(conninfo) as new_checkpointer:
        new_checkpointer.setup()

        resumed_graph = build_graph(new_checkpointer)

        print("[4/6] Resuming persisted workflow with a new graph...")

        final_result = resumed_graph.invoke(
            Command(resume="approved"),
            config,
        )

        print("      PASS: Graph resumed after execution restart.")
        print()

        print("[5/6] Verifying final execution...")

        assert final_result["approval"] == "approved", \
            "FAIL: Approval value was not persisted."

        assert final_result["message"] == "completed:approved", \
            "FAIL: Graph did not reach final node."

        print("      PASS: Final state is correct.")
        print(f"      Final result: {final_result}")
        print()

        print("[6/6] Verifying no interrupt remains...")

        final_state = resumed_graph.get_state(config)

        assert not final_state.interrupts, \
            "FAIL: Graph still has an active interrupt."

        print("      PASS: No active interrupt remains.")
        print()

    print("=" * 70)
    print("STAGE 8 REAL POSTGRESQL DURABILITY TEST PASSED")
    print("=" * 70)
    print()
    print("Verified:")
    print("  PASS - LangGraph interrupt()")
    print("  PASS - PostgreSQL checkpoint persistence")
    print("  PASS - persisted state retrieval")
    print("  PASS - original execution closed")
    print("  PASS - NEW checkpointer created")
    print("  PASS - NEW graph created")
    print("  PASS - Command(resume=...)")
    print("  PASS - workflow recovery after restart")
    print("  PASS - graph continuation")
    print("  PASS - final state")
    print("  PASS - interrupt cleared after resume")


if __name__ == "__main__":
    main()
