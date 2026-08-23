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
echo === turbojpeg ===
ls -l /usr/lib/libturbojpeg.so* /lib/libturbojpeg.so* /oem/usr/lib/libturbojpeg.so* 2>/dev/null
echo === tj syms ===
(nm -D /usr/lib/libturbojpeg.so 2>/dev/null || nm -D /lib/libturbojpeg.so 2>/dev/null || objdump -T /usr/lib/libturbojpeg.so 2>/dev/null) | grep -E ' tj|TJ' | head -40
echo === rga ===
ls -l /usr/lib/librga.so* /oem/usr/lib/librga.so* 2>/dev/null
echo === python arch ===
python3 -c "import os,sys,struct; print(sys.maxsize, struct.calcsize('P'), os.uname())"
echo === find lib ===
find /usr /lib /oem -name 'libturbojpeg*' -o -name 'librga.so*' 2>/dev/null | head
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
