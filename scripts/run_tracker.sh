#!/usr/bin/env bash
# Cron-friendly wrapper. Activates the venv and runs one tracking pass.
# Cron has a minimal environment, so we cd to the project and use absolute paths.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"

# Append output to a log so you can debug cron runs.
exec python run.py >> "$PROJECT_DIR/tracker.log" 2>&1
