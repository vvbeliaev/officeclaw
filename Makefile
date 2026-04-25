AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

wait-db:
	@echo "Waiting for db to accept TCP connections on 5434..."
	@until docker compose -f compose.local.yml exec -T db pg_isready -U postgres -d officeclaw -h 127.0.0.1 -p 5432 >/dev/null 2>&1; do sleep 1; done
	@echo "db ready"

migrate: wait-db
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