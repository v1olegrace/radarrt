"""Compatibility wrapper for the packaged RadarRT CLI.

Prefer `radarrt-indicadores` after `pip install -e .`. This file stays at the
repository root because the hackathon workflow already references it directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from radarrt.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
