"""SSE (Server-Sent Events) manager for streaming progress events."""

import asyncio
import json


class SSEManager:
    """Manages Server-Sent Events for real-time progress streaming."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict] = asyncio.Queue()

    async def send_event(self, event_type: str, data: dict) -> None:
        """Put an event onto the queue for streaming to connected clients.

        Args:
            event_type: The SSE event name (e.g., "progress", "complete").
            data: Dictionary payload to send as JSON.
        """
        await self._queue.put(
            {"event": event_type, "data": json.dumps(data)}
        )

    async def event_generator(self):
        """Async generator that yields events from the queue.

        Yields SSE-formatted dicts suitable for sse-starlette EventSourceResponse.
        """
        while True:
            event = await self._queue.get()
            yield event


# Global SSE manager instance
sse_manager = SSEManager()
