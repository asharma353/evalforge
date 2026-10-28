"""Shared model settings and helpers for the backend's Claude calls."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic

MODEL = "claude-haiku-5-5"

# Every backend call is a short structured-generation task (a JSON list or one
# Python module), so low effort keeps latency and cost down.
EFFORT = "low"

# Thinking counts toward max_tokens, so leave room beyond the answer itself.
MAX_TOKENS = 16000


def response_text(message: anthropic.types.Message) -> str:
    """Return the text of *message*, skipping thinking blocks.

    Claude Haiku 5.5 thinks by default, so the answer is not necessarily the
    first content block.
    """
    if message.stop_reason == "refusal":
        raise ValueError("Claude declined the request (stop_reason=refusal)")
    text = "".join(block.text for block in message.content if block.type == "text")
    if not text:
        raise ValueError(f"Claude returned no text (stop_reason={message.stop_reason})")
    return text
