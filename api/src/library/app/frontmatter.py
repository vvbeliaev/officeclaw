"""SKILL.md frontmatter parse/synthesize.

DB is the source of truth: structured fields live as columns on `skills`.
On sandbox assembly we synthesize a YAML frontmatter block from those
columns and prepend it to the stored SKILL.md body. On writes coming
from outside (ClawHub import, MCP `add_skill_file`) we parse the
incoming frontmatter, split it into known fields + metadata_extra, and
store only the body in skill_files.content.

Known fields (match nanobot's SkillsLoader contract):
    name, description, homepage
    metadata.nanobot.always          -> skills.always
    metadata.nanobot.emoji           -> skills.emoji
    metadata.nanobot.requires.bins   -> skills.required_bins
    metadata.nanobot.requires.env    -> skills.required_envs

Anything else under `metadata` is preserved verbatim in
`skills.metadata_extra` (JSONB) so unknown publisher-specific keys
round-trip without loss. `clawdbot`/`openclaw` are legacy aliases for
`nanobot` — we normalize them to `nanobot` on parse.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# SKILL.md frontmatter is a limited subset of YAML in practice: shallow
# key/value pairs where `metadata` is a single-line JSON object. Keep
# the parser deliberately permissive on this shape and refuse anything
# else so we don't need a full YAML dependency.
_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)
_KV_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
_LEGACY_NAMESPACES = ("clawdbot", "openclaw")


@dataclass(frozen=True)
class Frontmatter:
    """Parsed, normalized frontmatter. All fields have safe defaults."""

    name: str | None = None
    description: str | None = None
    homepage: str | None = None
    always: bool = False
    emoji: str | None = None
    required_bins: tuple[str, ...] = ()
    required_envs: tuple[str, ...] = ()
    metadata_extra: dict[str, Any] = field(default_factory=dict)


def strip_frontmatter(content: str) -> str:
    """Return `content` with a leading `---...---` block removed (if present)."""
    match = _FRONTMATTER_RE.match(content)
    return content[match.end():] if match else content


def parse(content: str) -> tuple[Frontmatter, str]:
    """Parse frontmatter from `content`. Returns (parsed, body_without_frontmatter).

    No-frontmatter input returns (empty Frontmatter, original content).
    Malformed frontmatter silently falls back to no-frontmatter — callers
    don't care about fine-grained parse errors; we'd rather accept a
    file with odd formatting than reject the upload.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return Frontmatter(), content

    raw_fields = _parse_shallow_yaml(match.group(1))
    body = content[match.end():]

    name = raw_fields.get("name")
    description = raw_fields.get("description")
    homepage = raw_fields.get("homepage")

    metadata_raw = raw_fields.get("metadata") or "{}"
    try:
        metadata = json.loads(metadata_raw)
        if not isinstance(metadata, dict):
            metadata = {}
    except (json.JSONDecodeError, TypeError):
        metadata = {}

    # Normalize legacy namespaces into `nanobot`.
    nanobot_meta: dict[str, Any] = dict(metadata.get("nanobot") or {})
    for legacy in _LEGACY_NAMESPACES:
        legacy_meta = metadata.get(legacy)
        if isinstance(legacy_meta, dict):
            for key, value in legacy_meta.items():
                nanobot_meta.setdefault(key, value)

    always = bool(nanobot_meta.get("always") or raw_fields.get("always") == "true")
    emoji = nanobot_meta.get("emoji") or None
    requires = nanobot_meta.get("requires") or {}
    required_bins = tuple(_as_str_list(requires.get("bins")))
    required_envs = tuple(_as_str_list(requires.get("env")))

    # Preserve unknown metadata keys verbatim (and unknown keys inside
    # `nanobot` itself, minus the ones we just absorbed).
    known_nanobot = {"always", "emoji", "requires"}
    nanobot_extra = {k: v for k, v in nanobot_meta.items() if k not in known_nanobot}

    metadata_extra = {
        k: v
        for k, v in metadata.items()
        if k not in ("nanobot", *_LEGACY_NAMESPACES)
    }
    if nanobot_extra:
        metadata_extra["nanobot"] = nanobot_extra

    return (
        Frontmatter(
            name=name,
            description=description,
            homepage=homepage,
            always=always,
            emoji=emoji,
            required_bins=required_bins,
            required_envs=required_envs,
            metadata_extra=metadata_extra,
        ),
        body,
    )


def synthesize(fm: Frontmatter) -> str:
    """Render `fm` as a `---...---` block followed by a trailing newline.

    Returns empty string if no meaningful fields are set (e.g. fresh
    skill with no metadata) — callers should then just emit the body.
    """
    lines: list[str] = []
    if fm.name is not None:
        lines.append(f"name: {fm.name}")
    if fm.description is not None:
        lines.append(f"description: {_yaml_string(fm.description)}")
    if fm.homepage:
        lines.append(f"homepage: {fm.homepage}")

    metadata = dict(fm.metadata_extra)
    nanobot_block: dict[str, Any] = dict(metadata.get("nanobot") or {})
    if fm.always:
        nanobot_block["always"] = True
    if fm.emoji:
        nanobot_block["emoji"] = fm.emoji
    if fm.required_bins or fm.required_envs:
        requires: dict[str, list[str]] = {}
        if fm.required_bins:
            requires["bins"] = list(fm.required_bins)
        if fm.required_envs:
            requires["env"] = list(fm.required_envs)
        nanobot_block["requires"] = requires
    if nanobot_block:
        metadata["nanobot"] = nanobot_block
    if metadata:
        # Single-line JSON — matches ClawHub/nanobot convention.
        # ensure_ascii=False keeps emoji and Unicode characters readable.
        lines.append(
            f"metadata: {json.dumps(metadata, separators=(',', ':'), ensure_ascii=False)}"
        )

    if not lines:
        return ""
    return "---\n" + "\n".join(lines) + "\n---\n"


def prepend(fm: Frontmatter, body: str) -> str:
    """Build the final SKILL.md content to ship to the sandbox."""
    header = synthesize(fm)
    if not header:
        return body
    # Ensure a blank line between the closing `---` and the body for
    # markdown renderers — but avoid a double blank if body already
    # starts with whitespace.
    if body.startswith("\n"):
        return header + body
    return header + "\n" + body if body else header


def _parse_shallow_yaml(source: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in source.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        m = _KV_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        # Strip matching surrounding quotes on simple scalar values.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if isinstance(x, (str, int, float)) and str(x)]
    return []


def _yaml_string(value: str) -> str:
    """Quote a string if necessary so it survives shallow-YAML parsing.

    Single line + no special leading chars → bare. Otherwise wrap in
    double quotes and escape `\\`, `"`, and control characters.
    """
    if "\n" in value or "\r" in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{escaped}"'
    # Leading chars that collide with YAML indicators.
    if value and value[0] in "!&*-?[]{}|>%@`,:#\"'":
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value
