#!/usr/bin/env python3
"""Download opencv-python-headless aarch64 cp312 into build/wheels."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

DST = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\wheels")
DST.mkdir(parents=True, exist_ok=True)


def main() -> int:
    url = "https://pypi.org/pypi/opencv-python-headless/4.10.0.84/json"
    meta = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
    picked = None
    for item in meta["urls"]:
        name = item.get("filename") or ""
        if "aarch64" in name and name.endswith(".whl") and "abi3" in name:
            picked = item
            break
    if not picked:
        raise SystemExit("no aarch64 cp312 wheel")
    dest = DST / picked["filename"]
    print("get", picked["url"], flush=True)
    print("to", dest, "size", picked.get("size"), flush=True)
    urllib.request.urlretrieve(picked["url"], dest)
    print("saved", dest.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
