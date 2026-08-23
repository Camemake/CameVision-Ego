#!/usr/bin/env python3
"""On-board: unzip wheels from /userdata/wheels into /userdata/pylib."""
from __future__ import annotations

import pathlib
import sys
import zipfile

dst = pathlib.Path("/userdata/pylib")
dst.mkdir(parents=True, exist_ok=True)
for w in sorted(pathlib.Path("/userdata/wheels").glob("*.whl")):
    if not zipfile.is_zipfile(w):
        print("skip bad", w.name, w.stat().st_size, flush=True)
        continue
    print("extract", w.name, flush=True)
    zipfile.ZipFile(w).extractall(dst)
sys.path.insert(0, "/userdata/pylib")
try:
    import numpy

    print("numpy", numpy.__version__, flush=True)
except Exception as exc:
    print("numpy fail", exc, flush=True)
try:
    import cv2

    print("cv2", cv2.__version__, flush=True)
except Exception as exc:
    print("cv2 missing", exc, flush=True)
