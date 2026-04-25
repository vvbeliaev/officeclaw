from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/ package root — parents[2] == .../officeclaw/api
_API_ROOT = Path(__file__).resolve().parents[2]
# Repository root — one level above api/.
_REPO_ROOT = _API_ROOT.parent

# Resolve .env relative to api/ so the file is found regardless of the
# process cwd (uvicorn, pytest, scripts, …).
_ENV_PATH = _API_ROOT / ".env"


class Settings(BaseSettings):
    database_url: str
    encryption_key: str
    debug: bool = False
    mcp_base_url: str = "http://localhost:8000"

    # Sandbox runner: "docker" for local dev (macOS/Intel), "msb" for
    # production (microsandbox Python SDK — Linux x86_64/aarch64 or macOS
    # arm64, KVM-backed microVMs). The "msb" runner requires the optional
    # `microsandbox` extra (`pip install -e "./api[microsandbox]"`).
    sandbox_runner: Literal["docker", "msb"] = "msb"

    # Host to reach the nanobot gateway once a sandbox is up.
    # docker runner: "host.docker.internal" when API is inside a container,
    #                "localhost" when API runs natively on the host.
    # msb runner:    "localhost".
    sandbox_gateway_host: str = "localhost"

    # Directory on the host where sandbox workspaces are materialised.
    # Must be a path that the sandbox runner can bind-mount. Defaults to
    # <repo>/.sandboxes so workspaces are visible in the IDE alongside the
    # rest of the source. Git-ignored — see .gitignore.
    sandbox_workdir: str = str(_REPO_ROOT / ".sandboxes")

    # Default LLM settings for new agents — any OpenAI-compatible endpoint.
    # On user bootstrap these are seeded into a user_env called "default-llm",
    # and every agent's generated nanobot config references them via
    # ${OFFICECLAW_LLM_*} so secrets never land in config.json on disk.
    # Leave blank to opt out — user must then configure LLM manually.
    default_llm_api_key: str = ""
    default_llm_base_url: str = ""
    default_llm_model: str = "gpt-4o-mini"

    # Default web-search provider for new agents. Seeded into a per-workspace
    # "default-web-search" env on bootstrap; nanobot's tools.web.search reads
    # ${OFFICECLAW_WEB_SEARCH_*} from sandbox env so keys stay out of config.json.
    # Supported providers: duckduckgo, brave, tavily, searxng, jina.
    # duckduckgo needs no key — leave default_web_search_api_key blank.
    default_web_search_provider: str = "duckduckgo"
    default_web_search_api_key: str = ""

    # Knowledge graph (LightRAG) — LLM for entity extraction at ingest
    knowledge_llm_api_key: str = ""
    knowledge_llm_base_url: str = "https://api.openai.com/v1"
    knowledge_llm_model: str = "gpt-4o-mini"

    # Knowledge graph — embedding model for vector storage
    knowledge_embed_api_key: str = ""
    knowledge_embed_base_url: str = "https://api.openai.com/v1"
    knowledge_embed_model: str = "text-embedding-3-small"
    knowledge_embed_dim: int = 1536

    # Document normalisation — docling-serve base URL
    docling_url: str = "http://localhost:5001"

    # S3-compatible object storage
    storage_endpoint: str
    storage_access_key: str
    storage_secret_key: str
    storage_bucket: str
    storage_public_base_url: str

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH, env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("encryption_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        from cryptography.fernet import Fernet

        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError(
                f"ENCRYPTION_KEY is not a valid Fernet key: {exc}"
            ) from exc
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
