#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    print("serial", s)
    cmd = r"""
which ffmpeg ffplay python3 python 2>/dev/null
ls /usr/bin/ffmpeg /oem/usr/bin/ffmpeg 2>/dev/null
echo === ps ===
ps | grep -v grep | grep -E 'v4l2|ffmpeg|hw_rtsp|rkaiq' || true
echo === cif ===
for p in rkcif-mipi-lvds rkcif-mipi-lvds2; do
  echo -- $p --
  for d in /sys/devices/platform/$p/video4linux/video* /sys/devices/platform/$p/*/video4linux/video*; do
    [ -f $d/name ] && echo $(basename $d) $(cat $d/name)
  done
done
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
