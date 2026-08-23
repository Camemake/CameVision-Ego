#!/usr/bin/env python3
"""Push best linear IQ and restart 3A only. Does not touch Knee HDR or rockit."""
from __future__ import annotations

import subprocess
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
IQ = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\live\sc233hgs_efference-sc233hgs_best.json")
NAME = "sc233hgs_efference-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    subprocess.run([ADB, "-s", s, "push", str(IQ), "/userdata/iqfiles/" + NAME], check=True)
    cmd = (
        "cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s || "
        "(mount -o remount,rw /oem && cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s); "
        "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; sleep 1; "
        "sh /userdata/camevision-aiq.sh; "
        "killall rkaiq_tool_server 2>/dev/null; true; "
        "echo === hw ===; "
        "grep -E 'YNR|CNR|SHARP|ENH|GIC|CAC|DRC|HDRMGE|DEBAYER|LSC|CCM' /proc/rkisp-vir0; "
        "echo === 3A ===; ps | grep rkaiq_3A | grep -v grep" % (NAME, NAME, NAME, NAME)
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=40)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
