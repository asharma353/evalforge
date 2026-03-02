"""SSE (Server-Sent Events) manager for streaming progress events."""

import asyncio
import json


class SSEManager:
    """Per-connection queue registry for SSE fan-out.

    Each SSE connection gets its own asyncio.Queue. send_event fans out
    to ALL registered queues. Each connection's generator drains only its
    own queue. Prevents events being stolen by whichever connection wins
    the queue.get() race (the bug in the single-queue design).
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    async def send_event(self, event_type: str, data: dict) -> None:
        """Fan out an event to ALL registered connection queues.

        Args:
            event_type: The SSE event name (e.g., "progress", "complete").
            data: Dictionary payload to send as JSON.
        """
        payload = {"event": event_type, "data": json.dumps(data)}
        # Shallow copy to avoid dict mutation during iteration (disconnect race)
        for queue in list(self._queues.values()):
            await queue.put(payload)

    async def event_generator(self, connection_id: str):
        """Async generator that drains events for a single connection.

        Registers the queue on entry, always cleans up on exit (disconnect
        or server close) via the finally block to prevent memory leaks.

        Args:
            connection_id: Unique ID for this SSE connection (UUID string).
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[connection_id] = queue
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            # Always clean up — even if the client disconnects mid-stream
            self._queues.pop(connection_id, None)


# Global SSE manager instance
sse_manager = SSEManager()
