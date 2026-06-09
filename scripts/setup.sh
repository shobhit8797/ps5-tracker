#!/usr/bin/env bash
# One-time setup: create venv, install deps, install the Playwright browser.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> Creating virtual environment (.venv)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Installing Playwright Chromium (used for Amazon/Flipkart)"
python -m playwright install chromium

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from template — now edit it and add your Telegram token + chat id."
fi

echo ""
echo "Setup complete. Next:"
echo "  1. Edit .env  (Telegram token + chat id)"
echo "  2. Edit config.yaml  (your locations/pincodes + products)"
echo "  3. Test:   source .venv/bin/activate && python run.py --test-telegram"
echo "  4. Dry run: python run.py --dry-run"
