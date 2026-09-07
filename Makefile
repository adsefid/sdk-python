.PHONY: deps fmt lint build
deps:
	pip install -e ".[dev]"
fmt:
	ruff format .
lint:
	ruff check . && ruff format --check . && mypy src/adsefid
build:
	python -m build
