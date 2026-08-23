#!/usr/bin/env python3
"""On-device MJPEG HTTP from an ISP mainpath. USB stays ADB; host forwards the port."""
from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time

W, H = 1920, 1200


def frames(dev: str):
    cmd = (
        f"v4l2-ctl -d {dev} --set-fmt-video=width={W},height={H},pixelformat=NV12 "
        f"--stream-mmap=8 --stream-to=- --stream-poll "
        f"| ffmpeg -hide_banner -loglevel error -f rawvideo -pix_fmt nv12 "
        f"-video_size {W}x{H} -i - -vf hflip,vflip -q:v 5 -f mjpeg pipe:1"
    )
    proc = subprocess.Popen(
        ["sh", "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdout is not None
    buf = b""
    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk
        while True:
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9")
            if start < 0 or end < 0 or end < start:
                if start > 0:
                    buf = buf[start:]
                if len(buf) > 4_000_000:
                    buf = buf[-400000:]
                break
            jpg = buf[start : end + 2]
            buf = buf[end + 2 :]
            yield jpg


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: ego_mjpeg.py /dev/videoN PORT\n")
        return 2
    dev, port = sys.argv[1], int(sys.argv[2])
    latest = {"jpg": b""}
    lock = threading.Lock()

    def grab() -> None:
        for jpg in frames(dev):
            with lock:
                latest["jpg"] = jpg

    threading.Thread(target=grab, daemon=True).start()
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(4)
    print(f"mjpeg {dev} :{port}", flush=True)
    while True:
        conn, _ = sock.accept()
        threading.Thread(target=serve, args=(conn, latest, lock), daemon=True).start()


def serve(conn: socket.socket, latest: dict, lock: threading.Lock) -> None:
    try:
        conn.recv(1024)
        hdr = (
            b"HTTP/1.1 200 OK\r\n"
            b"Cache-Control: no-cache\r\n"
            b"Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n"
        )
        conn.sendall(hdr)
        last = b""
        while True:
            with lock:
                jpg = latest["jpg"]
            if jpg and jpg is not last:
                last = jpg
                conn.sendall(
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpg)).encode()
                    + b"\r\n\r\n"
                    + jpg
                    + b"\r\n"
                )
            time.sleep(0.04)
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
