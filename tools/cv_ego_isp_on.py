#!/usr/bin/env python3
"""Push IQ, start RKAIQ 3A, prove ISP NV12 on Ego. No rockit. USB stays ADB."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
AIQ = ROOT / r"restore\recovery-3-20260822-uvc-wifi-rkaiq\overlay\camevision-aiq.sh"
IQ = ROOT / r"restore\recovery-3-20260822-uvc-wifi-rkaiq\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True, check=False)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 40) -> str:
    r = subprocess.run(
        [ADB, "-s", s, "shell", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (r.stdout or "") + (r.stderr or "")
    print(out, end="" if out.endswith("\n") else "\n")
    return out


def push(s: str, src: Path, dst: str) -> None:
    print("push", src.name, "->", dst, flush=True)
    r = subprocess.run([ADB, "-s", s, "push", str(src), dst], capture_output=True, text=True)
    print((r.stdout or "") + (r.stderr or ""), end="")
    if r.returncode:
        raise SystemExit(f"push failed {src} -> {dst}")


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    if not AIQ.is_file() or not IQ.is_file():
        raise SystemExit(f"missing {AIQ} or {IQ}")

    sh(
        s,
        "echo === dt modules ===; "
        "for f in "
        "/proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-name "
        "/proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-lens-name "
        "/proc/device-tree/i2c-gpio-cam1/sc233hgs@30/rockchip,camera-module-name "
        "/proc/device-tree/i2c-gpio-cam1/sc233hgs@30/rockchip,camera-module-lens-name; "
        "do echo $f; cat $f 2>/dev/null; echo; done",
    )

    sh(
        s,
        "kill $(cat /tmp/ego-cam0.pid /tmp/ego-cam1.pid 2>/dev/null) 2>/dev/null; "
        "killall ffmpeg 2>/dev/null; "
        "for p in /proc/[0-9]*; do "
        "  cmd=$(tr '\\0' ' ' < $p/cmdline 2>/dev/null); "
        "  case $cmd in *v4l2-ctl*|*ego_mjpeg*) kill -9 ${p#/proc/} ;; esac; "
        "done; "
        "echo killed-cif; "
        "ps | grep -v grep | grep -E 'v4l2|ffmpeg|ego_mjpeg' || true",
    )

    push(s, AIQ, "/userdata/camevision-aiq.sh")
    sh(s, "mkdir -p /userdata/iqfiles; sed -i 's/\\r$//' /userdata/camevision-aiq.sh")
    push(s, IQ, "/userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json")

    print("start 3A", flush=True)
    sh(s, "sh /userdata/camevision-aiq.sh", timeout=30)
    time.sleep(2)
    sh(
        s,
        "echo === sysctl ===; "
        "grep -E 'sysctl|cid|iqfiles|ERR|error|success' /userdata/rkaiq.log | tail -40",
    )

    print("isp stills", flush=True)
    sh(
        s,
        "v4l2-ctl -d /dev/video24 --set-fmt-video=width=1920,height=1200,pixelformat=NV12 --get-fmt-video; "
        "timeout -k 2 10 v4l2-ctl -d /dev/video24 --stream-mmap=4 --stream-count=4 "
        "--stream-to=/userdata/cam0_isp.nv12 --stream-poll; "
        "echo cam0_bytes $(wc -c < /userdata/cam0_isp.nv12); "
        "v4l2-ctl -d /dev/video32 --set-fmt-video=width=1920,height=1200,pixelformat=NV12 --get-fmt-video; "
        "timeout -k 2 10 v4l2-ctl -d /dev/video32 --stream-mmap=4 --stream-count=4 "
        "--stream-to=/userdata/cam1_isp.nv12 --stream-poll; "
        "echo cam1_bytes $(wc -c < /userdata/cam1_isp.nv12); "
        "echo === rkisp after ===; "
        "sed -n '1,20p' /proc/rkisp-vir0; echo ----; sed -n '1,20p' /proc/rkisp-vir2",
        timeout=40,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
