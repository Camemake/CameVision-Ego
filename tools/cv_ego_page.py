#!/usr/bin/env python3
"""Bring the Ego live page back after a USB plug-in.

The stereo service already starts on the board at boot. ADB port forwards
live on the host and are dropped every unplug, so the browser has nothing
to open until this runs.
"""
from __future__ import annotations

import subprocess
import time
import webbrowser
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
PAGE = "http://127.0.0.1:8081/"
CAL = "http://127.0.0.1:8081/cal"


def adb(*args: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, *args], capture_output=True, text=True, timeout=timeout)


def serial() -> str:
    t0 = time.time()
    while time.time() - t0 < 60:
        r = adb("wait-for-device", timeout=20)
        r = adb("devices")
        for line in (r.stdout or "").splitlines():
            if "\tdevice" in line:
                return line.split()[0]
        time.sleep(1)
    raise SystemExit("no ADB device")


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    adb("-s", s, "forward", "tcp:8081", "tcp:8081")
    adb("-s", s, "forward", "tcp:8083", "tcp:8083")
    t0 = time.time()
    while time.time() - t0 < 45:
        chk = adb(
            "-s",
            s,
            "shell",
            "netstat -lnt 2>/dev/null | grep 8081 || ss -lnt | grep 8081",
            timeout=8,
        )
        if "8081" in (chk.stdout or ""):
            break
        time.sleep(1)
    else:
        print("board is up but :8081 is not listening yet", flush=True)
        print("if this is a cold boot, wait a few seconds and run this again", flush=True)
        return 1
    print("forward tcp:8081 tcp:8081", flush=True)
    print("page", PAGE, flush=True)
    print("cal ", CAL, flush=True)
    webbrowser.open(PAGE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
