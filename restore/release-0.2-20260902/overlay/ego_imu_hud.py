#!/usr/bin/env python3
"""Dual-IMU HUD sampler. Sysfs oneshot at high ODR (buffer has no trigger here)."""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path

PORT = 8083
ODR = "480"
BASELINE_MM = 75.0
G = 9.80665
RAD2DEG = 57.29577951308232

IMUS = (
    {
        "id": "imu0",
        "cam": 0,
        "bus": "spi0.0",
        "accel": Path("/sys/bus/iio/devices/iio:device2"),
        "gyro": Path("/sys/bus/iio/devices/iio:device1"),
    },
    {
        "id": "imu1",
        "cam": 1,
        "bus": "spi1.0",
        "accel": Path("/sys/bus/iio/devices/iio:device4"),
        "gyro": Path("/sys/bus/iio/devices/iio:device3"),
    },
)

lock = threading.Lock()
state = {
    "t_unix_ns": 0,
    "t_iso": "",
    "t_mono_ns": 0,
    "baseline_mm": BASELINE_MM,
    "odr_hz": float(ODR),
    "read_hz": 0.0,
    "imu0": {},
    "imu1": {},
}


def ns_realtime() -> int:
    return time.clock_gettime_ns(time.CLOCK_REALTIME)


def ns_mono() -> int:
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def iso_now(ns: int) -> str:
    sec, nsec = divmod(ns, 1_000_000_000)
    tm = time.localtime(sec)
    off = -time.timezone if (not tm.tm_isdst) else -time.altzone
    sign = "+" if off >= 0 else "-"
    hh, mm = divmod(abs(off) // 60, 60)
    return time.strftime("%Y-%m-%dT%H:%M:%S", tm) + f".{nsec//1000000:03d}{sign}{hh:02d}:{mm:02d}"


def fopen(path: Path):
    return open(path, "rb", buffering=0)


def fread_int(f) -> int:
    f.seek(0)
    return int(f.read().strip() or b"0")


def disable_buffers() -> None:
    for d in (
        Path("/sys/bus/iio/devices/iio:device1"),
        Path("/sys/bus/iio/devices/iio:device2"),
        Path("/sys/bus/iio/devices/iio:device3"),
        Path("/sys/bus/iio/devices/iio:device4"),
    ):
        try:
            (d / "buffer" / "enable").write_text("0")
        except OSError:
            pass


def _touch(imu_id: str, patch: dict) -> None:
    t_unix = ns_realtime()
    t_mono = ns_mono()
    patch["t_unix_ns"] = t_unix
    patch["t_iso"] = iso_now(t_unix)
    patch["t_mono_ns"] = t_mono
    with lock:
        rec = dict(state.get(imu_id) or {})
        rec.update(patch)
        if "ax" in rec and "ay" in rec and "az" in rec:
            rec["a_g"] = (rec["ax"] ** 2 + rec["ay"] ** 2 + rec["az"] ** 2) ** 0.5 / G
        rec["cam"] = patch.get("cam", rec.get("cam"))
        rec["bus"] = patch.get("bus", rec.get("bus"))
        state[imu_id] = rec
        state["t_unix_ns"] = t_unix
        state["t_iso"] = patch["t_iso"]
        state["t_mono_ns"] = t_mono
        h0 = (state.get("imu0") or {}).get("read_hz") or 0.0
        h1 = (state.get("imu1") or {}).get("read_hz") or 0.0
        state["read_hz"] = h0 + h1
        state["odr_hz"] = float(ODR)
        state["baseline_mm"] = BASELINE_MM


def sample_half(imu: dict, kind: str) -> None:
    a, g = imu["accel"], imu["gyro"]
    try:
        ((a if kind == "accel" else g) / "sampling_frequency").write_text(ODR)
    except OSError:
        pass
    if kind == "accel":
        files = (
            fopen(a / "in_accel_x_raw"),
            fopen(a / "in_accel_y_raw"),
            fopen(a / "in_accel_z_raw"),
        )
        scl = float((a / "in_accel_scale").read_text())
        keys = ("ax", "ay", "az")
    else:
        files = (
            fopen(g / "in_anglvel_x_raw"),
            fopen(g / "in_anglvel_y_raw"),
            fopen(g / "in_anglvel_z_raw"),
        )
        scl = float((g / "in_anglvel_scale").read_text()) * RAD2DEG
        keys = ("gx", "gy", "gz")
    n = 0
    t0 = time.monotonic()
    hz = 0.0
    while True:
        vals = [fread_int(f) * scl for f in files]
        n += 1
        now = time.monotonic()
        if now - t0 >= 0.5:
            hz = n / (now - t0)
            n = 0
            t0 = now
        patch = {keys[0]: vals[0], keys[1]: vals[1], keys[2]: vals[2], "read_hz": hz, "cam": imu["cam"], "bus": imu["bus"]}
        _touch(imu["id"], patch)


def handle(conn: socket.socket) -> None:
    try:
        req = conn.recv(1024)
        if b"GET /" not in req:
            return
        with lock:
            body = json.dumps(state, separators=(",", ":")).encode()
        conn.sendall(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Cache-Control: no-store\r\n"
            b"Content-Length: "
            + str(len(body)).encode()
            + b"\r\n\r\n"
            + body
        )
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def serve() -> None:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))
    sock.listen(8)
    print(f"imu hud :{PORT} odr={ODR}", flush=True)
    while True:
        conn, _ = sock.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


def main() -> int:
    os.environ.setdefault("TZ", "UTC-2")
    time.tzset()
    disable_buffers()
    for imu in IMUS:
        threading.Thread(target=sample_half, args=(imu, "accel"), daemon=True).start()
        threading.Thread(target=sample_half, args=(imu, "gyro"), daemon=True).start()
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
