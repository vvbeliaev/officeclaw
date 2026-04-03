.PHONY: run nanobot browser

install:
	uv sync --upgrade-package nanobot-ai

browser:
	bash scripts/start-browser.sh

run:
	uv run nanobot gateway --config ./.nanobot/config.json