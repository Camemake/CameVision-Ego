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
echo === dmesg cam1 ===
dmesg | grep -iE 'sc233|dphy1|mipi1|mipi2|lvds1|PHY_SPLIT|6-0030|chip id' | tail -40
echo === videos cif ===
for d in /sys/class/video4linux/video*; do n=$(cat $d/name); echo $(basename $d) $n; done | grep cif
echo === media devices ===
ls /dev/media*
for m in /dev/media0 /dev/media1 /dev/media2 /dev/media3 /dev/media4; do
  echo --- $m ---
  media-ctl -d $m -p 2>/dev/null | grep -E 'entity|sc233|dphy|mipi|lvds' | head -25
done
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
