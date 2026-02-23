"""SSE streaming router for real-time progress events."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from services.sse import sse_manager

router = APIRouter()


@router.get("/")
async def sse_stream():
    """Stream Server-Sent Events to connected clients."""
    return EventSourceResponse(sse_manager.event_generator())


@router.get("/test")
async def sse_test():
    """Send a test event to verify SSE infrastructure is working."""
    await sse_manager.send_event("test", {"message": "SSE working"})
    return {"status": "ok", "message": "Test event sent"}
