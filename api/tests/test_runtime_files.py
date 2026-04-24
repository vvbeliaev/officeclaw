# api/tests/test_runtime_files.py
"""Unit tests for runtime-file assemble/extract — round-trip and edge cases.

These are pure functions over strings; no DB / fixtures needed.
"""
from src.fleet.core.runtime_files import (
    BOUNDARY_MARKER,
    RUNTIME_FILES,
    RUNTIME_PATHS,
    assemble,
    extract_override,
)


def test_assemble_both_parts_uses_marker():
    result = assemble("TPL", "OV")
    assert result == f"TPL\n{BOUNDARY_MARKER}\nOV"


def test_assemble_template_only():
    assert assemble("TPL", None) == "TPL"
    assert assemble("TPL", "") == "TPL"


def test_assemble_override_only():
    assert assemble(None, "OV") == "OV"
    assert assemble("", "OV") == "OV"


def test_assemble_both_empty_returns_none():
    assert assemble(None, None) is None
    assert assemble("", "") is None


def test_extract_override_strips_template_and_marker():
    body = f"TPL\n{BOUNDARY_MARKER}\nOV"
    assert extract_override(body) == "OV"


def test_extract_override_no_marker_returns_whole_body():
    """No marker → sandbox started without a template; persist everything."""
    assert extract_override("OV only") == "OV only"


def test_round_trip_both_parts():
    """assemble → extract yields the original override verbatim."""
    override = "# Agent override\nLine 2\n\nmore"
    assembled = assemble("TPL", override)
    assert assembled is not None
    assert extract_override(assembled) == override


def test_round_trip_multiline_template():
    template = "# Shared\n\n- rule 1\n- rule 2"
    override = "specific"
    assembled = assemble(template, override)
    assert assembled is not None
    assert extract_override(assembled) == override


def test_round_trip_override_only():
    """When only override exists, round-trip preserves it."""
    assembled = assemble(None, "pure override")
    assert assembled is not None
    assert extract_override(assembled) == "pure override"


def test_marker_is_unique_not_plain_hrule():
    """Markdown `---` hrules must NOT be mistaken for the boundary marker."""
    body = "section one\n\n---\n\nsection two"
    # No boundary marker present → whole body is the override.
    assert extract_override(body) == body


def test_override_containing_marker_is_preserved_after_first_occurrence():
    """If a user somehow embeds the marker in their override (shouldn't happen
    in practice), split is on the FIRST occurrence only so nothing is silently
    truncated after a round-trip — subsequent occurrences survive untouched."""
    override_with_marker = f"before\n{BOUNDARY_MARKER}\nafter"
    assembled = assemble("TPL", override_with_marker)
    assert assembled is not None
    # Extract keeps only the FIRST split — original override re-emerges intact.
    assert extract_override(assembled) == override_with_marker


def test_runtime_paths_match_runtime_files_values():
    assert RUNTIME_PATHS == frozenset(RUNTIME_FILES.values())
    assert "SOUL.md" in RUNTIME_PATHS
    assert "USER.md" in RUNTIME_PATHS
    assert "AGENTS.md" in RUNTIME_PATHS
    assert "HEARTBEAT.md" in RUNTIME_PATHS
    assert "TOOLS.md" in RUNTIME_PATHS
