#!/usr/bin/env bash
# Cron-friendly wrapper. Runs one tracking pass.
# Cron has a minimal environment, so we cd to the project and use absolute paths.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Append output to a log so you can debug cron runs.
if command -v uv >/dev/null 2>&1; then
  exec uv run ps5-tracker >> "$PROJECT_DIR/tracker.log" 2>&1
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"
exec python run.py >> "$PROJECT_DIR/tracker.log" 2>&1
