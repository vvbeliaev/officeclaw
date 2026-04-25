"""OpenAI-compat provider streams tool-call args and reasoning deltas.

These callbacks are how the API server forwards live agent activity to
SvelteKit / AI SDK consumers (UIMessage tool-X parts and reasoning).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from nanobot.providers.base import ToolCallDelta
from nanobot.providers.openai_compat_provider import OpenAICompatProvider
from nanobot.providers.registry import find_by_name


class _ChunkStream:
    """Minimal async iterator over pre-built OpenAI streaming chunks."""

    def __init__(self, chunks: list[SimpleNamespace]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


def _text_chunk(text: str) -> SimpleNamespace:
    delta = SimpleNamespace(content=text, tool_calls=None, reasoning_content=None)
    choice = SimpleNamespace(delta=delta, finish_reason=None)
    return SimpleNamespace(choices=[choice], usage=None)


def _tool_call_chunk(
    *, index: int, call_id: str | None = None,
    name: str | None = None, args_delta: str | None = None,
) -> SimpleNamespace:
    function = SimpleNamespace(name=name, arguments=args_delta)
    tc = SimpleNamespace(index=index, id=call_id, type="function", function=function)
    delta = SimpleNamespace(content=None, tool_calls=[tc], reasoning_content=None)
    choice = SimpleNamespace(delta=delta, finish_reason=None)
    return SimpleNamespace(choices=[choice], usage=None)


def _reasoning_chunk(text: str) -> SimpleNamespace:
    delta = SimpleNamespace(content=None, tool_calls=None, reasoning_content=text)
    choice = SimpleNamespace(delta=delta, finish_reason=None)
    return SimpleNamespace(choices=[choice], usage=None)


def _final_chunk() -> SimpleNamespace:
    delta = SimpleNamespace(content=None, tool_calls=None, reasoning_content=None)
    choice = SimpleNamespace(delta=delta, finish_reason="tool_calls")
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_chat_stream_emits_tool_call_deltas() -> None:
    chunks = [
        _text_chunk("Let me check"),
        _tool_call_chunk(index=0, call_id="call_abc", name="web_fetch"),
        _tool_call_chunk(index=0, args_delta='{"url"'),
        _tool_call_chunk(index=0, args_delta=':"https://x"}'),
        _final_chunk(),
    ]
    spec = find_by_name("openai")

    text_deltas: list[str] = []
    tool_deltas: list[ToolCallDelta] = []

    async def on_content(d: str) -> None:
        text_deltas.append(d)

    async def on_tool(d: ToolCallDelta) -> None:
        tool_deltas.append(d)

    with patch("nanobot.providers.openai_compat_provider.AsyncOpenAI") as MockClient:
        client = MockClient.return_value
        client.chat.completions.create = AsyncMock(return_value=_ChunkStream(chunks))
        provider = OpenAICompatProvider(api_key="k", default_model="gpt-4o", spec=spec)

        await provider.chat_stream(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            on_content_delta=on_content,
            on_tool_call_delta=on_tool,
        )

    assert text_deltas == ["Let me check"]
    assert [(d.index, d.id, d.name, d.arguments_delta) for d in tool_deltas] == [
        (0, "call_abc", "web_fetch", None),
        (0, None, None, '{"url"'),
        (0, None, None, ':"https://x"}'),
    ]


@pytest.mark.asyncio
async def test_chat_stream_emits_reasoning_deltas() -> None:
    chunks = [
        _reasoning_chunk("thinking step one"),
        _reasoning_chunk("...step two"),
        _text_chunk("done"),
        _final_chunk(),
    ]
    spec = find_by_name("openai")

    reasoning: list[str] = []

    async def on_reasoning(d: str) -> None:
        reasoning.append(d)

    with patch("nanobot.providers.openai_compat_provider.AsyncOpenAI") as MockClient:
        client = MockClient.return_value
        client.chat.completions.create = AsyncMock(return_value=_ChunkStream(chunks))
        provider = OpenAICompatProvider(api_key="k", default_model="gpt-4o", spec=spec)

        await provider.chat_stream(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            on_reasoning_delta=on_reasoning,
        )

    assert reasoning == ["thinking step one", "...step two"]


@pytest.mark.asyncio
async def test_chat_stream_skips_callbacks_when_not_provided() -> None:
    """Backward compat: existing callers passing only on_content_delta still work."""
    chunks = [
        _text_chunk("hi"),
        _tool_call_chunk(index=0, call_id="x", name="t", args_delta="{}"),
        _reasoning_chunk("r"),
        _final_chunk(),
    ]
    spec = find_by_name("openai")
    text: list[str] = []

    async def on_content(d: str) -> None:
        text.append(d)

    with patch("nanobot.providers.openai_compat_provider.AsyncOpenAI") as MockClient:
        client = MockClient.return_value
        client.chat.completions.create = AsyncMock(return_value=_ChunkStream(chunks))
        provider = OpenAICompatProvider(api_key="k", default_model="gpt-4o", spec=spec)

        # No tool/reasoning callbacks — must not raise, must still receive text.
        await provider.chat_stream(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            on_content_delta=on_content,
        )

    assert text == ["hi"]
