#!/usr/bin/env python3
import subprocess
import time

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"


def sh(cmd: str, timeout: int = 30) -> str:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    print(out, end="" if out.endswith("\n") else "\n")
    return out


sh(
    "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; "
    "export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
    "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH; "
    "start-stop-daemon -S -b -m -p /userdata/rkaiq.pid -x /oem/usr/bin/rkaiq_3A_server -- --silent; "
    "echo pidfile; cat /userdata/rkaiq.pid"
)
time.sleep(4)
sh(
    "echo === ps ===; ps | grep -E 'rkaiq_3A|ego_mjpeg' | grep -v grep; "
    "echo === sysctl ===; grep sysctl /userdata/rkaiq.log | tail -8; "
    "echo === hw ===; grep -E 'YNR|CNR|SHARP|ENH|GIC|CAC|DRC' /proc/rkisp-vir0; "
    "echo === logerr ===; grep -E 'ERR|error|fail' /userdata/rkaiq.log | tail -15"
)
