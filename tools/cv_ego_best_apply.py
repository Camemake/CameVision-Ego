#!/usr/bin/env python3
import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
IQ = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\live\sc233hgs_efference-sc233hgs_best.json")
NAME = "sc233hgs_efference-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def sh(s: str, cmd: str, timeout: int = 35) -> None:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    print((r.stdout or "") + (r.stderr or ""), end="" if (r.stdout or "").endswith("\n") else "\n")


def main() -> int:
    s = serial()
    subprocess.run([ADB, "-s", s, "push", str(IQ), "/userdata/iqfiles/" + NAME], check=True)
    sh(
        s,
        "cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s || "
        "(mount -o remount,rw /oem && cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s); "
        "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; "
        "export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH; "
        "start-stop-daemon -S -b -m -p /userdata/rkaiq.pid -x /oem/usr/bin/rkaiq_3A_server -- --silent"
        % (NAME, NAME, NAME, NAME),
    )
    time.sleep(4)
    sh(s, "grep -E 'YNR|CNR|SHARP|ENH|GIC|CAC|DRC' /proc/rkisp-vir0; ps | grep rkaiq_3A | grep -v grep")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
