AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

infra:
	docker compose -f compose.local.yml up -d db registry docling minio minio-init

dev-api:
	cd api && uv run uvicorn src.entrypoint.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

down:
	docker compose -f compose.local.yml down

dev:
	docker compose -f compose.local.yml up -d db registry docling minio minio-init api web

vm-build:
	docker build -t $(AGENT_IMAGE) ./sandbox/
	docker push $(AGENT_IMAGE)

vm-build-cached:
	docker build --no-cache -t $(AGENT_IMAGE) ./sandbox/
	docker push $(AGENT_IMAGE)