#!/usr/bin/env python3
"""Install the working Ego overlay over ADB: stereo page, Wi-Fi STA, pylib.

Does not flash partitions. USB stays ADB. Used after Maskrom and by
tools/cv_ego_flash.py (V0.2).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import time

from cv_ego_paths import adb_exe, boot_img, boot_ok, repo_root  # noqa: E402

ADB = adb_exe()
ROOT = repo_root()
_OV_UP = ROOT / "restore" / "updates" / "current" / "overlay"
_OV02 = ROOT / "restore" / "release-0.2-20260902" / "overlay"
_OV01 = ROOT / "restore" / "release-1-20260824" / "overlay"
OV = next((p for p in (_OV_UP, _OV02, _OV01) if p.is_dir()), _OV02)
IQ_NAME = "sc233hgs_camevision-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def adb(s: str, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    r = subprocess.run([ADB, "-s", s, *args], capture_output=True, timeout=timeout)
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    if r.returncode != 0:
        raise SystemExit(f"adb {args} failed ({r.returncode})")
    return r


def flatten_content_dir(p: Path) -> Path:
    cur = p
    for _ in range(4):
        entries = [e for e in cur.iterdir() if not e.name.startswith(".")]
        files = [e for e in entries if e.is_file()]
        dirs = [e for e in entries if e.is_dir()]
        if files or len(dirs) != 1:
            return cur
        cur = dirs[0]
    return cur


def first_dir(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_dir() and any(p.iterdir()):
            return flatten_content_dir(p)
    return None


def first_file(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def push(s: str, src: Path, dst: str, timeout: int = 30) -> None:
    print(f"push {src} -> {dst}", flush=True)
    adb(s, "push", str(src), dst, timeout=timeout)


def push_dir(s: str, src: Path, dst: str) -> None:
    adb(s, "shell", f"mkdir -p {dst}")
    print(f"push {src}/. -> {dst}", flush=True)
    adb(s, "push", str(src) + "/.", dst, timeout=180)


def _module_names(s: str) -> str:
    r = subprocess.run(
        [
            ADB,
            "-s",
            s,
            "shell",
            "cat '/proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-name'; echo; "
            "cat '/proc/device-tree/i2c-gpio-cam1/sc233hgs@30/rockchip,camera-module-name'; echo",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return r.stdout or ""


def ensure_camevision_dtb(s: str) -> str:
    names = _module_names(s)
    print("camera-module-name", names.replace("\n", " ").strip(), flush=True)
    if names.count("camevision-sc233hgs") >= 2:
        return s
    img = boot_img()
    if img is None or not boot_ok(img.read_bytes()):
        raise SystemExit("DTB is not CameVision and no good boot FIT is in this package")
    print(f"=== DTB not CameVision — rewriting boot from {img} ===", flush=True)
    adb(s, "push", str(img), "/userdata/camevision_boot_ego.img", timeout=180)
    adb(
        s,
        "shell",
        "dd if=/userdata/camevision_boot_ego.img of=/dev/mmcblk0p4 bs=1M conv=fsync; sync; echo DD_OK",
        timeout=180,
    )
    subprocess.run([ADB, "-s", s, "reboot"], capture_output=True, timeout=20)
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(3)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        if s not in listing or "device" not in listing:
            continue
        model = subprocess.run(
            [ADB, "-s", s, "shell", "cat /proc/device-tree/model; echo"],
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout
        if "CameVision Ego" in (model or ""):
            break
    else:
        raise SystemExit("board did not return after boot rewrite")
    names = _module_names(s)
    print("camera-module-name after rewrite", names.replace("\n", " ").strip(), flush=True)
    if names.count("camevision-sc233hgs") < 2:
        raise SystemExit("boot rewrite did not switch camera-module-name to CameVision")
    return s


def deploy(s: str, pylib: bool = True) -> None:
    s = ensure_camevision_dtb(s)
    files = [
        (ROOT / "tools" / "ego_stereo.py", "/userdata/ego_stereo.py"),
        (ROOT / "tools" / "ego_cam_sync.py", "/userdata/ego_cam_sync.py"),
        (ROOT / "tools" / "ego_calib.html", "/userdata/ego_calib.html"),
        (ROOT / "tools" / "ego_imu_hud.py", "/userdata/ego_imu_hud.py"),
        (ROOT / "tools" / "camemake-logo.png", "/userdata/camemake-logo.png"),
        (ROOT / "tools" / "camevision-stereo.sh", "/userdata/camevision-stereo.sh"),
        (ROOT / "tools" / "camevision-aiq.sh", "/userdata/camevision-aiq.sh"),
        (ROOT / "tools" / "camevision-wifi.sh", "/userdata/camevision-wifi.sh"),
        (ROOT / "tools" / "wpa_camevision.conf", "/userdata/wpa_camevision.conf"),
        (ROOT / "tools" / "S99ego-stereo", "/userdata/S99ego-stereo"),
        (ROOT / "tools" / "S11hwclock", "/userdata/S11hwclock"),
        (ROOT / "tools" / "ego_record.py", "/userdata/ego_record.py"),
        (ROOT / "tools" / "ego_mtf.py", "/userdata/ego_mtf.py"),
        (ROOT / "tools" / "iso12233.png", "/userdata/iso12233.png"),
    ]
    for src, dst in files:
        if src.is_file():
            push(s, src, dst)
    so = first_file(ROOT / "build" / "libego_stereo.so", OV / "libego_stereo.so")
    if so is not None and so.stat().st_size > 4000:
        push(s, so, "/userdata/libego_stereo.so")
    kmpp = first_file(
        OV / "kmpp-rt52.ko",
        ROOT / "restore" / "release-0.2-20260902" / "overlay" / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay" / "kmpp-rt52.ko",
        ROOT / "restore" / "lock-20260821-rt52-adb-hwrtsp" / "overlay" / "kmpp-rt52.ko",
    )
    if kmpp is not None:
        push(s, kmpp, "/userdata/kmpp-rt52.ko", timeout=60)
    iq = first_file(
        ROOT / "tools" / "iqfiles" / IQ_NAME,
        ROOT / "tools" / "iqfiles" / "sc233hgs_camevision-sc233hgs_flicker50.json",
        OV / "iqfiles" / IQ_NAME,
        ROOT / "restore" / "recovery-5-20260823-imaging-adb" / "overlay" / "iqfiles" / IQ_NAME,
    )
    if iq is None:
        raise SystemExit("missing SC233HGS IQ")
    adb(s, "shell", "mkdir -p /userdata/iqfiles")
    push(s, iq, "/userdata/iqfiles/" + IQ_NAME)

    kos = first_dir(
        OV / "swt6621-rt52",
        ROOT / "build" / "live" / "swt6621-rt52",
    )
    fw = first_dir(
        OV / "swt6621_fw",
        ROOT / "build" / "live" / "swt6621_fw",
    )
    if kos is not None:
        push_dir(s, kos, "/userdata/swt6621-rt52")
    else:
        print("WARN Wi-Fi modules not in this package — imaging still installs", flush=True)
    if fw is not None:
        push_dir(s, fw, "/userdata/swt6621_fw")

    adb(
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/ego_cam_sync.py "
        "/userdata/ego_calib.html /userdata/ego_imu_hud.py "
        "/userdata/camevision-stereo.sh /userdata/camevision-aiq.sh "
        "/userdata/camevision-wifi.sh "
        "/userdata/wpa_camevision.conf /userdata/S99ego-stereo /userdata/S11hwclock "
        "/userdata/ego_record.py /userdata/ego_mtf.py; "
        "chmod 755 /userdata/camevision-stereo.sh /userdata/camevision-aiq.sh "
        "/userdata/camevision-wifi.sh "
        "/userdata/S99ego-stereo /userdata/S11hwclock; "
        "rm -f /userdata/uvc-webcam.on; "
        "mount -o remount,rw / 2>/dev/null; "
        "cp -f /userdata/S99ego-stereo /etc/init.d/S99ego-stereo; "
        "cp -f /userdata/S11hwclock /etc/init.d/S11hwclock; "
        "chmod 755 /etc/init.d/S99ego-stereo /etc/init.d/S11hwclock; "
        "mount -o remount,ro / 2>/dev/null; "
        "if [ -f /userdata/iqfiles/" + IQ_NAME + " ]; then "
        "mount -o remount,rw /oem 2>/dev/null; "
        "for d in /oem/usr/share/iqfiles /userdata/iqfiles /userdata/iqfiles-all; do "
        "[ -d \"$d\" ] || continue; "
        "find \"$d\" -maxdepth 1 -type f -name 'sc233hgs_*_default.json' "
        "! -name '" + IQ_NAME + "' -exec rm -f {} +; done; "
        "cp -f /userdata/iqfiles/" + IQ_NAME + " "
        "/oem/usr/share/iqfiles/" + IQ_NAME + "; "
        "ln -sfn " + IQ_NAME + " "
        "/oem/usr/share/iqfiles/sc233hgs_default_default.json; fi",
        timeout=30,
    )

    print("=== start IQ / 3A ===", flush=True)
    adb(s, "shell", "sh /userdata/camevision-aiq.sh", timeout=90)

    if pylib:
        wheels = first_dir(
            ROOT / "build" / "wheels",
            ROOT / "restore" / "release-0.2-20260902" / "wheels",
        )
        extract = first_file(
            ROOT / "tools" / "cv_ego_extract_pylib.py",
            OV / "cv_ego_extract_pylib.py",
        )
        if wheels is None or extract is None:
            raise SystemExit("no numpy/opencv wheels — depth will be broken")
        adb(s, "shell", "mkdir -p /userdata/wheels /userdata/pylib")
        for w in sorted(wheels.glob("*.whl")):
            name = w.name.lower()
            if w.stat().st_size < 8_000_000:
                continue
            if name.startswith("numpy-") or name.startswith("opencv_python_headless-4."):
                push(s, w, "/userdata/wheels/" + w.name, timeout=180)
        push(s, extract, "/userdata/cv_ego_extract_pylib.py")
        adb(
            s,
            "shell",
            "sed -i 's/\\r$//' /userdata/cv_ego_extract_pylib.py; "
            "python3 /userdata/cv_ego_extract_pylib.py",
            timeout=300,
        )
        adb(
            s,
            "shell",
            "PYTHONPATH=/userdata/pylib python3 -c 'import numpy,cv2'",
            timeout=30,
        )

    print("=== start live page ===", flush=True)
    adb(
        s,
        "shell",
        "kill $(ps | awk '/ego_stereo.py/ && !/awk/ {print $1}') 2>/dev/null; "
        "killall v4l2-ctl 2>/dev/null; sleep 1; sh /userdata/camevision-stereo.sh",
        timeout=90,
    )
    check = subprocess.run(
        [
            ADB,
            "-s",
            s,
            "shell",
            "n=0; while [ $n -lt 25 ]; do "
            "grep -q 'AWBGAIN    ON' /proc/rkisp-vir0 2>/dev/null && "
            "grep -q 'AWBGAIN    ON' /proc/rkisp-vir2 2>/dev/null && exit 0; "
            "n=$((n+1)); sleep 1; done; exit 1",
        ],
        capture_output=True,
        timeout=40,
    )
    if check.returncode != 0:
        raise SystemExit("ISP did not start after overlay — 3A did not attach")
    print("ISP on", flush=True)
    depth = subprocess.run(
        [
            ADB,
            "-s",
            s,
            "shell",
            "n=0; while [ $n -lt 45 ]; do "
            "st=$(wget -q -O - http://127.0.0.1:8081/stat 2>/dev/null || true); "
            "echo \"$st\"; "
            "if echo \"$st\" | grep -q ModuleNotFoundError; then n=$((n+1)); sleep 1; continue; fi; "
            "if ! echo \"$st\" | grep -Eq '\"kind\":\"(sgbm|bm)\"'; then n=$((n+1)); sleep 1; continue; fi; "
            "if echo \"$st\" | grep -Eq '\"hit\":[1-9]'; then echo DEPTH_OK; exit 0; fi; "
            "n=$((n+1)); sleep 1; done; exit 1",
        ],
        capture_output=True,
        timeout=60,
    )
    text = ((depth.stdout or b"") + (depth.stderr or b"")).decode("utf-8", "replace")
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    if depth.returncode != 0 or "DEPTH_OK" not in text:
        raise SystemExit("depth matcher did not start after overlay")
    print("DEPTH on", flush=True)
    print("OVERLAY_OK", flush=True)


def main() -> int:
    s = sys.argv[1] if len(sys.argv) > 1 else serial()
    print("serial", s, flush=True)
    deploy(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
