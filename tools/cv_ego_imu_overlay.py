#!/usr/bin/env python3
"""Sync board time, start high-rate IMU HUD, serve overlay page.

Does not restart 3A or the MJPEG cameras. USB stays ADB.
"""
from __future__ import annotations

import os

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import datetime
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
HUD = ROOT / "tools" / "ego_imu_hud.py"
HTML_PATH = ROOT / "tools" / "ego_preview.html"
HTML_PORT = 8766


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def adb(s: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, "-s", s, *args], capture_output=True, text=True, timeout=timeout)


def sync_time(s: str) -> None:
    now = datetime.datetime.now().astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    # POSIX TZ sign is inverted: UTC-2 means local = UTC+2.
    off = now.utcoffset() or datetime.timedelta(0)
    hours = int(off.total_seconds() // 3600)
    tz = f"UTC-{hours}" if hours >= 0 else f"UTC+{abs(hours)}"
    print(f"sync time {stamp} TZ={tz}", flush=True)
    r = adb(
        s,
        "shell",
        f"export TZ={tz}; "
        f"date -s '{stamp}' >/dev/null; "
        "hwclock -w 2>/dev/null || true; "
        "date; date +%s",
        timeout=15,
    )
    print((r.stdout or "") + (r.stderr or ""), end="")


def start_hud(s: str) -> None:
    adb(s, "push", str(HUD), "/userdata/ego_imu_hud.py", timeout=20)
    r = adb(
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_imu_hud.py; "
        "kill $(cat /tmp/ego-imu.pid 2>/dev/null) 2>/dev/null; "
        "killall -q ego_imu_hud.py 2>/dev/null; "
        "export TZ=UTC-2; "
        "start-stop-daemon -S -b -m -p /tmp/ego-imu.pid -x /usr/bin/python3 -- "
        "/userdata/ego_imu_hud.py; "
        "sleep 1; echo pid=$(cat /tmp/ego-imu.pid 2>/dev/null); "
        "ps | grep ego_imu_hud | grep -v grep",
        timeout=20,
    )
    print((r.stdout or "") + (r.stderr or ""), end="")


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    sync_time(s)
    start_hud(s)
    adb(s, "forward", "tcp:8083", "tcp:8083")
    adb(s, "forward", "tcp:8081", "tcp:8081")
    adb(s, "forward", "tcp:8082", "tcp:8082")
    print("forward 8081/8082/8083", flush=True)

    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            html = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

    httpd = ThreadingHTTPServer(("127.0.0.1", HTML_PORT), H)
    print(f"page http://127.0.0.1:{HTML_PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
