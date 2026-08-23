#!/usr/bin/env python3
"""Try OpenCV chessboard detection on the live calibration snaps."""
from __future__ import annotations

import urllib.request

import cv2
import numpy as np

FLAGS = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
SIZES = [(11, 8), (8, 11), (10, 8), (8, 10), (10, 7), (9, 6), (8, 6), (7, 5)]


def load(url: str):
    data = urllib.request.urlopen(url, timeout=8).read()
    print(url, "bytes", len(data))
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print("  decode fail")
        return None
    print("  shape", img.shape)
    return img


def try_find(gray, tag: str) -> None:
    for cols, rows in SIZES:
        ok, c = cv2.findChessboardCorners(gray, (cols, rows), FLAGS)
        print(f"  {tag} classic {cols}x{rows} {ok} {0 if c is None else len(c)}")
        if ok:
            return
    if hasattr(cv2, "findChessboardCornersSB"):
        for cols, rows in SIZES:
            ok, c = cv2.findChessboardCornersSB(
                gray, (cols, rows), cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
            )
            print(f"  {tag} SB {cols}x{rows} {ok} {0 if c is None else len(c)}")
            if ok:
                return
    big = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(2.0, (8, 8)).apply(big)
    for cols, rows in SIZES[:4]:
        ok, c = cv2.findChessboardCorners(clahe, (cols, rows), FLAGS)
        print(f"  {tag} x2+clahe {cols}x{rows} {ok}")
        if ok:
            return


def main() -> int:
    for url in (
        "http://127.0.0.1:8081/snapr0",
        "http://127.0.0.1:8081/snapr1",
        "http://127.0.0.1:8081/snap0",
        "http://127.0.0.1:8081/snap1",
    ):
        img = load(url)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        try_find(gray, url.split("/")[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
