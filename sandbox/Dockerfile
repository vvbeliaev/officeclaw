FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# ── Core system + CLI tools ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # network
    curl wget ca-certificates gnupg \
    # vcs
    git git-lfs \
    # text / file tools
    jq ripgrep fd-find fzf bat tree \
    # data processing
    miller sqlite3 \
    # document / media
    pandoc poppler-utils imagemagick ffmpeg \
    # archives
    zip unzip tar gzip bzip2 xz-utils \
    # shell / terminal
    zsh tmux vim nano \
    # system
    htop procps lsof watch \
    # http
    httpie \
    # parallel execution
    parallel \
    # build tools (needed for packages with C extensions)
    build-essential cmake pkg-config \
    # python
    python3 python3-dev \
    # go (Ubuntu 24.04 ships 1.22)
    golang-go \
    && rm -rf /var/lib/apt/lists/* \
    # Ubuntu renames these — expose canonical names
    && ln -sf /usr/bin/fdfind /usr/local/bin/fd \
    && ln -sf /usr/bin/batcat /usr/local/bin/bat

# ── GitHub CLI ─────────────────────────────────────────────────────────────────
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js LTS (22) ───────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── uv (fast Python package manager) ──────────────────────────────────────────
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ── yq (YAML processor) ────────────────────────────────────────────────────────
RUN curl -fsSL https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 \
        -o /usr/local/bin/yq \
    && chmod +x /usr/local/bin/yq

# ── DuckDB ─────────────────────────────────────────────────────────────────────
RUN curl -fsSL https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-amd64.zip \
        -o /tmp/duckdb.zip \
    && unzip /tmp/duckdb.zip duckdb -d /usr/local/bin \
    && rm /tmp/duckdb.zip \
    && chmod +x /usr/local/bin/duckdb

# ── Python packages (system-wide via uv) ──────────────────────────────────────
RUN uv pip install --system --break-system-packages \
    httpx pydantic requests \
    csvkit \
    git+https://github.com/vvbeliaev/nanobot.git@officeclaw

# ── Named-volume paths (no-op if volume not mounted) ──────────────────────────
ENV PATH="/opt/packages/bin:/opt/packages/node/bin:$PATH"
ENV PYTHONPATH="/opt/packages/py"

EXPOSE 18790

WORKDIR /workspace

ENTRYPOINT ["nanobot"]
CMD ["gateway", "--config", "/workspace/config.json", "--workspace", "/workspace"]
