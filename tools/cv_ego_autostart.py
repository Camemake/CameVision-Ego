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
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import adb_exe, repo_root  # noqa: E402

ADB = adb_exe()
ROOT = repo_root()
LOG = ROOT / "build" / "ego-autostart.log"
PIDF = ROOT / "build" / "ego-autostart.pid"
PAGE = "http://127.0.0.1:8081/"
CAL = "http://127.0.0.1:8081/cal"

SRC = ROOT / "tools" / "ego_stereo.py"
SYNC = ROOT / "tools" / "ego_cam_sync.py"
CAL_HTML = ROOT / "tools" / "ego_calib.html"
IMU = ROOT / "tools" / "ego_imu_hud.py"
REC = ROOT / "tools" / "ego_record.py"
MTF = ROOT / "tools" / "ego_mtf.py"
KMPP_CANDIDATES = (
    ROOT / "restore" / "release-0.2-20260902" / "overlay" / "kmpp-rt52.ko",
    ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "kmpp-rt52.ko",
    ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay" / "kmpp-rt52.ko",
    ROOT / "restore" / "lock-20260821-rt52-adb-hwrtsp" / "overlay" / "kmpp-rt52.ko",
)
KMPP = next((p for p in KMPP_CANDIDATES if p.is_file()), KMPP_CANDIDATES[0])
HOST_REC = ROOT / "tools" / "cv_ego_record_host.py"
LOGO = ROOT / "tools" / "camemake-logo.png"
SO = ROOT / "build" / "libego_stereo.so"
BOOT_SH = ROOT / "tools" / "camevision-stereo.sh"
AIQ_SH = ROOT / "tools" / "camevision-aiq.sh"
WIFI_SH = ROOT / "tools" / "camevision-wifi.sh"
WPA_CONF = ROOT / "tools" / "wpa_camevision.conf"
S99 = ROOT / "tools" / "S99ego-stereo"
IQ_NAME = "sc233hgs_camevision-sc233hgs_default.json"
IQ_CANDIDATES = (
    ROOT / "tools" / "iqfiles" / "sc233hgs_camevision-sc233hgs_flicker50.json",
    ROOT / "restore" / "release-0.2-20260902" / "overlay" / "iqfiles" / IQ_NAME,
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
    push(s, REC, "/userdata/ego_record.py")
    push(s, MTF, "/userdata/ego_mtf.py")
    push(s, ROOT / "tools" / "iso12233.png", "/userdata/iso12233.png")
    if KMPP.is_file():
        push(s, KMPP, "/userdata/kmpp-rt52.ko", timeout=60)
    push(s, LOGO, "/userdata/camemake-logo.png")
    if SO.is_file() and SO.stat().st_size > 4000:
        push(s, SO, "/userdata/libego_stereo.so")
    push(s, BOOT_SH, "/userdata/camevision-stereo.sh")
    push(s, AIQ_SH, "/userdata/camevision-aiq.sh")
    push(s, WIFI_SH, "/userdata/camevision-wifi.sh")
    push(s, WPA_CONF, "/userdata/wpa_camevision.conf")
    push(s, S99, "/userdata/S99ego-stereo")
    push(s, ROOT / "tools" / "S11hwclock", "/userdata/S11hwclock")
    iq = next((p for p in IQ_CANDIDATES if p.is_file() and p.stat().st_size > 10000), None)
    if iq is not None:
        adb("-s", s, "shell", "mkdir -p /userdata/iqfiles")
        push(s, iq, "/userdata/iqfiles/" + IQ_NAME)
        adb(
            "-s",
            s,
            "shell",
            "mount -o remount,rw /oem 2>/dev/null; "
            "cp -f /userdata/iqfiles/" + IQ_NAME + " /oem/usr/share/iqfiles/" + IQ_NAME + "; "
            "ln -sfn " + IQ_NAME + " /oem/usr/share/iqfiles/sc233hgs_default_default.json",
        )
    adb(
        "-s",
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/ego_cam_sync.py "
        "/userdata/ego_calib.html /userdata/ego_imu_hud.py /userdata/ego_record.py "
        "/userdata/ego_mtf.py "
        "/userdata/camevision-stereo.sh /userdata/camevision-aiq.sh "
        "/userdata/camevision-wifi.sh "
        "/userdata/wpa_camevision.conf /userdata/S99ego-stereo /userdata/S11hwclock; "
        "chmod 755 /userdata/camevision-stereo.sh /userdata/camevision-aiq.sh "
        "/userdata/camevision-wifi.sh "
        "/userdata/S99ego-stereo /userdata/S11hwclock; "
        "rm -f /userdata/uvc-webcam.on; "
        "mount -o remount,rw / 2>/dev/null; "
        "cp -f /userdata/S99ego-stereo /etc/init.d/S99ego-stereo; "
        "cp -f /userdata/S11hwclock /etc/init.d/S11hwclock; "
        "chmod 755 /etc/init.d/S99ego-stereo /etc/init.d/S11hwclock; "
        "mount -o remount,ro / 2>/dev/null",
        timeout=20,
    )


def start_service(s: str) -> None:
    log(f"{s} start 3A + camevision-stereo.sh")
    adb(
        "-s",
        s,
        "shell",
        "sh /userdata/camevision-aiq.sh >/userdata/aiq-boot.log 2>&1; "
        "/userdata/camevision-stereo.sh >/userdata/ego-stereo-boot.log 2>&1",
        timeout=90,
    )


def forward(s: str) -> None:
    adb("-s", s, "forward", "tcp:8081", "tcp:8081")
    adb("-s", s, "forward", "tcp:8083", "tcp:8083")
    adb("-s", s, "forward", "tcp:8092", "tcp:8091")
    try:
        adb("-s", s, "reverse", "tcp:8091", "tcp:8091")
    except Exception:
        pass


def record_host_up() -> bool:
    sock = socket.socket()
    try:
        sock.settimeout(0.4)
        sock.connect(("127.0.0.1", 8093))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def ensure_record_host() -> None:
    if record_host_up():
        return
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(
        [sys.executable, str(HOST_REC)],
        cwd=str(ROOT),
        creationflags=flags,
    )
    t0 = time.time()
    while time.time() - t0 < 5 and not record_host_up():
        time.sleep(0.2)


def on_connect(s: str, open_page: bool) -> None:
    try:
        deploy(s)
        ensure_record_host()
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


def install_windows() -> int:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    vbs = startup / "CameVision-Ego-autostart.vbs"
    cmd = ROOT / "tools" / "cv_ego_autostart-hidden.cmd"
    py = sys.executable
    script = ROOT / "tools" / "cv_ego_autostart.py"
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
    subprocess.Popen(["wscript.exe", str(vbs)], cwd=str(ROOT), close_fds=True)
    return 0


def install_linux() -> int:
    desktop_dir = Path.home() / ".config" / "autostart"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop = desktop_dir / "camevision-ego.desktop"
    py = sys.executable
    script = ROOT / "tools" / "cv_ego_autostart.py"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=CameVision Ego\n"
        f'Exec="{py}" "{script}" --daemon\n'
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    os.chmod(desktop, 0o644)
    log(f"installed desktop autostart {desktop}")
    subprocess.Popen(
        [py, str(script), "--daemon"],
        cwd=str(ROOT),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return 0


def install() -> int:
    if sys.platform == "win32":
        rc = install_windows()
    else:
        rc = install_linux()
    log("USB stays ADB. Plug the board and the page opens by itself.")
    return rc


def already_running() -> bool:
    if not PIDF.is_file():
        return False
    try:
        pid = int(PIDF.read_text(encoding="ascii").strip())
    except ValueError:
        return False
    if pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


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
    p.add_argument("--install", action="store_true", help="install logon / desktop autostart")
    p.add_argument("--daemon", action="store_true", help="run the USB watcher loop")
    p.add_argument("--once", action="store_true", help="deploy/forward once and exit")
    args = p.parse_args()
    if args.install:
        return install()
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
