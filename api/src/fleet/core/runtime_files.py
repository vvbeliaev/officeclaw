"""Runtime-file assembly and split helpers.

Runtime files (SOUL.md, USER.md, AGENTS.md, HEARTBEAT.md, TOOLS.md) are the
5 nanobot-managed files whose final content is composed of two parts:

    <workspace-level user template>
    <unique boundary marker>
    <per-agent override>

Both parts are optional. The boundary marker is a fenced HTML comment that is
unlikely to collide with user-authored content (plain `---` hrules are common
in markdown and cannot be used as a reliable splitter).

The same module is used on both ends of the lifecycle:

- `assemble()` builds the file content shipped into the sandbox workspace
  (called from `vm_payload.build_vm_payload`)
- `extract_override()` splits a sandbox-persisted file back into just the
  override portion so the template is never duplicated on the next start
  (called from `sandbox._read_workspace_files` on stop/sync)

If the marker is absent after a sandbox stop, the file is treated as
pure override (no template was attached when it started, or the agent
detached the template mid-session). This is the safe default.
"""

from __future__ import annotations

# Maps template_type (from user_templates.template_type) to the nanobot
# runtime filename it controls. The 5 types here are a closed set enforced
# in `entrypoint/mcp/templates.py` and in the DB check constraint.
RUNTIME_FILES: dict[str, str] = {
    "user": "USER.md",
    "soul": "SOUL.md",
    "agents": "AGENTS.md",
    "heartbeat": "HEARTBEAT.md",
    "tools": "TOOLS.md",
}

RUNTIME_PATHS: frozenset[str] = frozenset(RUNTIME_FILES.values())

# Fenced HTML comment — survives as a comment in markdown rendering, is unique
# enough that collision with user content is vanishingly unlikely, and carries
# a DO-NOT-EDIT hint for any LLM that reads the file (Dream / agent).
BOUNDARY_MARKER = "<!--- OFFICECLAW:TEMPLATE_BOUNDARY:DO-NOT-EDIT --->"


def assemble(template: str | None, override: str | None) -> str | None:
    """Compose a runtime-file body from workspace template + agent override.

    Returns None when both parts are missing (caller should skip writing the
    file). If only one part is present, it is returned unchanged — the marker
    is only emitted when both sides exist, so a sandbox that never had a
    template attached will sync cleanly as a pure override.
    """
    if template and override:
        return f"{template}\n{BOUNDARY_MARKER}\n{override}"
    if template:
        return template
    if override:
        return override
    return None


def extract_override(content: str) -> str:
    """Return the override portion of a runtime-file body.

    If the marker is present, everything after the first occurrence is the
    override. If absent, the whole body is treated as override — this is what
    lets the "no template attached" case round-trip without special handling.

    The split strips exactly one leading newline after the marker so that
    `assemble(t, o) -> extract_override(...)` returns `o` unchanged.
    """
    idx = content.find(BOUNDARY_MARKER)
    if idx == -1:
        return content
    after = content[idx + len(BOUNDARY_MARKER):]
    if after.startswith("\n"):
        after = after[1:]
    return after
