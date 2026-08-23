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
    cmd = r"""
echo === videos ===
for d in /sys/class/video4linux/video*; do echo $(basename $d) $(cat $d/name); done
echo === media cam1 ===
media-ctl -d /dev/media2 -p 2>/dev/null | grep -E 'sc233|csi2|dphy|entity|Enabled|fmt:' | head -40
echo === dmesg csi1 ===
dmesg | grep -iE 'dphy1|mipi1|lvds1|csi2-dphy1|6-0030' | tail -20
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
