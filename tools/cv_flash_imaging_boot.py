#!/usr/bin/env python3
"""Flash the last working imaging DTB. Does not overwrite that image."""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
SRC = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\boot_before_ego.img")
IMG = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\boot_imaging_good.img")
BAK = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\boot_before_imaging_flash.img")
REMOTE = "/userdata/boot_imaging_good.img"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def adb(s: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    r = subprocess.run([ADB, "-s", s, *args], capture_output=True, timeout=timeout)
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    if r.returncode != 0:
        raise SystemExit(f"adb {' '.join(args)} failed\n{text}")
    return r


def main() -> int:
    if not SRC.is_file():
        raise SystemExit(f"missing {SRC}")
    if not IMG.is_file() or IMG.stat().st_size != SRC.stat().st_size:
        shutil.copy2(SRC, IMG)
    print(f"image {IMG} ({IMG.stat().st_size} bytes)")
    s = serial()
    print("serial", s)
    model = subprocess.run(
        [ADB, "-s", s, "shell", "cat /proc/device-tree/model; echo"],
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout
    print("live model", model.strip())

    print("backup live boot ->", BAK)
    adb(s, "pull", "/dev/block/by-name/boot", str(BAK), timeout=180)
    print("push imaging boot")
    adb(s, "push", str(IMG), REMOTE, timeout=180)
    print("dd mmcblk0p4")
    r = adb(
        s,
        "shell",
        f"dd if={REMOTE} of=/dev/mmcblk0p4 bs=1M conv=fsync; sync; echo DD_OK",
        timeout=180,
    )
    print(r.stdout.decode("utf-8", "replace"), end="")
    print("rebooting")
    subprocess.run([ADB, "-s", s, "reboot"], capture_output=True, timeout=20)

    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(3)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        print(f"t={time.time()-t0:.0f}s {listing.strip()}")
        for line in listing.splitlines():
            if "\tdevice" not in line:
                continue
            ns = line.split()[0]
            m = subprocess.run(
                [ADB, "-s", ns, "shell", "cat /proc/device-tree/model; echo"],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout
            if "CameVision Ego" in m:
                gpio = subprocess.run(
                    [ADB, "-s", ns, "shell", "ls /proc/device-tree/i2c-gpio-cam1 >/dev/null && echo I2C_GPIO_OK"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout
                print("up", ns, m.strip(), gpio.strip())
                if "I2C_GPIO_OK" not in gpio:
                    raise SystemExit("booted without i2c-gpio-cam1")
                return 0
    raise SystemExit("board did not return")


if __name__ == "__main__":
    raise SystemExit(main())
