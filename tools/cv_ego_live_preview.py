#!/usr/bin/env python3
"""Live Cam 0 + Cam 1 preview over ADB. USB stays ADB.

Host HTTP MJPEG at http://127.0.0.1:8765
"""
from __future__ import annotations

import io
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
HOST, PORT = "127.0.0.1", 8765
W, H, STRIDE, FRAME = 1920, 1200, 2048, 2457600
VIEW = (960, 600)


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def cif_id0(s: str, plat: str) -> str:
    cmd = (
        f"for d in /sys/devices/platform/{plat}/video4linux/video* "
        f"/sys/devices/platform/{plat}/*/video4linux/video*; do "
        f"[ -f $d/name ] || continue; "
        f"n=$(cat $d/name); "
        f"if [ \"$n\" = stream_cif_mipi_id0 ]; then echo /dev/$(basename $d); exit 0; fi; "
        f"done; exit 1"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=15)
    lines = [x.strip() for x in (r.stdout or "").splitlines() if x.strip().startswith("/dev/")]
    if not lines:
        raise SystemExit(f"no CIF id0 on {plat}")
    return lines[0]


def raw_to_jpeg(buf: bytes, title: str) -> bytes:
    gray = bytearray(W * H)
    for y in range(H):
        src = y * STRIDE
        dst = y * W
        gray[dst : dst + W] = buf[src : src + W]
    im = Image.frombytes("L", (W, H), bytes(gray)).resize(VIEW, Image.BILINEAR)
    rgb = im.convert("RGB")
    draw = ImageDraw.Draw(rgb)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle((0, 0, 220, 52), fill=(0, 0, 0))
    draw.text((10, 8), title, fill=(255, 255, 255), font=font)
    out = io.BytesIO()
    rgb.save(out, "JPEG", quality=70)
    return out.getvalue()


class Cam:
    def __init__(self, name: str, dev: str, s: str) -> None:
        self.name = name
        self.dev = dev
        self.s = s
        self.jpeg = b""
        self.lock = threading.Lock()
        self.ok = False
        self.err = ""
        self.stop = threading.Event()

    def latest(self) -> bytes:
        with self.lock:
            return self.jpeg

    def run(self) -> None:
        cmd = (
            f"v4l2-ctl -d {self.dev} --set-fmt-video=width=1920,height=1200,pixelformat=RGGB "
            f"--stream-mmap=4 --stream-to=- --stream-poll"
        )
        print(f"{self.name} {self.dev} starting")
        errlog = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build") / f"{self.name.replace(' ', '')}.stderr.txt"
        errf = errlog.open("wb")
        p = subprocess.Popen(
            [ADB, "-s", self.s, "exec-out", "sh", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=errf,
        )
        assert p.stdout is not None
        try:
            while not self.stop.is_set():
                buf = p.stdout.read(FRAME)
                if len(buf) < FRAME:
                    self.err = f"short read {len(buf)}"
                    break
                jpg = raw_to_jpeg(buf, self.name)
                with self.lock:
                    self.jpeg = jpg
                    self.ok = True
        finally:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
            errf.close()
            print(f"{self.name} stopped {self.err}")


HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>CameVision Ego live</title>
<style>
  html,body{margin:0;background:#111;color:#eee;font-family:sans-serif}
  h1{margin:12px 16px;font-size:18px}
  .row{display:flex;gap:8px;padding:0 8px}
  .col{flex:1;min-width:0}
  img{width:100%;background:#000;display:block}
  .lab{padding:6px 8px;font-size:14px}
</style></head>
<body>
<h1>CameVision Ego live &mdash; USB ADB &mdash; turn Cam 1 lens until it matches Cam 0</h1>
<div class="row">
  <div class="col"><div class="lab">Cam 0</div><img src="/cam0.mjpg"></div>
  <div class="col"><div class="lab">Cam 1 (adjust this)</div><img src="/cam1.mjpg"></div>
</div>
</body></html>
"""


def handler(cams: dict[str, Cam]):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            key = "cam0" if self.path.startswith("/cam0") else "cam1" if self.path.startswith("/cam1") else ""
            cam = cams.get(key)
            if not cam:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    jpg = cam.latest()
                    if jpg:
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                            + str(len(jpg)).encode()
                            + b"\r\n\r\n"
                            + jpg
                            + b"\r\n"
                        )
                    time.sleep(0.05)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                return

    return H


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, port)) == 0


def main() -> int:
    s = serial()
    print("serial", s)
    cam0 = Cam("Cam 0", cif_id0(s, "rkcif-mipi-lvds"), s)
    cam1 = Cam("Cam 1", cif_id0(s, "rkcif-mipi-lvds2"), s)
    threads = [threading.Thread(target=c.run, daemon=True) for c in (cam0, cam1)]
    for t in threads:
        t.start()
    t0 = time.time()
    while time.time() - t0 < 15:
        if cam0.ok and cam1.ok:
            break
        time.sleep(0.2)
    print(f"cam0={'ok' if cam0.ok else cam0.err or 'waiting'} cam1={'ok' if cam1.ok else cam1.err or 'waiting'}")
    if not (cam0.ok or cam1.ok):
        raise SystemExit("no frames yet")
    httpd = ThreadingHTTPServer((HOST, PORT), handler({"cam0": cam0, "cam1": cam1}))
    print(f"preview http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    cam0.stop.set()
    cam1.stop.set()
    httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
