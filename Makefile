AGENT_IMAGE ?= localhost:5005/officeclaw/agent:latest

infra:
	docker compose -f compose.local.yml up -d db registry

agent-build:
	docker build -t $(AGENT_IMAGE) ./sandbox/
	docker push $(AGENT_IMAGE)