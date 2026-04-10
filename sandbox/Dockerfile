FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir git+https://github.com/vvbeliaev/nanobot.git@officeclaw

EXPOSE 18790

WORKDIR /workspace

ENTRYPOINT ["nanobot"]
CMD ["gateway", "--config", "/workspace/config.json", "--workspace", "/workspace"]
