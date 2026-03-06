.PHONY: help install test lint format clean run

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies"
	@echo "  test       Run tests"
	@echo "  lint       Run linting"
	@echo "  format     Format code"
	@echo "  clean      Clean build artifacts"
	@echo "  run        Run the application"

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	flake8 model_comparison_system tests
	mypy model_comparison_system

format:
	black model_comparison_system tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python -m model_comparison_system.main