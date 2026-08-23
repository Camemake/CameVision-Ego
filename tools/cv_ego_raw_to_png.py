#!/usr/bin/env python3
"""Convert first CIF RGGB8 frame (1920x1200, stride 2048) to a viewable PNG."""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("pip install pillow")

RAW = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills\cam0.raw")
PNG = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills\cam0.png")
W, H, STRIDE, FRAME = 1920, 1200, 2048, 2457600


def main() -> int:
    data = RAW.read_bytes()
    frame = data[:FRAME]
    print(f"file {len(data)} first-frame unique={len(set(frame))} min={min(frame)} max={max(frame)}")
    rgb = bytearray(W * H * 3)
    for y in range(H):
        row = frame[y * STRIDE : y * STRIDE + W]
        even = (y % 2) == 0
        for x in range(W):
            v = row[x]
            i = (y * W + x) * 3
            if even:
                if (x % 2) == 0:
                    rgb[i] = v
                else:
                    rgb[i + 1] = v
            else:
                if (x % 2) == 0:
                    rgb[i + 1] = v
                else:
                    rgb[i + 2] = v
        # simple neighbor fill for missing channels
        for x in range(W):
            i = (y * W + x) * 3
            if rgb[i] == 0 and rgb[i + 1] == 0 and rgb[i + 2] == 0:
                continue
            if rgb[i] == 0:
                rgb[i] = rgb[i + 1] or rgb[i + 2]
            if rgb[i + 1] == 0:
                rgb[i + 1] = rgb[i] or rgb[i + 2]
            if rgb[i + 2] == 0:
                rgb[i + 2] = rgb[i + 1] or rgb[i]
    Image.frombytes("RGB", (W, H), bytes(rgb)).save(PNG)
    print(f"wrote {PNG} {PNG.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
