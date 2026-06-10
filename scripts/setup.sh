#!/usr/bin/env bash
# One-time setup: sync deps and install the Playwright browser.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

RUN_CMD="uv run ps5-tracker"

if command -v uv >/dev/null 2>&1; then
  echo "==> Syncing Python environment with uv"
  uv sync

  echo "==> Installing Playwright Chromium (used for Amazon/Flipkart)"
  uv run playwright install chromium
else
  echo "==> uv not found; falling back to python -m venv + pip"
  RUN_CMD="source .venv/bin/activate && python run.py"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate

  echo "==> Installing Python dependencies"
  pip install --upgrade pip
  pip install -r requirements.txt

  echo "==> Installing Playwright Chromium (used for Amazon/Flipkart)"
  python -m playwright install chromium
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from template — now edit it and add your Telegram token + chat id."
fi

echo ""
echo "Setup complete. Next:"
echo "  1. Edit .env  (Telegram token + chat id)"
echo "  2. Edit config.yaml  (your locations/pincodes + products)"
echo "  3. Test:   $RUN_CMD --test-telegram"
echo "  4. Dry run: $RUN_CMD --dry-run"
