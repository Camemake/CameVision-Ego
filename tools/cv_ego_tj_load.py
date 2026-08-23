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
echo === libc ===
ls -l /lib/libc.so* /lib/ld-linux* /lib64/ld-linux* /lib/ld-musl* 2>/dev/null
echo === tj load ===
python3 - <<'PY'
from ctypes import *
lib=CDLL('/oem/usr/lib/libturbojpeg.so')
print('loaded', lib)
for n in ['tjInitCompress','tjCompressFromYUV','tjCompressFromYUVPlanes','tjCompress2','tjDestroy','tjFree','tjGetErrorStr','tj3Init','tjInitDecompress']:
    try:
        getattr(lib, n)
        print('ok', n)
    except AttributeError:
        print('no', n)
h=lib.tjInitCompress()
print('handle', h)
lib.tjDestroy(h)
print('destroy ok')
PY
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
