#!/usr/bin/env python3
"""Time stereo matcher variants on the board so the live config is measured."""
from __future__ import annotations

import os
import time

import cv2
import numpy as np


def pair(w: int, h: int, shift: int = 9):
    rng = np.random.default_rng(7)
    base = rng.integers(0, 255, (h, w + 64), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (5, 5), 0)
    left = np.ascontiguousarray(base[:, 32 : 32 + w])
    right = np.ascontiguousarray(base[:, 32 - shift : 32 - shift + w])
    return left, right


def sgbm(nd: int, bs: int):
    return cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=nd,
        blockSize=bs,
        P1=8 * bs * bs,
        P2=32 * bs * bs,
        disp12MaxDiff=2,
        uniquenessRatio=4,
        speckleWindowSize=0,
        speckleRange=0,
        preFilterCap=31,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
    )


def bm(nd: int, bs: int):
    m = cv2.StereoBM_create(numDisparities=nd, blockSize=bs)
    m.setPreFilterType(cv2.STEREO_BM_PREFILTER_XSOBEL)
    m.setPreFilterCap(31)
    m.setTextureThreshold(0)
    m.setUniquenessRatio(0)
    m.setDisp12MaxDiff(-1)
    return m


def ms(fn, l, r, n: int = 6) -> float:
    fn(l, r)
    t = time.monotonic()
    for _ in range(n):
        fn(l, r)
    return (time.monotonic() - t) * 1000 / n


def main() -> int:
    print("cpus", os.cpu_count(), "cv2", cv2.__version__, flush=True)
    for nt in (1, 2, 4):
        cv2.setNumThreads(nt)
        for w, h in ((320, 200), (256, 160)):
            l, r = pair(w, h)
            for nd in (32, 48):
                for bs in (3, 5):
                    m = sgbm(nd, bs)
                    print(
                        "t%d %dx%d sgbm nd%d bs%d %.1f ms"
                        % (nt, w, h, nd, bs, ms(m.compute, l, r)),
                        flush=True,
                    )
            m = bm(48, 15)
            print("t%d %dx%d bm nd48 bs15 %.1f ms" % (nt, w, h, ms(m.compute, l, r)), flush=True)
    cv2.setNumThreads(os.cpu_count() or 4)
    l, r = pair(320, 200)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    print("clahe %.1f ms" % ms(lambda a, b: (clahe.apply(a), clahe.apply(b)), l, r), flush=True)
    big = np.zeros((200, 320), np.uint8)
    print(
        "upscale1920 %.1f ms"
        % ms(lambda a, b: cv2.resize(a, (1920, 1200), interpolation=cv2.INTER_LINEAR), big, big),
        flush=True,
    )
    lut = np.arange(256, dtype=np.uint8).reshape(256, 1)
    full = np.zeros((1200, 1920), np.uint8)
    print("lut1920 %.1f ms" % ms(lambda a, b: cv2.LUT(a, lut), full, full), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
