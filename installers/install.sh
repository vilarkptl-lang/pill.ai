#!/usr/bin/env bash
# pill.ai — one-click installer for Linux / macOS
# Usage: curl -sSL https://get.pill.ai | bash
#    or: bash install.sh [--key PILLAI-XXXX-XXXX-XXXX-XXXX]
set -euo pipefail

REPO="https://github.com/vilarkptl-lang/pill.ai"
MIN_PYTHON="3.12"
LICENSE_KEY=""

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --key) LICENSE_KEY="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo ""
echo "  ██████╗ ██╗██╗     ██╗      █████╗ ██╗"
echo "  ██╔══██╗██║██║     ██║     ██╔══██╗██║"
echo "  ██████╔╝██║██║     ██║     ███████║██║"
echo "  ██╔═══╝ ██║██║     ██║     ██╔══██║██║"
echo "  ██║     ██║███████╗███████╗██║  ██║██║"
echo "  ╚═╝     ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝"
echo ""
echo "  Ultra-cheap multi-agent computer AI"
echo ""

# Check Python version
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python $MIN_PYTHON+ from https://python.org"
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_MAJOR=3
REQUIRED_MINOR=12
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt "$REQUIRED_MAJOR" || ("$PY_MAJOR" -eq "$REQUIRED_MAJOR" && "$PY_MINOR" -lt "$REQUIRED_MINOR") ]]; then
  echo "ERROR: Python $MIN_PYTHON+ required (found $PY_VERSION)"
  exit 1
fi
echo "✓ Python $PY_VERSION"

# Create venv
INSTALL_DIR="$HOME/.pill.ai/app"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
echo "✓ Virtual environment created"

# Clone / update repo
if [[ -d "$INSTALL_DIR/src/.git" ]]; then
  echo "  Updating existing installation..."
  git -C "$INSTALL_DIR/src" pull --ff-only
else
  git clone --depth=1 "$REPO" "$INSTALL_DIR/src"
fi
echo "✓ Source code ready"

# Install dependencies
pip install --quiet --upgrade pip
pip install --quiet -e "$INSTALL_DIR/src[dashboard]"
echo "✓ Dependencies installed"

# Install Playwright browsers
python3 -m playwright install chromium --with-deps 2>/dev/null || true
echo "✓ Browser installed"

# Activate license if provided
if [[ -n "$LICENSE_KEY" ]]; then
  pillai activate "$LICENSE_KEY"
fi

# Create shell shortcut
SHELL_RC="$HOME/.bashrc"
[[ -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"

if ! grep -q "pill.ai" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# pill.ai" >> "$SHELL_RC"
  echo "export PATH=\"$INSTALL_DIR/venv/bin:\$PATH\"" >> "$SHELL_RC"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  pill.ai installed successfully!"
echo ""
echo "  Start:    pillai"
echo "  Activate: pillai activate <YOUR-KEY>"
echo "  Status:   pillai status"
echo "  Pricing:  https://pill.ai/pricing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Restart your terminal or run: source $SHELL_RC"
echo ""
