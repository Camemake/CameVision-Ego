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
echo === py ===
python3 -c "import sys; print(sys.version)"
ldd --version 2>&1 | head -1
echo === ffmpeg enc ===
ffmpeg -hide_banner -encoders 2>/dev/null | grep -iE 'mjpeg|jpeg|h264|mpp|rga|vpu' | head -20
echo === video jpeg ===
ls /dev/video* 2>/dev/null
echo === libs ===
ls /usr/lib /lib /oem/usr/lib 2>/dev/null | grep -iE 'rga|mpp|jpeg|turbo|opencl|mali' | head -30
echo === load ===
cat /proc/loadavg
nproc
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
