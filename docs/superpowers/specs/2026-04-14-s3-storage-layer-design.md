# S3 Storage Layer Design

**Date:** 2026-04-14  
**Status:** Approved

## Overview

Replace the local filesystem volume mount for agent avatar uploads with a proper S3-compatible storage abstraction. Add MinIO to `compose.local.yml` for local development. Introduce `StoragePort` in `src/shared/storage/` so any hexagonal domain can write to object storage via a single, swappable interface.

## Goals

- Agent avatars stored in S3-compatible object storage (MinIO locally, any S3-compatible in production)
- Generic `StoragePort` Protocol in `src/shared/` — any domain can request it via DI
- Storage configured entirely via env vars — no hardcoded paths or endpoints
- Public bucket, direct URLs — browser fetches files straight from MinIO/S3
- No fallback to filesystem — missing env vars = startup failure with a clear error

## Infrastructure

### compose.local.yml changes

Add two services, remove `./api/uploads` volume from `api`:

```yaml
minio:
  image: minio/minio
  ports:
    - "9000:9000"   # S3 API
    - "9001:9001"   # Web console
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  command: server /data --console-address ":9001"
  volumes:
    - ./minio:/data
  restart: unless-stopped

minio-init:
  image: minio/mc
  depends_on:
    - minio
  entrypoint: >
    /bin/sh -c "
      sleep 2 &&
      mc alias set local http://minio:9000 minioadmin minioadmin &&
      mc mb --ignore-existing local/officeclaw &&
      mc anonymous set public local/officeclaw
    "
  restart: on-failure
```

`minio-init` is a one-shot container: creates bucket `officeclaw` and sets it to public anonymous read.

## Configuration

Five new fields in `api/src/shared/config.py`:

| Env var | Example (local) | Purpose |
|---|---|---|
| `STORAGE_ENDPOINT` | `http://minio:9000` | S3 API endpoint (internal, for API→MinIO) |
| `STORAGE_ACCESS_KEY` | `minioadmin` | S3 access key |
| `STORAGE_SECRET_KEY` | `minioadmin` | S3 secret key |
| `STORAGE_BUCKET` | `officeclaw` | Bucket name |
| `STORAGE_PUBLIC_BASE_URL` | `http://localhost:9000/officeclaw` | Base URL for public object URLs (browser-facing) |

`STORAGE_ENDPOINT` and `STORAGE_PUBLIC_BASE_URL` are intentionally separate: inside Docker containers communicate via `http://minio:9000`, but browsers need `http://localhost:9000`.

All fields are required strings. Missing any → `pydantic_settings` raises `ValidationError` at startup.

## Storage Abstraction

### `src/shared/storage/port.py`

```python
from typing import Protocol

class StoragePort(Protocol):
    async def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    async def delete_object(self, key: str) -> None: ...
    def public_url(self, key: str) -> str: ...
```

Three methods cover all current and foreseeable use cases. `public_url` is synchronous — it is pure string concatenation: `f"{self._public_base_url}/{key}"`.

### `src/shared/storage/s3.py`

`S3Storage` implements `StoragePort` using `aiobotocore` (native async S3 client):

```python
class S3Storage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_base_url: str,
    ) -> None: ...

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        # aiobotocore session → client.put_object(Bucket=..., Key=key, Body=data, ContentType=content_type)

    async def delete_object(self, key: str) -> None:
        # client.delete_object(Bucket=..., Key=key)

    def public_url(self, key: str) -> str:
        return f"{self._public_base_url}/{key}"
```

`aiobotocore` sessions are created per-call to avoid context management complexity. The client is cheap to construct.

### `src/shared/storage/__init__.py`

Re-exports `StoragePort` and `S3Storage` for clean imports.

## Wiring

### `src/entrypoint/main.py` — lifespan

```python
from src.shared.storage import S3Storage

storage = S3Storage(
    endpoint=settings.storage_endpoint,
    access_key=settings.storage_access_key,
    secret_key=settings.storage_secret_key,
    bucket=settings.storage_bucket,
    public_base_url=settings.storage_public_base_url,
)

fleet, watcher = fleet_di.build(pool, integrations, library, storage)
```

Remove `StaticFiles` mount and `uploads_dir.mkdir`.

### `src/entrypoint/main.py` — app.state

`storage` is set directly on `app.state` in lifespan (same pattern as `fleet`, `identity`, etc.):

```python
app.state.storage = storage
```

### `src/fleet/adapters/_in/router.py` — dependency

```python
def get_storage(request: Request) -> StoragePort:
    return request.app.state.storage
```

`fleet_di.py` does not need to change for storage — storage is accessed directly from `app.state` by the router, not threaded through the fleet domain facade.

### `src/fleet/adapters/_in/router.py` — upload_avatar

Before:
```python
_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
dest = _AVATAR_DIR / filename
with dest.open("wb") as f:
    shutil.copyfileobj(file.file, f)
avatar_url = f"{base}/static/avatars/{filename}"
```

After:
```python
data = await file.read()
key = f"avatars/{agent_id}{ext}"
await storage.put_object(key, data, file.content_type)
avatar_url = storage.public_url(key)
```

Remove `_AVATAR_DIR` constant, `shutil` import, `Path` import from this file.

## Data Flow

```
Browser → POST /agents/{id}/avatar (multipart)
  → router: read bytes from UploadFile
  → storage.put_object("avatars/{id}.jpg", bytes, "image/jpeg") → MinIO
  → avatar_url = storage.public_url("avatars/{id}.jpg")
             = "http://localhost:9000/officeclaw/avatars/{id}.jpg"
  → fleet.update_agent(id, avatar_url=avatar_url) → Postgres
  → AgentOut returned with new avatar_url

Browser renders <img src="http://localhost:9000/officeclaw/avatars/{id}.jpg">
  → direct request to MinIO, API not involved
```

## Files Changed

| File | Change |
|---|---|
| `compose.local.yml` | Add `minio`, `minio-init` services; remove `./api/uploads` volume from `api` |
| `api/src/shared/config.py` | Add 5 `STORAGE_*` fields |
| `api/src/shared/storage/port.py` | New — `StoragePort` Protocol |
| `api/src/shared/storage/s3.py` | New — `S3Storage` implementation |
| `api/src/shared/storage/__init__.py` | New — re-exports |
| `api/src/entrypoint/main.py` | Wire `S3Storage`, remove `StaticFiles` mount |
| `api/src/entrypoint/main.py` (app.state) | Set `app.state.storage = storage` |
| `api/src/fleet/adapters/_in/router.py` | Rewrite `upload_avatar` to use storage |
| `api/.env` | Add `STORAGE_*` vars |

## Out of Scope

- Presigned URLs
- Local filesystem fallback
- Knowledge graph or agent file storage migration (can adopt `StoragePort` independently later)
- Production deployment configuration
