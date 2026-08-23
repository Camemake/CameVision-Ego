#!/usr/bin/env python3
"""Push UVC files over ADB, then switch USB to CameVision Single (Wi-Fi stays)."""
import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Single")
OV = ROOT / r"restore\recovery-2-20260821-adb-stream\overlay"
LIVE = ROOT / r"build\live"


def adb(*args, check=True):
    r = subprocess.run([ADB, "-s", S, *args], capture_output=True)
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    if out:
        print(out, end="" if out.endswith("\n") else out + "\n")
    if err:
        print(err, end="" if err.endswith("\n") else err + "\n")
    if check and r.returncode != 0:
        raise SystemExit(r.returncode)
    return r


def push(src: Path, dst: str):
    tmp = Path(r"C:\Users\stefa\AppData\Local\Temp") / (src.name + ".unix")
    text = src.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    tmp.write_bytes(text.encode("utf-8"))
    adb("push", str(tmp), dst)


def main():
    adb("wait-for-device")
    adb("shell", "mount -o remount,rw /; mount -o remount,rw /userdata")
    push(LIVE / "S50usbdevice.uvc-rk", "/etc/init.d/S50usbdevice")
    push(OV / "S99camevision", "/etc/init.d/S99camevision")
    push(OV / "camevision-uvc-mjpg.py", "/userdata/camevision-uvc-mjpg.py")
    push(OV / "camevision-uvc-cam.sh", "/userdata/camevision-uvc-cam.sh")
    push(OV / "camevision-uvc-live.sh", "/userdata/camevision-uvc-live.sh")
    push(OV / "camevision-aiq.sh", "/userdata/camevision-aiq.sh")
    adb(
        "shell",
        "chmod 755 /etc/init.d/S50usbdevice /etc/init.d/S99camevision "
        "/userdata/camevision-uvc-mjpg.py /userdata/camevision-uvc-cam.sh "
        "/userdata/camevision-uvc-live.sh /userdata/camevision-aiq.sh; "
        "busybox telnetd -l /bin/sh -p 2323; sync",
    )
    print("=== SWITCH USB TO UVC ===")
    subprocess.Popen(
        [
            ADB,
            "-s",
            S,
            "shell",
            "setsid /userdata/camevision-uvc-live.sh </dev/null >/userdata/cv-uvc-live.log 2>&1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(10)
    print("pushed and switch issued")


if __name__ == "__main__":
    main()
