#!/usr/bin/env python3
"""Default CameVision Ego Maskrom flash (alias of tools/cv_ego_flash.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv_ego_flash

if __name__ == "__main__":
    raise SystemExit(cv_ego_flash.main())
