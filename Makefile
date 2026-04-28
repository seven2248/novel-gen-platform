.PHONY: test install lint clean

# Install all dependencies in editable mode
install:
	pip install -e .

# Run full test suite
test:
	pytest -v

# Run with coverage (if installed)
test-cov:
	pytest -v --cov=. --cov-report=term-missing

# Lint (ruff if available)
lint:
	ruff check .

# Clean cache files
clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf packages/**/__pycache__
	rm -rf services/**/__pycache__
	rm -rf tests/**/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
