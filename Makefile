.PHONY: install run test lint clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PILLAI := $(VENV)/bin/pillai

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -e .
	@echo ""
	@echo "Done. Run: source .venv/bin/activate && pillai status"

run:
	$(PILLAI)

test:
	$(VENV)/bin/pytest tests/ -v

lint:
	$(VENV)/bin/ruff check . --select E,F,W --ignore E501

clean:
	rm -rf $(VENV) *.egg-info
