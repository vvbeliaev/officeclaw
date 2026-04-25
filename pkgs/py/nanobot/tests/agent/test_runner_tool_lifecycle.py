"""Runner emits per-tool lifecycle events through AgentHook.

Order under test (matches what the API server forwards to UIMessage parts):
    on_tool_call_finalized → on_tool_execution_start → on_tool_result
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.hook import AgentHook, AgentHookContext
from nanobot.agent.runner import AgentRunSpec, AgentRunner
from nanobot.config.schema import AgentDefaults
from nanobot.providers.base import LLMResponse, ToolCallRequest

_MAX_TOOL_RESULT_CHARS = AgentDefaults().max_tool_result_chars


class _RecordingHook(AgentHook):
    def __init__(self) -> None:
        self.events: list[tuple[str, str | None]] = []

    async def on_tool_call_finalized(self, ctx: AgentHookContext, tool_call: ToolCallRequest) -> None:
        self.events.append(("finalized", tool_call.id))

    async def on_tool_execution_start(self, ctx: AgentHookContext, tool_call: ToolCallRequest) -> None:
        self.events.append(("start", tool_call.id))

    async def on_tool_result(
        self,
        ctx: AgentHookContext,
        tool_call: ToolCallRequest,
        result: str,
        error: str | None,
    ) -> None:
        self.events.append(("result", tool_call.id))


@pytest.mark.asyncio
async def test_runner_emits_finalized_start_and_result_per_tool() -> None:
    provider = MagicMock()

    async def chat_with_retry(*, messages, **kwargs):
        # Two tool calls in one assistant turn — checks per-call ordering and
        # that result events arrive after every start event.
        if any(m.get("role") == "tool" for m in messages):
            return LLMResponse(content="done", tool_calls=[], usage={})
        return LLMResponse(
            content="ok",
            tool_calls=[
                ToolCallRequest(id="call_a", name="t1", arguments={"x": 1}),
                ToolCallRequest(id="call_b", name="t2", arguments={"y": 2}),
            ],
            usage={},
        )

    provider.chat_with_retry = chat_with_retry
    tools = MagicMock()
    tools.get_definitions.return_value = []
    tools.execute = AsyncMock(return_value="tool result")

    hook = _RecordingHook()
    runner = AgentRunner(provider)
    result = await runner.run(AgentRunSpec(
        initial_messages=[{"role": "user", "content": "do task"}],
        tools=tools,
        model="test-model",
        max_iterations=3,
        max_tool_result_chars=_MAX_TOOL_RESULT_CHARS,
        hook=hook,
    ))

    assert result.final_content == "done"
    # finalized fires for both calls before any execution begins;
    # then per-call (start, result) pairs in stable order.
    assert hook.events == [
        ("finalized", "call_a"),
        ("finalized", "call_b"),
        ("start", "call_a"),
        ("result", "call_a"),
        ("start", "call_b"),
        ("result", "call_b"),
    ]


@pytest.mark.asyncio
async def test_runner_emits_result_with_error_when_tool_raises() -> None:
    provider = MagicMock()

    async def chat_with_retry(*, messages, **kwargs):
        if any(m.get("role") == "tool" for m in messages):
            return LLMResponse(content="recovered", tool_calls=[], usage={})
        return LLMResponse(
            content="",
            tool_calls=[ToolCallRequest(id="call_err", name="bad", arguments={})],
            usage={},
        )

    provider.chat_with_retry = chat_with_retry
    tools = MagicMock()
    tools.get_definitions.return_value = []
    tools.execute = AsyncMock(side_effect=RuntimeError("nope"))

    error_payloads: list[tuple[str, str | None]] = []

    class ErrorRecorder(AgentHook):
        async def on_tool_result(self, ctx, tool_call, result, error):
            error_payloads.append((tool_call.id, error))

    runner = AgentRunner(provider)
    await runner.run(AgentRunSpec(
        initial_messages=[{"role": "user", "content": "do task"}],
        tools=tools,
        model="test-model",
        max_iterations=3,
        max_tool_result_chars=_MAX_TOOL_RESULT_CHARS,
        hook=ErrorRecorder(),
    ))

    assert len(error_payloads) == 1
    call_id, err = error_payloads[0]
    assert call_id == "call_err"
    assert err is not None and "RuntimeError" in err
