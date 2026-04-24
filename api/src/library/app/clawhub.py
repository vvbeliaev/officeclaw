"""ClawHub importer — pure Python, no shell-out.

Fetches a skill from https://clawhub.ai via its public JSON + zip endpoints,
unpacks in-memory, and fans out into `skills` + `skill_files`.

API shape (verified against clawhub 0.9.0 CLI source):
  GET /api/v1/skills/{slug}                         -> metadata JSON
  GET /api/v1/download?slug={slug}&version={v}      -> zip archive
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass

import httpx

_CLAWHUB_BASE = "https://clawhub.ai"
_CLAWHUB_URL_RE = re.compile(r"^https?://clawhub\.ai/([a-z0-9-]+)/([a-z0-9-]+)/?$")

# Bomb guards. Keep generous for skills with many reference/asset files but
# tight enough that a hostile archive can't wedge the server.
_MAX_ZIP_BYTES = 5 * 1024 * 1024           # 5 MiB archive
_MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024  # 20 MiB total uncompressed
_MAX_PER_FILE_BYTES = 512 * 1024            # 512 KiB per file
_MAX_FILES = 200
_HTTP_TIMEOUT = 20.0

# _meta.json is ClawHub-internal metadata — the agent runtime never reads it.
_SKIP_FILES = {"_meta.json"}


class ClawhubImportError(ValueError):
    """User-facing import failure. Message is safe to surface in HTTP responses."""


@dataclass(frozen=True)
class ParsedUrl:
    owner: str
    slug: str


def parse_url(url: str) -> ParsedUrl:
    match = _CLAWHUB_URL_RE.match(url.strip())
    if not match:
        raise ClawhubImportError(
            "Expected a ClawHub skill URL like https://clawhub.ai/<owner>/<slug>"
        )
    return ParsedUrl(owner=match.group(1), slug=match.group(2))


def _is_safe_path(path: str) -> bool:
    """Reject absolute paths and traversal attempts."""
    if not path or path.startswith(("/", "\\")):
        return False
    parts = path.replace("\\", "/").split("/")
    return not any(part in ("", "..") for part in parts)


@dataclass(frozen=True)
class ClawhubSkill:
    name: str
    description: str
    version: str
    files: tuple[tuple[str, str], ...]  # (path, content)


async def fetch(url: str) -> ClawhubSkill:
    """Fetch and parse a skill from ClawHub. Does no DB writes."""
    parsed = parse_url(url)

    async with httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT,
        follow_redirects=False,  # pinned host — no redirect-based SSRF
    ) as client:
        meta = await _fetch_meta(client, parsed.slug)
        if meta.get("owner", {}).get("handle") != parsed.owner:
            actual = meta.get("owner", {}).get("handle", "<unknown>")
            raise ClawhubImportError(
                f"Slug '{parsed.slug}' is owned by '{actual}', not '{parsed.owner}'"
            )

        version = meta.get("latestVersion", {}).get("version")
        if not version:
            raise ClawhubImportError("Skill has no published version")

        zip_bytes = await _fetch_zip(client, parsed.slug, version)

    skill_info = meta.get("skill", {})
    name = skill_info.get("slug") or parsed.slug
    description = skill_info.get("summary") or ""
    files = _unpack(zip_bytes)
    return ClawhubSkill(
        name=name, description=description, version=version, files=files,
    )


async def _fetch_meta(client: httpx.AsyncClient, slug: str) -> dict:
    response = await client.get(f"{_CLAWHUB_BASE}/api/v1/skills/{slug}")
    if response.status_code == 404:
        raise ClawhubImportError(f"Skill '{slug}' not found on ClawHub")
    response.raise_for_status()
    return response.json()


async def _fetch_zip(client: httpx.AsyncClient, slug: str, version: str) -> bytes:
    response = await client.get(
        f"{_CLAWHUB_BASE}/api/v1/download",
        params={"slug": slug, "version": version},
    )
    if response.status_code == 404:
        raise ClawhubImportError(f"Version {version} of '{slug}' not available")
    response.raise_for_status()

    data = response.content
    if len(data) > _MAX_ZIP_BYTES:
        raise ClawhubImportError("Skill archive exceeds 5 MiB limit")
    return data


def _unpack(zip_bytes: bytes) -> tuple[tuple[str, str], ...]:
    files: list[tuple[str, str]] = []
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.filename in _SKIP_FILES:
                    continue
                if not _is_safe_path(info.filename):
                    raise ClawhubImportError(
                        f"Unsafe path in archive: {info.filename!r}"
                    )
                if info.file_size > _MAX_PER_FILE_BYTES:
                    raise ClawhubImportError(
                        f"File {info.filename!r} exceeds 512 KiB limit"
                    )
                total += info.file_size
                if total > _MAX_UNCOMPRESSED_BYTES:
                    raise ClawhubImportError("Archive uncompresses beyond 20 MiB")
                if len(files) >= _MAX_FILES:
                    raise ClawhubImportError(
                        f"Archive contains more than {_MAX_FILES} files"
                    )
                content = zf.read(info).decode("utf-8", errors="replace")
                files.append((info.filename, content))
    except zipfile.BadZipFile as exc:
        raise ClawhubImportError("Archive is not a valid zip file") from exc
    if not files:
        raise ClawhubImportError("Archive contains no importable files")
    return tuple(files)
