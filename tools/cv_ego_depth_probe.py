#!/usr/bin/env python3
"""Read-only probe of on-board stereo / OpenCV / NPU. Does not kill cameras."""
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
echo === python cv ===
python3 -c "import cv2,numpy; print('cv2',cv2.__version__,'np',numpy.__version__); print('sgbm',hasattr(cv2,'StereoSGBM_create'))" 2>&1
echo === opencv libs ===
ls /usr/lib /usr/lib64 /oem/usr/lib 2>/dev/null | grep -i opencv | head
echo === rknn / mpi / stereo ===
ls /oem/usr/bin /usr/bin 2>/dev/null | grep -iE 'rknn|stereo|depth|sgbm|opencv|rga|mpi' | head -40
echo === python pkgs ===
python3 -c "import sys; print(sys.version)" 2>&1
ls /usr/lib/python3*/site-packages /usr/lib/python3* 2>/dev/null | head
echo === cpu ===
grep -E 'processor|model name' /proc/cpuinfo | head
cat /proc/loadavg
echo === mem ===
free
echo === cameras still ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg|ego_imu' | grep -v grep
echo === video ===
ls /dev/video24 /dev/video32 2>/dev/null
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
