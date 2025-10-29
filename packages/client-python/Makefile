.PHONY: build clean install test publish help

help:
	@echo "Available commands:"
	@echo "  make build    - Build dakora-agents and dakora-client packages"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make install  - Install package locally from wheel"
	@echo "  make test     - Run tests"
	@echo "  make publish  - Publish to PyPI"

build: clean
	@echo "Building dakora-agents..."
	cd ../agents && uv build --out-dir ../../dist
	@echo "Building dakora-client..."
	uv build --out-dir ../../dist

clean:
	rm -rf dist/ build/ *.egg-info ../../dist/dakora_client* ../../dist/dakora_agents*
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

install: build
	pip install --force-reinstall ../../dist/dakora_client*.whl

test:
	uv run pytest

publish: build
	uv publish