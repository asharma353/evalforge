"""Tests for the backend's Claude calls, using a fake client (no network).

Claude Haiku 5.5 thinks by default, so every fake reply starts with a thinking
block: code that reads ``message.content[0].text`` would fail these tests.
"""

from __future__ import annotations

import anthropic
import pytest
from anthropic.types import Message, TextBlock, ThinkingBlock, Usage

from services import llm
from services.generator.evaluator_generator import generate_evaluator


def make_message(text: str, stop_reason: str = "end_turn") -> Message:
    content = [ThinkingBlock.model_construct(type="thinking", thinking="", signature="sig")]
    if text:
        content.append(TextBlock.model_construct(type="text", text=text))
    return Message.model_construct(
        id="msg_test",
        type="message",
        role="assistant",
        model=llm.MODEL,
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage.model_construct(input_tokens=1, output_tokens=1),
    )


@pytest.fixture
def fake_client(monkeypatch):
    """Patch anthropic.Anthropic; returns a dict holding the reply and request kwargs."""
    state: dict = {"reply": "", "requests": []}

    class FakeMessages:
        def create(self, **kwargs):
            state["requests"].append(kwargs)
            return make_message(state["reply"])

    class FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    return state


def test_response_text_skips_thinking_blocks():
    assert llm.response_text(make_message('["a"]')) == '["a"]'


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (make_message("", stop_reason="refusal"), "declined"),
        (make_message("", stop_reason="max_tokens"), "no text"),
    ],
)
def test_response_text_raises_without_an_answer(message, error):
    with pytest.raises(ValueError, match=error):
        llm.response_text(message)


def test_generator_calls_current_model_and_reads_text_after_thinking(fake_client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_client["reply"] = (
        "# evaluator_type: assertion\n"
        "METADATA = {}\n"
        "def check_sample_mode(response, context=None):\n"
        "    return True\n"
    )

    code = generate_evaluator({"id": "sample_mode", "evaluator_type": "assertion"})

    assert code == fake_client["reply"].strip()
    request = fake_client["requests"][0]
    assert request["model"] == llm.MODEL == "claude-haiku-5-5"
    assert request["output_config"] == {"effort": llm.EFFORT}


@pytest.mark.parametrize(("verdict", "passed"), [("true", True), ("false", False)])
def test_exported_llm_judge_reads_text_after_thinking(fake_client, monkeypatch, verdict, passed):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code = generate_evaluator({"id": "sample_mode", "evaluator_type": "llm_judge"})
    namespace: dict = {}
    exec(compile(code, "check_sample_mode.py", "exec"), namespace)
    fake_client["reply"] = f'{{"pass": {verdict}, "reason": "test"}}'

    assert namespace["check_sample_mode"]("some response", {"input": "hi"}) is passed

    # The exported stub is self-contained, so it hardcodes the model; keep it in sync.
    assert fake_client["requests"][0]["model"] == llm.MODEL


# The public entry points fall back to static data on any error, which would
# hide a broken call, so these tests call the private LLM functions directly.

def test_failure_mode_augmentation_reads_text_after_thinking(fake_client):
    from services.generator.failure_modes import _augment_with_llm

    fake_client["reply"] = (
        '[{"id": "custom_mode", "name": "Custom", "description": "d", '
        '"evaluator_type": "regex", "app_type": "general", "severity": "low"}]'
    )

    intent = {"app_type": "general", "failure_concerns": ["made-up facts"]}
    modes = _augment_with_llm(intent, [], "test-key")

    assert [mode["id"] for mode in modes] == ["custom_mode"]
    assert fake_client["requests"][0]["model"] == llm.MODEL


def test_dimension_augmentation_reads_text_after_thinking(fake_client):
    from services.test_data.dimension_extractor import _augment_with_llm

    fake_client["reply"] = '[{"name": "tone", "values": ["polite", "rude"], "description": "d"}]'

    dims = _augment_with_llm({}, {"id": "m", "name": "M", "description": "d"}, [], "test-key")

    assert [dim["name"] for dim in dims] == ["tone"]
    assert fake_client["requests"][0]["model"] == llm.MODEL


def test_test_case_naturalization_reads_text_after_thinking(fake_client):
    from services.test_data.test_case_generator import _llm_naturalize_batch

    fake_client["reply"] = '[{"input": "llm input", "expected_behavior": "llm expected"}]'

    cases = _llm_naturalize_batch([{"tone": "polite"}], {"id": "m"}, {}, "test-key")

    assert cases == [{"input": "llm input", "expected_behavior": "llm expected", "failure_mode_id": "m"}]
    assert fake_client["requests"][0]["model"] == llm.MODEL


def test_question_generation_reads_text_after_thinking(fake_client):
    import asyncio

    from services.questioner.generator import _generate_with_llm

    fake_client["reply"] = (
        "["
        + ", ".join(
            f'{{"id": "q{i}", "text": "llm question {i}", "category": "c", "type": "text"}}'
            for i in range(5)
        )
        + "]"
    )

    questions, _source = asyncio.run(_generate_with_llm({}, "chatbot", "test-key"))

    assert [q["text"] for q in questions] == [f"llm question {i}" for i in range(5)]
    assert fake_client["requests"][0]["model"] == llm.MODEL
