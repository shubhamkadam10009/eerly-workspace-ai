from __future__ import annotations

from collections import defaultdict
from queue import Empty, Queue
from threading import Lock
from typing import Iterator

from app.agent.events import AgentEvent


class AgentEventBus:
    """Thread-safe in-process event bus.

    Each user/thread gets isolated subscriber queues.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[Queue[AgentEvent]]] = defaultdict(set)
        self._lock = Lock()

    def subscribe(self, stream_key: str) -> Queue[AgentEvent]:
        queue: Queue[AgentEvent] = Queue()

        with self._lock:
            self._subscribers[stream_key].add(queue)

        return queue

    def unsubscribe(
        self,
        stream_key: str,
        queue: Queue[AgentEvent],
    ) -> None:
        with self._lock:
            subscribers = self._subscribers.get(stream_key)

            if not subscribers:
                return

            subscribers.discard(queue)

            if not subscribers:
                self._subscribers.pop(stream_key, None)

    def publish(
        self,
        stream_key: str,
        event: AgentEvent,
    ) -> None:
        with self._lock:
            subscribers = list(
                self._subscribers.get(stream_key, set())
            )

        for queue in subscribers:
            queue.put(event)

    def stream(
        self,
        stream_key: str,
        timeout: float = 15.0,
    ) -> Iterator[AgentEvent]:
        queue = self.subscribe(stream_key)

        try:
            while True:
                try:
                    event = queue.get(timeout=timeout)
                except Empty:
                    continue

                yield event

                if event.event in {
                    "completed",
                    "rejected",
                    "failed",
                }:
                    break
        finally:
            self.unsubscribe(stream_key, queue)


event_bus = AgentEventBus()
