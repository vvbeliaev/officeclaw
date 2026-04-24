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
    csvkit

# ── nanobot (vendored from monorepo) ──────────────────────────────────────────
COPY pkgs/py/nanobot /opt/nanobot
RUN uv pip install --system --break-system-packages /opt/nanobot

# ── humanize-browser (vendored from monorepo) ─────────────────────────────────
# Firefox runtime libs (shared by camoufox's patched Firefox binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2t64 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libdbus-glib-1-2 \
    libdrm2 libgbm1 libgtk-3-0t64 libnspr4 libnss3 libpango-1.0-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 \
    libxt6t64 libvpx9 libevent-2.1-7t64 libgl1 \
    libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 \
    fonts-liberation fonts-unifont \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY pkgs/py/humanize-browser /opt/humanize-browser
RUN uv pip install --system --break-system-packages /opt/humanize-browser \
    # download camoufox's patched Firefox + GeoIP DB into the image
    && python3 -m camoufox fetch

# ── Named-volume paths (no-op if volume not mounted) ──────────────────────────
ENV PATH="/opt/packages/bin:/opt/packages/node/bin:$PATH"
ENV PYTHONPATH="/opt/packages/py"

EXPOSE 18790

WORKDIR /workspace

ENTRYPOINT ["nanobot"]
CMD ["gateway", "--config", "/workspace/config.json", "--workspace", "/workspace"]
