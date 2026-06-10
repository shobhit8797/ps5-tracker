#!/usr/bin/env python3
"""PS5 availability tracker - entrypoint.

Usage:
    python run.py                 # run all checks, notify per config
    python run.py --dry-run       # run checks, print report, DON'T send Telegram
    python run.py --test-telegram # send a test message and exit
    python run.py --platform amazon --platform zepto   # only these platforms
"""

from __future__ import annotations

import sys

from ps5tracker.cli import main


if __name__ == "__main__":
    sys.exit(main())
