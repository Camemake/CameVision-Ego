#!/usr/bin/env python3
"""Push DRC IQ, restart 3A, enable sensor Knee Point HDR. USB stays ADB."""
from __future__ import annotations

import subprocess
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
IQ = ROOT / "build" / "live" / "sc233hgs_efference-sc233hgs_drc.json"
HDR = ROOT / "tools" / "ego_hdr_on.py"
IQNAME = "sc233hgs_efference-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 40) -> str:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    print(out, end="" if out.endswith("\n") else "\n")
    return out


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    if not IQ.is_file():
        raise SystemExit("missing " + str(IQ))
    print("push IQ + hdr script", flush=True)
    subprocess.run([ADB, "-s", s, "push", str(IQ), "/userdata/iqfiles/" + IQNAME], check=True)
    subprocess.run([ADB, "-s", s, "push", str(HDR), "/userdata/ego_hdr_on.py"], check=True)
    sh(
        s,
        "sed -i 's/\\r$//' /userdata/ego_hdr_on.py; "
        "cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s 2>/dev/null || "
        "(mount -o remount,rw /oem; cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s); "
        "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; sleep 1; "
        "sh /userdata/camevision-aiq.sh; "
        "killall rkaiq_tool_server 2>/dev/null; true" % (IQNAME, IQNAME, IQNAME, IQNAME),
        timeout=35,
    )
    print("enable sensor knee HDR", flush=True)
    sh(s, "python3 /userdata/ego_hdr_on.py", timeout=15)
    sh(
        s,
        "echo === modules ===; "
        "grep -E 'Module drc|Module MERGE|Module mge|sysctl_start' /userdata/rkaiq.log | tail -20",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
