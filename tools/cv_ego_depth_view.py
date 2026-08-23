#!/usr/bin/env python3
"""Host-side stereo depth + 3D overlay from CAM0/CAM1.

Does not touch 3A, USB, or on-device ffmpeg. Uses the existing MJPEG
forwards on 8081/8082. Baseline is the board figure: 75.000 mm.
Uncalibrated: focal length is estimated from SC233HGS 1920-wide.
"""
from __future__ import annotations

import os

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import json
import socket
import struct
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

HTML = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\ego_depth.html").read_bytes()
PORT = 8767
LEFT = "http://127.0.0.1:8081/"
RIGHT = "http://127.0.0.1:8082/"
BASELINE_M = 0.075
PROC_W = 480
FULL_W, FULL_H = 1920, 1200
# ~70 deg HFOV at 1920 → f ≈ 1370 px; scale with PROC_W
FOCAL_FULL = 1370.0

lock = threading.Lock()
latest = {
    "ov0": b"",
    "ov1": b"",
    "depth": b"",
    "cloud": b'{"pts":[]}',
    "ok": False,
    "fps": 0.0,
    "swap": False,
}


def read_mjpeg(url: str, key: str, store: dict) -> None:
    while True:
        try:
            req = urllib.request.urlopen(url, timeout=8)
            buf = b""
            while True:
                chunk = req.read(8192)
                if not chunk:
                    break
                buf += chunk
                while True:
                    a = buf.find(b"\xff\xd8")
                    b = buf.find(b"\xff\xd9")
                    if a < 0 or b < 0 or b < a:
                        if a > 0:
                            buf = buf[a:]
                        if len(buf) > 3_000_000:
                            buf = buf[-400000:]
                        break
                    store[key] = buf[a : b + 2]
                    buf = buf[b + 2 :]
        except Exception:
            time.sleep(0.4)


def decode(jpg: bytes):
    if not jpg:
        return None
    arr = np.frombuffer(jpg, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def encode(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buf.tobytes() if ok else b""


def overlay(bgr, color, alpha=0.48):
    if color.shape[:2] != bgr.shape[:2]:
        color = cv2.resize(color, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_NEAREST)
    mask = (color.astype(np.int16).sum(axis=2) > 12).astype(np.float32)[:, :, None]
    out = bgr.astype(np.float32) * (1.0 - alpha * mask) + color.astype(np.float32) * (alpha * mask)
    return np.clip(out, 0, 255).astype(np.uint8)


def stereo_loop(left_src: dict, right_src: dict) -> None:
    num_d = 64
    block = 5
    stereo = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_d,
        blockSize=block,
        P1=8 * 3 * block * block,
        P2=32 * 3 * block * block,
        disp12MaxDiff=2,
        uniquenessRatio=12,
        speckleWindowSize=80,
        speckleRange=2,
        preFilterCap=31,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )
    scale = PROC_W / float(FULL_W)
    proc_h = int(FULL_H * scale)
    fpx = FOCAL_FULL * scale
    n = 0
    t0 = time.monotonic()
    swap = False
    while True:
        ljpg, rjpg = left_src.get("jpg"), right_src.get("jpg")
        L, R = decode(ljpg), decode(rjpg)
        if L is None or R is None:
            time.sleep(0.05)
            continue
        Ls = cv2.resize(L, (PROC_W, proc_h), interpolation=cv2.INTER_AREA)
        Rs = cv2.resize(R, (PROC_W, proc_h), interpolation=cv2.INTER_AREA)
        g0 = cv2.cvtColor(Ls, cv2.COLOR_BGR2GRAY)
        g1 = cv2.cvtColor(Rs, cv2.COLOR_BGR2GRAY)
        # small vertical align (uncalibrated pair)
        try:
            (dx, dy), _ = cv2.phaseCorrelate(np.float32(g0), np.float32(g1))
            if abs(dy) < 40:
                M = np.float32([[1, 0, 0], [0, 1, -dy]])
                g1 = cv2.warpAffine(g1, M, (PROC_W, proc_h), flags=cv2.INTER_LINEAR)
                Rs = cv2.warpAffine(Rs, M, (PROC_W, proc_h), flags=cv2.INTER_LINEAR)
        except cv2.error:
            pass
        a = stereo.compute(g0, g1)
        b = stereo.compute(g1, g0)
        va = a[a > 16]
        vb = b[b > 16]
        use = a
        left_bgr, right_bgr = Ls, Rs
        if vb.size > va.size * 1.15:
            use = b
            left_bgr, right_bgr = Rs, Ls
            swap = True
        else:
            swap = False
        disp = use.astype(np.float32) / 16.0
        valid = disp > 1.0
        depth = np.zeros_like(disp)
        depth[valid] = (fpx * BASELINE_M) / disp[valid]
        vis = np.clip(disp * (255.0 / float(num_d)), 0, 255).astype(np.uint8)
        vis[~valid] = 0
        color = cv2.applyColorMap(vis, cv2.COLORMAP_TURBO)
        color[~valid] = 0
        ov_l = overlay(left_bgr, color)
        ov_r = overlay(right_bgr, color)
        cv2.putText(ov_l, "CAM0 + depth" if not swap else "CAM1 + depth", (12, proc_h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(ov_r, "CAM1 + depth" if not swap else "CAM0 + depth", (12, proc_h - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        # 3D points in metres, origin at left camera
        step = 4
        ys, xs = np.where(valid[::step, ::step])
        pts = []
        if xs.size:
            xs = xs * step
            ys = ys * step
            # cap
            if xs.size > 9000:
                pick = np.linspace(0, xs.size - 1, 9000, dtype=np.int32)
                xs, ys = xs[pick], ys[pick]
            cx, cy = PROC_W * 0.5, proc_h * 0.5
            z = depth[ys, xs]
            x = (xs - cx) * z / fpx
            y = (ys - cy) * z / fpx
            cols = left_bgr[ys, xs][:, ::-1] / 255.0  # RGB
            # drop far/near outliers
            keep = (z > 0.15) & (z < 8.0)
            x, y, z, cols = x[keep], y[keep], z[keep], cols[keep]
            # OpenGL-ish: X right, Y up, Z forward
            pts = np.column_stack((x, -y, z, cols)).astype(np.float32)
            pts = pts.tolist()
        n += 1
        now = time.monotonic()
        fps = latest["fps"]
        if now - t0 >= 1.0:
            fps = n / (now - t0)
            n = 0
            t0 = now
        with lock:
            latest["ov0"] = encode(ov_l)
            latest["ov1"] = encode(ov_r)
            latest["depth"] = encode(color)
            latest["cloud"] = json.dumps({"pts": pts, "baseline_mm": 75.0, "swap": swap}).encode()
            latest["ok"] = True
            latest["fps"] = fps
            latest["swap"] = swap
        time.sleep(0.02)


def mjpeg_stream(get_jpg):
    def gen():
        last = b""
        while True:
            with lock:
                jpg = get_jpg()
            if jpg and jpg is not last:
                last = jpg
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpg)).encode()
                    + b"\r\n\r\n"
                    + jpg
                    + b"\r\n"
                )
            time.sleep(0.04)
    return gen


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            body = HTML
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/cloud.json":
            with lock:
                body = latest["cloud"]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        key = {"/ov0": "ov0", "/ov1": "ov1", "/depth": "depth"}.get(path)
        if key:
            self.send_response(200)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                last = b""
                while True:
                    with lock:
                        jpg = latest[key]
                    if jpg and jpg is not last:
                        last = jpg
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                            + str(len(jpg)).encode()
                            + b"\r\n\r\n"
                            + jpg
                            + b"\r\n"
                        )
                    time.sleep(0.04)
            except Exception:
                return
        self.send_error(404)


def main() -> int:
    left_src: dict = {"jpg": b""}
    right_src: dict = {"jpg": b""}
    threading.Thread(target=read_mjpeg, args=(LEFT, "jpg", left_src), daemon=True).start()
    threading.Thread(target=read_mjpeg, args=(RIGHT, "jpg", right_src), daemon=True).start()
    threading.Thread(target=stereo_loop, args=(left_src, right_src), daemon=True).start()
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"depth page http://127.0.0.1:{PORT}/", flush=True)
    print("this is the live 3D view — leave it running", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
