from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# MIME types that map to a filename extension docling-serve understands
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/html": ".html",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

# Types that bypass docling-serve entirely — just decode as UTF-8
_PASSTHROUGH: frozenset[str] = frozenset({"text/plain", "text/markdown"})

_ALL_SUPPORTED: frozenset[str] = _PASSTHROUGH | frozenset(_MIME_TO_EXT)

# Generous timeout: complex PDFs can take 30-60 s on CPU
_TIMEOUT = httpx.Timeout(120.0)


class DoclingNormalizer:
    """Converts raw file bytes to Markdown by calling docling-serve.

    Plain text / Markdown bypasses the service entirely.
    All other types are POST-ed to /v1/convert/file and the returned
    md_content is used as input for LightRAG.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def supported_types(self) -> frozenset[str]:
        return _ALL_SUPPORTED

    async def normalize(self, content: bytes, content_type: str, filename: str) -> str:
        if content_type in _PASSTHROUGH:
            return content.decode("utf-8", errors="replace")

        if content_type not in _MIME_TO_EXT:
            logger.warning(
                "DoclingNormalizer: unknown type %s for %s, falling back to UTF-8",
                content_type,
                filename,
            )
            return content.decode("utf-8", errors="replace")

        try:
            return await self._convert(content, content_type, filename)
        except Exception:
            logger.exception(
                "Docling conversion failed for %s, falling back to UTF-8", filename
            )
            return content.decode("utf-8", errors="replace")

    async def _convert(self, content: bytes, content_type: str, filename: str) -> str:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{self._base_url}/v1/convert/file",
                files={"files": (filename, content, content_type)},
                data={"to_formats": "md"},
            )
            response.raise_for_status()

        data = response.json()
        doc = data.get("document") or {}
        md: str = doc.get("md_content", "")
        if not md:
            logger.warning(
                "DoclingNormalizer: empty markdown for %s, falling back to UTF-8", filename
            )
            return content.decode("utf-8", errors="replace")
        return md
