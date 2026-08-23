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
echo === numpy gcc rknn ===
python3 -c "import numpy; print(numpy.__version__)" 2>&1
which gcc cc aarch64-linux-gnu-gcc 2>/dev/null
ls /oem/usr/lib | grep -iE 'rknn|opencv|opencl|mali' | head
ls /usr/lib | grep -iE 'rknn|opencv|mali|OpenCL' | head
echo === rknn ===
ls /oem/usr/bin /usr/bin 2>/dev/null | grep -i rknn
find /oem /usr -name '*rknn*' -o -name '*stereo*' 2>/dev/null | head
echo === fmt video24 ===
v4l2-ctl -d /dev/video24 --list-formats-ext 2>/dev/null | head -40
echo === nproc top ===
nproc
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
