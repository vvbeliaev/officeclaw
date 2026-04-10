FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://install.microsandbox.dev | sh

# msb installer may put binary in ~/.local/bin or /usr/local/bin
ENV PATH="/root/.local/bin:${PATH}"

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.entrypoint.main:app", "--host", "0.0.0.0", "--port", "8000"]
