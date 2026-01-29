.PHONY: help test lint typecheck format all clean

# Default target
all: format lint typecheck test

help:
	@echo "Available commands:"
	@echo "  make test      - Run tests using pytest"
	@echo "  make lint      - Check for linting issues using ruff"
	@echo "  make typecheck - Check for type safety using mypy"
	@echo "  make format    - Format code using black"
	@echo "  make all       - Run format, lint, typecheck, and test"
	@echo "  make clean     - Remove python cache files"

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy .

format:
	black .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .mypy_cache
