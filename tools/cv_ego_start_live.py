#!/usr/bin/env python3
"""Start on-device MJPEG, forward ports, serve the HTML page."""
from __future__ import annotations

import os

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
PY = ROOT / "tools" / "ego_mjpeg.py"
AIQ = ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "camevision-aiq.sh"
IQ = ROOT / "build" / "live" / "sc233hgs_efference-sc233hgs_backlight.json"
HTML_PORT = 8765
CAM0, CAM1 = "/dev/video24", "/dev/video32"
PAGE = (ROOT / "tools" / "ego_preview.html").read_bytes()


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def adb(s: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, "-s", s, *args], capture_output=True, text=True, timeout=timeout)


def wait_up(want: str | None = None) -> str:
    t0 = time.time()
    while time.time() - t0 < 90:
        time.sleep(2)
        r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
        for line in (r.stdout or "").splitlines():
            if "\tdevice" in line:
                s = line.split()[0]
                if want and s != want:
                    continue
                model = adb(s, "shell", "cat /proc/device-tree/model; echo").stdout
                if "CameVision Ego" in model:
                    print(f"up {s}")
                    return s
        print(f"  wait {time.time()-t0:.0f}s")
    raise SystemExit("board did not return")


def isp_ok(s: str) -> bool:
    r = adb(s, "shell", "timeout 3 v4l2-ctl -d /dev/video24 --info >/dev/null; echo $?", timeout=8)
    return (r.stdout or "").strip().endswith("0")


def start_aiq(s: str) -> None:
    adb(s, "push", str(AIQ), "/userdata/camevision-aiq.sh", timeout=20)
    adb(s, "shell", "mkdir -p /userdata/iqfiles")
    adb(s, "push", str(IQ), "/userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json", timeout=20)
    print("start RKAIQ 3A", flush=True)
    r = adb(
        s,
        "shell",
        "mkdir -p /userdata/iqfiles; "
        "cp -f /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json "
        "/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json || "
        "(mount -o remount,rw /oem && cp -f /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json "
        "/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json); "
        "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; "
        "export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH; "
        "start-stop-daemon -S -b -m -p /userdata/rkaiq.pid -x /oem/usr/bin/rkaiq_3A_server -- --silent; "
        "sleep 2; ps | grep rkaiq_3A | grep -v grep",
        timeout=30,
    )
    print((r.stdout or "") + (r.stderr or ""), end="")


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    if not isp_ok(s):
        print("ISP stuck, rebooting", flush=True)
        subprocess.run([ADB, "-s", s, "reboot"], capture_output=True, timeout=20)
        s = wait_up(s)

    start_aiq(s)
    print("push ego_mjpeg.py")
    adb(s, "push", str(PY), "/userdata/ego_mjpeg.py", timeout=20)
    adb(
        s,
        "shell",
        "kill $(cat /tmp/ego-cam0.pid /tmp/ego-cam1.pid 2>/dev/null) 2>/dev/null; "
        "killall ffmpeg v4l2-ctl 2>/dev/null; "
        "sed -i 's/\\r$//' /userdata/ego_mjpeg.py; "
        "start-stop-daemon -S -b -m -p /tmp/ego-cam0.pid -x /usr/bin/python3 -- "
        f"/userdata/ego_mjpeg.py {CAM0} 8081; "
        "start-stop-daemon -S -b -m -p /tmp/ego-cam1.pid -x /usr/bin/python3 -- "
        f"/userdata/ego_mjpeg.py {CAM1} 8082; "
        "sleep 1; echo pids; cat /tmp/ego-cam0.pid /tmp/ego-cam1.pid; "
        "netstat -lnt 2>/dev/null | grep -E '8081|8082' || ss -lnt | grep -E '8081|8082' || true",
        timeout=20,
    )
    print("forward 8081/8082")
    adb(s, "forward", "--remove-all")
    adb(s, "forward", "tcp:8081", "tcp:8081")
    adb(s, "forward", "tcp:8082", "tcp:8082")

    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)

    httpd = ThreadingHTTPServer(("127.0.0.1", HTML_PORT), H)
    print(f"page http://127.0.0.1:{HTML_PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
