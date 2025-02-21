.PHONY: help setup setup-dev clean format lint test jupyter

help:  ## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

setup:  ## Install production dependencies
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv venv .venv
	. .venv/bin/activate && uv pip install -r requirements.txt

setup-dev: setup  ## Install development dependencies
	. .venv/bin/activate && uv pip install -r requirements-dev.txt

clean:  ## Clean up python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf .venv

format:  ## Format code using black and isort
	. .venv/bin/activate && black . --exclude .venv
	. .venv/bin/activate && isort . --skip .venv

lint:  ## Run linting checks
	. .venv/bin/activate && black . --check --exclude .venv
	. .venv/bin/activate && isort . --check --skip .venv

test:  ## Run tests with coverage
	. .venv/bin/activate && pytest --cov=. --cov-report=term-missing

jupyter:  ## Start JupyterLab server
	. .venv/bin/activate && jupyter lab

# Default target
.DEFAULT_GOAL := help 