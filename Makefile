.PHONY: install run test lint clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PILLAI := $(VENV)/bin/pillai

# Guard: all targets except 'install' and 'clean' require an active venv
check-venv:
	@python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || \
		(echo "ERROR: activate the virtualenv first: source .venv/bin/activate" && exit 1)

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -e .
	@echo ""
	@echo "Done. Run: source .venv/bin/activate && pillai status"

run: check-venv
	pillai

test: check-venv
	pytest tests/ -v

lint: check-venv
	ruff check . --select E,F,W --ignore E501

clean:
	rm -rf $(VENV) *.egg-info __pycache__
