.PHONY: install run test lint clean exe server

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PILLAI := $(VENV)/bin/pillai

# Guard: all targets except 'install', 'clean', 'exe' require an active venv
check-venv:
	@python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" || \
		(echo "ERROR: activate the virtualenv first: source .venv/bin/activate" && exit 1)

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -e ".[server,dev]"
	@echo ""
	@echo "Done. Run: source .venv/bin/activate && pillai status"

run: check-venv
	pillai

test: check-venv
	pytest tests/ -v

lint: check-venv
	ruff check . --select E,F,W --ignore E501

server: check-venv
	@test -f .env || (echo "ERROR: crea .env primero — bash installers/setup_env.sh" && exit 1)
	env $(cat .env | grep -v '^#' | grep -v '^$$' | xargs) \
		uvicorn licensing.server:app --host 0.0.0.0 --port 8080 --reload

# Build distributable .exe — bakes relay URL into the binary
# Usage: PILLAI_RELAY_URL=https://your-server.com make exe
exe:
	@test -n "$(PILLAI_RELAY_URL)" || (echo "ERROR: set PILLAI_RELAY_URL=https://your-server.com" && exit 1)
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip -q
	$(PIP) install -e ".[server]" pyinstaller -q
	PILLAI_RELAY_URL=$(PILLAI_RELAY_URL) $(PYTHON) installers/build_exe.py
	@echo ""
	@echo "Distributable: dist/pillai  (or dist/pillai.exe on Windows)"

clean:
	rm -rf $(VENV) *.egg-info __pycache__ dist/ build/ interpreter/_relay_config.py
