"""Tests for the extended streaming hook surface.

Covers the new callbacks added so the API server can stream tool-call
deltas, per-tool execution lifecycle, and reasoning content to clients
that render an agent activity timeline (Vercel AI SDK UIMessage parts).
"""

from __future__ import annotations

import pytest

from nanobot.agent.hook import AgentHook, AgentHookContext, CompositeHook
from nanobot.providers.base import ToolCallDelta, ToolCallRequest


def _ctx() -> AgentHookContext:
    return AgentHookContext(iteration=0, messages=[])


def _tool_call(name: str = "web_fetch", call_id: str = "call_1") -> ToolCallRequest:
    return ToolCallRequest(id=call_id, name=name, arguments={"url": "https://x"})


# ---------------------------------------------------------------------------
# AgentHook protocol — base implementations are no-ops
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_base_hook_extended_callbacks_are_no_ops():
    hook = AgentHook()
    ctx = _ctx()
    # None of these should raise — defaults are no-ops so subclasses opt in.
    await hook.on_tool_call_delta(ctx, ToolCallDelta(index=0, id="x", name="n"))
    await hook.on_tool_call_finalized(ctx, _tool_call())
    await hook.on_tool_execution_start(ctx, _tool_call())
    await hook.on_tool_result(ctx, _tool_call(), "ok", None)
    await hook.on_reasoning_delta(ctx, "thinking")


# ---------------------------------------------------------------------------
# CompositeHook — fan-out + ordering for the new callbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_composite_fans_out_extended_callbacks_in_order():
    events: list[str] = []

    class Recorder(AgentHook):
        def __init__(self, tag: str) -> None:
            self.tag = tag

        async def on_tool_call_delta(self, ctx, delta):
            events.append(f"{self.tag}:delta:{delta.id}:{delta.arguments_delta}")

        async def on_tool_call_finalized(self, ctx, tool_call):
            events.append(f"{self.tag}:final:{tool_call.id}")

        async def on_tool_execution_start(self, ctx, tool_call):
            events.append(f"{self.tag}:start:{tool_call.id}")

        async def on_tool_result(self, ctx, tool_call, result, error):
            events.append(f"{self.tag}:result:{tool_call.id}:{result}:{error}")

        async def on_reasoning_delta(self, ctx, delta):
            events.append(f"{self.tag}:reason:{delta}")

    hook = CompositeHook([Recorder("A"), Recorder("B")])
    ctx = _ctx()

    await hook.on_tool_call_delta(ctx, ToolCallDelta(index=0, id="c1", arguments_delta='{"u'))
    await hook.on_tool_call_finalized(ctx, _tool_call(call_id="c1"))
    await hook.on_tool_execution_start(ctx, _tool_call(call_id="c1"))
    await hook.on_tool_result(ctx, _tool_call(call_id="c1"), "200 OK", None)
    await hook.on_reasoning_delta(ctx, "step 1")

    assert events == [
        'A:delta:c1:{"u', 'B:delta:c1:{"u',
        "A:final:c1", "B:final:c1",
        "A:start:c1", "B:start:c1",
        "A:result:c1:200 OK:None", "B:result:c1:200 OK:None",
        "A:reason:step 1", "B:reason:step 1",
    ]


@pytest.mark.asyncio
async def test_composite_extended_callbacks_error_isolation():
    """A faulty hook must not break siblings — same contract as on_stream."""
    calls: list[str] = []

    class Bad(AgentHook):
        async def on_tool_result(self, ctx, tool_call, result, error):
            raise RuntimeError("boom")

    class Good(AgentHook):
        async def on_tool_result(self, ctx, tool_call, result, error):
            calls.append(f"good:{tool_call.id}:{error}")

    hook = CompositeHook([Bad(), Good()])
    await hook.on_tool_result(_ctx(), _tool_call(call_id="c2"), "ok", None)
    assert calls == ["good:c2:None"]


# ---------------------------------------------------------------------------
# ToolCallDelta — shape sanity (kept tight; AI SDK relies on these fields)
# ---------------------------------------------------------------------------


def test_tool_call_delta_fields_are_optional_except_index():
    d = ToolCallDelta(index=0)
    assert d.index == 0
    assert d.id is None
    assert d.name is None
    assert d.arguments_delta is None

    d2 = ToolCallDelta(index=2, id="call_xyz", name="web_fetch", arguments_delta='{"url"')
    assert d2.index == 2
    assert d2.id == "call_xyz"
    assert d2.name == "web_fetch"
    assert d2.arguments_delta == '{"url"'
