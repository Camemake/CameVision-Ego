#!/usr/bin/env python3
"""Keep the Ego live page up whenever the board is plugged in.

The stereo process starts on the board at boot. USB is ADB, so the PC must
re-create tcp:8081 forwards after every plug, reboot, or adb restart.
This watcher does that by itself: deploy the overlay, start the service if
it is down, set forwards, open the page.

Install once (Windows logon):
    python tools/cv_ego_autostart.py --install
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
LOG = ROOT / "build" / "ego-autostart.log"
PIDF = ROOT / "build" / "ego-autostart.pid"
PAGE = "http://127.0.0.1:8081/"
CAL = "http://127.0.0.1:8081/cal"

SRC = ROOT / "tools" / "ego_stereo.py"
SYNC = ROOT / "tools" / "ego_cam_sync.py"
CAL_HTML = ROOT / "tools" / "ego_calib.html"
IMU = ROOT / "tools" / "ego_imu_hud.py"
LOGO = ROOT / "tools" / "camemake-logo.png"
SO = ROOT / "build" / "libego_stereo.so"
BOOT_SH = ROOT / "tools" / "camevision-stereo.sh"
S99 = ROOT / "tools" / "S99ego-stereo"
IQ_NAME = "sc233hgs_efference-sc233hgs_default.json"
IQ_CANDIDATES = (
    ROOT / "tools" / "iqfiles" / "sc233hgs_efference-sc233hgs_flicker50.json",
    ROOT / "restore" / "release-1-20260824" / "overlay" / "iqfiles" / IQ_NAME,
)


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def adb(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, *args], capture_output=True, text=True, timeout=timeout)


def devices() -> list[str]:
    try:
        r = adb("devices", timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            out.append(line.split()[0])
    return out


def listening(s: str, port: str = "8081") -> bool:
    r = adb(
        "-s",
        s,
        "shell",
        f"netstat -lnt 2>/dev/null | grep {port} || ss -lnt | grep {port}",
        timeout=8,
    )
    return port in (r.stdout or "")


def push(s: str, src: Path, dst: str, timeout: int = 20) -> None:
    if src.is_file():
        adb("-s", s, "push", str(src), dst, timeout=timeout)


def deploy(s: str) -> None:
    log(f"{s} deploy overlay")
    push(s, SRC, "/userdata/ego_stereo.py")
    push(s, SYNC, "/userdata/ego_cam_sync.py")
    push(s, CAL_HTML, "/userdata/ego_calib.html")
    push(s, IMU, "/userdata/ego_imu_hud.py")
    push(s, LOGO, "/userdata/camemake-logo.png")
    if SO.is_file() and SO.stat().st_size > 4000:
        push(s, SO, "/userdata/libego_stereo.so")
    push(s, BOOT_SH, "/userdata/camevision-stereo.sh")
    push(s, S99, "/userdata/S99ego-stereo")
    iq = next((p for p in IQ_CANDIDATES if p.is_file() and p.stat().st_size > 10000), None)
    if iq is not None:
        adb("-s", s, "shell", "mkdir -p /userdata/iqfiles")
        push(s, iq, "/userdata/iqfiles/" + IQ_NAME)
    adb(
        "-s",
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/ego_cam_sync.py "
        "/userdata/ego_calib.html /userdata/ego_imu_hud.py "
        "/userdata/camevision-stereo.sh /userdata/S99ego-stereo; "
        "chmod 755 /userdata/camevision-stereo.sh /userdata/S99ego-stereo; "
        "rm -f /userdata/uvc-webcam.on; "
        "mount -o remount,rw / 2>/dev/null; "
        "cp -f /userdata/S99ego-stereo /etc/init.d/S99ego-stereo; "
        "chmod 755 /etc/init.d/S99ego-stereo; "
        "mount -o remount,ro / 2>/dev/null",
        timeout=20,
    )


def start_service(s: str) -> None:
    log(f"{s} start camevision-stereo.sh")
    adb(
        "-s",
        s,
        "shell",
        "/userdata/camevision-stereo.sh >/userdata/ego-stereo-boot.log 2>&1",
        timeout=50,
    )


def forward(s: str) -> None:
    adb("-s", s, "forward", "tcp:8081", "tcp:8081")
    adb("-s", s, "forward", "tcp:8083", "tcp:8083")


def on_connect(s: str, open_page: bool) -> None:
    try:
        deploy(s)
        if not listening(s):
            start_service(s)
            t0 = time.time()
            while time.time() - t0 < 40 and not listening(s):
                time.sleep(1)
        forward(s)
        if listening(s):
            log(f"{s} page {PAGE}")
            if open_page:
                webbrowser.open(PAGE)
        else:
            log(f"{s} :8081 still down after start")
    except subprocess.TimeoutExpired:
        log(f"{s} adb timeout")
    except Exception as e:
        log(f"{s} {type(e).__name__}: {e}")


def startup_paths() -> tuple[Path, Path]:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs = startup / "CameVision-Ego-autostart.vbs"
    cmd = ROOT / "tools" / "cv_ego_autostart-hidden.cmd"
    return vbs, cmd


def install() -> int:
    py = sys.executable
    script = ROOT / "tools" / "cv_ego_autostart.py"
    vbs, cmd = startup_paths()
    cmd.write_text(
        f'@echo off\nstart "" /min "{py}" "{script}" --daemon\n',
        encoding="ascii",
    )
    vbs.write_text(
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.Run """{py}"" ""{script}"" --daemon", 0, False\r\n',
        encoding="ascii",
    )
    log(f"installed logon helper {vbs}")
    log("USB stays ADB. Plug the board and the page opens by itself.")
    return 0


def already_running() -> bool:
    if not PIDF.is_file():
        return False
    try:
        pid = int(PIDF.read_text(encoding="ascii").strip())
    except ValueError:
        return False
    # Windows: OpenProcess via tasklist
    r = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
    )
    return str(pid) in (r.stdout or "") and "python" in (r.stdout or "").lower()


def daemon() -> int:
    if already_running() and os.getpid() != int(PIDF.read_text(encoding="ascii").strip() or "0"):
        log(f"already running pid={PIDF.read_text(encoding='ascii').strip()}")
        return 0
    PIDF.parent.mkdir(parents=True, exist_ok=True)
    PIDF.write_text(str(os.getpid()), encoding="ascii")
    log("watching for Ego ADB")
    armed: set[str] = set()
    while True:
        now = set(devices())
        for s in now - armed:
            log(f"{s} connected")
            on_connect(s, open_page=True)
            armed.add(s)
        for s in now & armed:
            try:
                forward(s)
                if not listening(s):
                    log(f"{s} :8081 dropped, restarting")
                    start_service(s)
                    forward(s)
            except Exception as e:
                log(f"{s} keep {e}")
        for s in armed - now:
            log(f"{s} disconnected")
        armed &= now
        time.sleep(2)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--install", action="store_true", help="install Windows logon autostart")
    p.add_argument("--daemon", action="store_true", help="run the USB watcher loop")
    p.add_argument("--once", action="store_true", help="deploy/forward once and exit")
    args = p.parse_args()
    if args.install:
        rc = install()
        # start watcher now so this session is covered
        vbs, _ = startup_paths()
        subprocess.Popen(
            ["wscript.exe", str(vbs)],
            cwd=str(ROOT),
            close_fds=True,
        )
        return rc
    if args.once:
        found = devices()
        if not found:
            raise SystemExit("no ADB")
        for s in found:
            on_connect(s, open_page=True)
        return 0
    return daemon()


if __name__ == "__main__":
    raise SystemExit(main())
