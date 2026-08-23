#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "/userdata/pylib")
print("path", sys.path[0])
try:
    import numpy

    print("numpy", numpy.__version__)
except Exception as exc:
    print("numpy fail", type(exc).__name__, exc)
try:
    import cv2

    print("cv2", cv2.__version__)
except Exception as exc:
    print("cv2 fail", type(exc).__name__, exc)
print("pylib", os.listdir("/userdata/pylib")[:20] if os.path.isdir("/userdata/pylib") else "missing")
