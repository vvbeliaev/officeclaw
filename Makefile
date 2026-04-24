AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

migrate:
	cd api && uv run alembic upgrade head

infra:
	docker compose -f compose.local.yml up -d db registry docling minio minio-init

dev-api:
	cd api && uv run uvicorn src.entrypoint.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

down:
	docker compose -f compose.local.yml down

dev: infra migrate
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) dev-api & \
	$(MAKE) dev-web & \
	wait

vm-build:
	docker build -t $(AGENT_IMAGE) -f ./sandbox/Dockerfile .
	docker push $(AGENT_IMAGE)

vm-build-cached:
	docker build --no-cache -t $(AGENT_IMAGE) -f ./sandbox/Dockerfile .
	docker push $(AGENT_IMAGE)