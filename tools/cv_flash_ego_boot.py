#!/usr/bin/env python3
"""Flash the compiled Ego DTB boot.img over ADB and reboot. USB stays ADB."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = ""
IMG = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\camevision_boot_ego.img")
BAK = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\boot_before_ego.img")
REMOTE = "/userdata/camevision_boot_ego.img"


def adb(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    r = subprocess.run([ADB, "-s", S, *args], capture_output=True, timeout=timeout)
    out = (r.stdout or b"") + (r.stderr or b"")
    text = out.decode("utf-8", "replace")
    if r.returncode != 0:
        raise SystemExit(f"adb {' '.join(args)} failed ({r.returncode})\n{text}")
    return r


def adb_out(*args: str, timeout: int = 30) -> str:
    r = subprocess.run([ADB, "-s", S, *args], capture_output=True, timeout=timeout)
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def main() -> int:
    global S
    S = serial()
    print("serial", S)
    if not IMG.is_file():
        raise SystemExit(f"missing {IMG}")
    print(f"image {IMG} ({IMG.stat().st_size} bytes)")

    model = adb_out("shell", "cat /proc/device-tree/model; echo")
    print("live model:", model.strip())

    print("backing up live boot ->", BAK)
    BAK.parent.mkdir(parents=True, exist_ok=True)
    adb("pull", "/dev/block/by-name/boot", str(BAK), timeout=180)
    print(f"  backup {BAK.stat().st_size} bytes")

    print("pushing Ego boot.img")
    adb("push", str(IMG), REMOTE, timeout=180)

    print("dd to mmcblk0p4")
    r = adb(
        "shell",
        f"dd if={REMOTE} of=/dev/mmcblk0p4 bs=1M conv=fsync; sync; echo DD_OK",
        timeout=180,
    )
    print(r.stdout.decode("utf-8", "replace"), end="")

    print("rebooting")
    subprocess.run([ADB, "-s", S, "reboot"], capture_output=True, timeout=20)

    print("waiting for ADB")
    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(3)
        try:
            listing = adb_out("devices")
        except Exception:
            continue
        if S in listing and "device" in listing:
            model = adb_out("shell", "cat /proc/device-tree/model; echo")
            if "CameVision Ego" in model:
                print(f"up in {time.time()-t0:.0f}s — {model.strip()}")
                return 0
            if model.strip():
                print(f"up but model is still: {model.strip()}")
                return 1
        print(f"  t={time.time()-t0:.0f}s")
    raise SystemExit("board did not return with CameVision Ego DTB")


if __name__ == "__main__":
    raise SystemExit(main())
