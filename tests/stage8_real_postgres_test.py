import uuid

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from app.core.config import get_settings


class TestState(TypedDict):
    message: str
    approval: str | None


def ask_for_approval(state: TestState):
    decision = interrupt({
        "type": "approval",
        "message": "Approve this test execution?"
    })

    return {
        "approval": decision
    }


def finish(state: TestState):
    return {
        "message": f"completed:{state['approval']}"
    }


def build_graph(checkpointer):
    builder = StateGraph(TestState)

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

    print("=" * 70)
    print("STAGE 8 REAL POSTGRESQL INTERRUPT/RESUME TEST")
    print("=" * 70)
    print(f"Thread ID: {thread_id}")
    print()

    with PostgresSaver.from_conn_string(conninfo) as checkpointer:
        checkpointer.setup()

        graph = build_graph(checkpointer)

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        print("[1/5] Starting graph...")
        first_result = graph.invoke(
            {
                "message": "Stage 8 durability test",
                "approval": None,
            },
            config,
        )

        print("      Graph paused at interrupt.")

        interrupts = first_result.get("__interrupt__", [])

        assert interrupts, "FAIL: No interrupt was created."

        print("      PASS: Interrupt detected.")
        print(f"      Interrupt payload: {interrupts[0].value}")
        print()

        print("[2/5] Checking persisted PostgreSQL state...")

        checkpoint_state = graph.get_state(config)

        assert checkpoint_state is not None, \
            "FAIL: No checkpoint state returned."

        assert checkpoint_state.values["message"] == \
            "Stage 8 durability test", \
            "FAIL: Persisted state does not contain expected message."

        print("      PASS: Checkpoint exists in PostgreSQL.")
        print(f"      Persisted values: {checkpoint_state.values}")
        print()

        print("[3/5] Resuming with approval...")

        final_result = graph.invoke(
            Command(resume="approved"),
            config,
        )

        print("      PASS: Graph resumed.")
        print()

        print("[4/5] Verifying final execution...")

        assert final_result["approval"] == "approved", \
            "FAIL: Approval value was not persisted."

        assert final_result["message"] == "completed:approved", \
            "FAIL: Graph did not reach final node."

        print("      PASS: Final state is correct.")
        print(f"      Final result: {final_result}")
        print()

        print("[5/5] Verifying no interrupt remains...")

        final_state = graph.get_state(config)

        assert not final_state.interrupts, \
            "FAIL: Graph still has an active interrupt."

        print("      PASS: No active interrupt remains.")
        print()

    print("=" * 70)
    print("STAGE 8 REAL POSTGRESQL TEST PASSED")
    print("=" * 70)
    print()
    print("Verified:")
    print("  PASS - LangGraph interrupt()")
    print("  PASS - PostgreSQL checkpoint persistence")
    print("  PASS - persisted state retrieval")
    print("  PASS - Command(resume=...)")
    print("  PASS - graph continuation")
    print("  PASS - final state")
    print("  PASS - interrupt cleared after resume")


if __name__ == "__main__":
    main()
