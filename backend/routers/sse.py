"""SSE streaming router for real-time progress events."""

import uuid

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from services.sse import sse_manager

router = APIRouter()


@router.get("/")
async def sse_stream():
    """Stream Server-Sent Events to connected clients.

    Generates a unique connection_id per connection so each tab gets its
    own queue in the SSEManager registry (per-connection fan-out).
    """
    connection_id = str(uuid.uuid4())
    return EventSourceResponse(sse_manager.event_generator(connection_id))


@router.get("/test")
async def sse_test():
    """Send a test event to verify SSE infrastructure is working."""
    await sse_manager.send_event("test", {"message": "SSE working"})
    return {"status": "ok", "message": "Test event sent"}
