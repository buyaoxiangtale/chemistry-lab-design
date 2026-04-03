.PHONY: install lint test run clean

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src/ tests/

lint-fix:
	$(PYTHON) -m ruff check --fix src/ tests/

test:
	$(PYTHON) -m pytest tests/ -q

run: install
	$(PYTHON) -m chemistry_lab --help

clean:
	rm -rf build/ dist/ src/*.egg-info
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
