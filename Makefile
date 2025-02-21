.PHONY: help setup setup-dev clean format lint test jupyter

help:  ## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

setup:  ## Install production dependencies
	python -m pip install -U pip
	python -m pip install -r requirements.txt

setup-dev: setup  ## Install development dependencies
	python -m pip install -r requirements-dev.txt
	jupyter labextension install @jupyter/ai  # Install Jupyter AI extension

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

format:  ## Format code using black and isort
	black .
	isort .

lint:  ## Run linting checks
	flake8 .
	mypy .
	black . --check
	isort . --check

test:  ## Run tests with coverage
	pytest --cov=. --cov-report=term-missing

jupyter:  ## Start JupyterLab server
	jupyter lab

# Default target
.DEFAULT_GOAL := help 