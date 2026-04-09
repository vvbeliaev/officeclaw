build:
	docker compose -f compose.local.yml build

infra:
	docker compose -f compose.local.yml up -d db