#!/usr/bin/env python3
"""Install the CameVision Ego AM / MIRA220 overlay over ADB.

Does not flash partitions. Does not touch the SC233HGS kit. USB stays ADB.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import adb_exe, repo_root  # noqa: E402
from cv_ego_paths_am import MODULE, boot_img_am, boot_ok_am, release_am  # noqa: E402

ADB = adb_exe()
ROOT = repo_root()
REL = release_am()
OV = REL / "overlay"
IQ_NAME = "mira220_camevision-mira220_default.json"


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


def first_file(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def first_dir(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_dir() and any(p.iterdir()):
            return p
    return None


def push(s: str, src: Path, dst: str, timeout: int = 60) -> None:
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
            "tr -d '\\000' </proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-name; echo; "
            "tr -d '\\000' </proc/device-tree/i2c-gpio-cam1/sc233hgs@30/rockchip,camera-module-name; echo",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return r.stdout or ""


def ensure_am_dtb(s: str) -> str:
    names = _module_names(s)
    print("camera-module-name", names.replace("\n", " ").strip(), flush=True)
    if names.count(MODULE) >= 2:
        return s
    img = boot_img_am()
    if img is None or not boot_ok_am(img.read_bytes()):
        raise SystemExit("DTB is not MIRA220 AM and no AM boot FIT is in this package")
    print(f"=== DTB not AM — rewriting boot from {img} ===", flush=True)
    adb(s, "push", str(img), "/userdata/camevision_boot_ego_am.img", timeout=180)
    adb(
        s,
        "shell",
        "dd if=/userdata/camevision_boot_ego_am.img of=/dev/mmcblk0p4 bs=1M conv=fsync; sync; echo DD_OK",
        timeout=180,
    )
    subprocess.run([ADB, "-s", s, "reboot"], capture_output=True, timeout=20)
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(3)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        if s in listing and "device" in listing:
            names = _module_names(s)
            if names.count(MODULE) >= 2:
                print("camera-module-name after rewrite", names.replace("\n", " ").strip(), flush=True)
                return s
    raise SystemExit("board did not return with camevision-mira220")


def deploy(s: str, pylib: bool = True) -> None:
    s = ensure_am_dtb(s)
    files = [
        (OV / "ego_stereo.py", "/userdata/ego_stereo.py"),
        (OV / "ego_cam_sync.py", "/userdata/ego_cam_sync.py"),
        (OV / "ego_calib.html", "/userdata/ego_calib.html"),
        (OV / "ego_imu_hud.py", "/userdata/ego_imu_hud.py"),
        (OV / "camemake-logo.png", "/userdata/camemake-logo.png"),
        (OV / "camevision-stereo.sh", "/userdata/camevision-stereo.sh"),
        (OV / "camevision-wifi.sh", "/userdata/camevision-wifi.sh"),
        (OV / "wpa_camevision.conf", "/userdata/wpa_camevision.conf"),
        (OV / "S99ego-stereo", "/userdata/S99ego-stereo"),
        (OV / "S11hwclock", "/userdata/S11hwclock"),
        (OV / "S10mira220", "/userdata/S10mira220"),
        (OV / "ego_record.py", "/userdata/ego_record.py"),
        (OV / "ego_mtf.py", "/userdata/ego_mtf.py"),
        (OV / "iso12233.png", "/userdata/iso12233.png"),
        (OV / "libego_stereo.so", "/userdata/libego_stereo.so"),
        (OV / "cv_ego_extract_pylib.py", "/userdata/cv_ego_extract_pylib.py"),
    ]
    for src, dst in files:
        if src.is_file():
            push(s, src, dst)
    for ko in ("mira220.ko", "miralink.ko", "ciflate.ko", "clkgo.ko", "mfix4.ko", "mstart.ko"):
        src = first_file(OV / "modules" / ko, REL / "driver" / ko)
        if src is None:
            raise SystemExit(f"missing AM module {ko}")
        push(s, src, f"/userdata/{ko}")
    kmpp = first_file(OV / "kmpp-rt52.ko")
    if kmpp is not None:
        push(s, kmpp, "/userdata/kmpp-rt52.ko", timeout=60)
    iq = first_file(OV / "iqfiles" / IQ_NAME, ROOT / "tools" / "iqfiles" / IQ_NAME)
    if iq is None:
        raise SystemExit("missing MIRA220 IQ")
    adb(s, "shell", "mkdir -p /userdata/iqfiles")
    push(s, iq, "/userdata/iqfiles/" + IQ_NAME)
    kos = first_dir(OV / "swt6621-rt52")
    fw = first_dir(OV / "swt6621_fw")
    if kos is not None:
        push_dir(s, kos, "/userdata/swt6621-rt52")
    if fw is not None:
        push_dir(s, fw, "/userdata/swt6621_fw")

    adb(
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/camevision-stereo.sh "
        "/userdata/S10mira220 /userdata/S99ego-stereo /userdata/S11hwclock "
        "/userdata/camevision-wifi.sh /userdata/cv_ego_extract_pylib.py; "
        "chmod 755 /userdata/camevision-stereo.sh /userdata/S10mira220 "
        "/userdata/S99ego-stereo /userdata/S11hwclock /userdata/camevision-wifi.sh; "
        "rm -f /userdata/uvc-webcam.on; "
        "mount -o remount,rw /; "
        "cp -f /userdata/S10mira220 /etc/init.d/S10mira220; "
        "cp -f /userdata/S99ego-stereo /etc/init.d/S99ego-stereo; "
        "cp -f /userdata/S11hwclock /etc/init.d/S11hwclock; "
        "cp -f /userdata/mira220.ko /userdata/miralink.ko /userdata/ciflate.ko "
        "/userdata/clkgo.ko /userdata/mfix4.ko /userdata/mstart.ko /lib/; "
        "chmod 644 /lib/mira220.ko /lib/miralink.ko /lib/ciflate.ko "
        "/lib/clkgo.ko /lib/mfix4.ko /lib/mstart.ko; "
        "chmod 755 /etc/init.d/S10mira220 /etc/init.d/S99ego-stereo /etc/init.d/S11hwclock; "
        "sync",
        timeout=40,
    )

    if pylib:
        wheels = first_dir(OV / "wheels", ROOT / "build" / "wheels")
        extract = first_file(OV / "cv_ego_extract_pylib.py", ROOT / "tools" / "cv_ego_extract_pylib.py")
        if wheels is not None and extract is not None:
            adb(s, "shell", "mkdir -p /userdata/wheels /userdata/pylib")
            for w in sorted(wheels.glob("*.whl")):
                name = w.name.lower()
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

    print("=== start AM CSI + live page ===", flush=True)
    adb(
        s,
        "shell",
        "killall python3 v4l2-ctl 2>/dev/null; sleep 1; "
        "sh /userdata/S10mira220; "
        "export PYTHONPATH=/userdata/pylib; "
        "sh /userdata/camevision-stereo.sh",
        timeout=90,
    )
    time.sleep(4)
    check = subprocess.run(
        [
            ADB,
            "-s",
            s,
            "shell",
            "n=0; while [ $n -lt 20 ]; do "
            "c0=$(wget -q -O - http://127.0.0.1:8081/snap0 2>/dev/null | wc -c); "
            "c1=$(wget -q -O - http://127.0.0.1:8081/snap1 2>/dev/null | wc -c); "
            "echo snap $c0 $c1; "
            "if [ \"$c0\" -gt 4000 ] && [ \"$c1\" -gt 4000 ]; then echo EYES_OK; exit 0; fi; "
            "n=$((n+1)); sleep 1; done; exit 1",
        ],
        capture_output=True,
        timeout=50,
    )
    text = ((check.stdout or b"") + (check.stderr or b"")).decode("utf-8", "replace")
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    if check.returncode != 0 or "EYES_OK" not in text:
        raise SystemExit("AM eyes did not start after overlay")
    print("EYES on", flush=True)
    print("OVERLAY_AM_OK", flush=True)


def main() -> int:
    s = sys.argv[1] if len(sys.argv) > 1 else serial()
    print("serial", s, flush=True)
    deploy(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
