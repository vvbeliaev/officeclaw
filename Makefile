.PHONY: run nanobot browser

nanobot:
	uv sync --upgrade-package nanobot-ai

browser:
	bash scripts/start-browser.sh

agency:
	uv run nanobot gateway --config ./.nanobot/digital-agency/config.json