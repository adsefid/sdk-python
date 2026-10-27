# Targets run through uv. CI installs the dev extra with pip and overrides
# RUN= and BUILD= to call the tools directly.
RUN ?= uv run --extra dev
BUILD ?= uv build

.PHONY: deps fmt lint build test
deps:
	uv sync --extra dev
fmt:
	$(RUN) ruff format .
lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) mypy src/adsefid
build:
	$(BUILD)
test:
	$(RUN) pytest
