AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

infra:
	docker compose -f compose.local.yml up -d db registry

dev:
	cd api && uv run uvicorn src.entrypoint.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

dev-api:
	docker compose -f compose.local.yml up -d db registry api web

agent-build:
	docker build -t $(AGENT_IMAGE) ./sandbox/
	docker push $(AGENT_IMAGE)