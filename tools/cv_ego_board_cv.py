#!/usr/bin/env python3
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = r"""
echo === pylib ===
ls /userdata/pylib 2>/dev/null | head
echo === import ===
PYTHONPATH=/userdata/pylib python3 -c "import sys; sys.path.insert(0,'/userdata/pylib');
import numpy as np; print('numpy', np.__version__)"
PYTHONPATH=/userdata/pylib python3 -c "import sys; sys.path.insert(0,'/userdata/pylib');
import cv2; print('cv2', cv2.__version__)"
echo === stat ===
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8081/cal/stat',timeout=5).read()[:500])"
echo === snap ===
python3 -c "import urllib.request; d=urllib.request.urlopen('http://127.0.0.1:8081/snapr0',timeout=5).read(); print('raw0', len(d))"
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
