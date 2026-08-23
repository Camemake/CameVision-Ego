#!/usr/bin/env python3
import json
import urllib.request

for ver in ("4.10.0.84", "4.11.0.86", "4.12.0.88"):
    url = f"https://pypi.org/pypi/opencv-python-headless/{ver}/json"
    try:
        meta = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
    except Exception as exc:
        print(ver, "fail", exc)
        continue
    print("==", ver)
    for item in meta["urls"]:
        name = item.get("filename") or ""
        if "aarch64" in name:
            print(" ", name, item.get("size"))
