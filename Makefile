AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

infra:
	docker compose -f compose.local.yml up -d db registry

dev-api:
	cd api && uv run uvicorn src.entrypoint.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

api:
	docker compose -f compose.local.yml up -d db registry api web

vm-build:
	docker build --no-cache -t $(AGENT_IMAGE) ./sandbox/
	docker push $(AGENT_IMAGE)
