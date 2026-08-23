#!/usr/bin/env python3
"""Stream the RV1126B SDK tarball once and pull out everything needed to write
a board device tree: the rockchip dts/dtsi sources, the pinctrl headers, and an
inventory of available camera sensor drivers.
"""
from __future__ import annotations

import sys
import tarfile
import time
from pathlib import Path

DOWNLOADS = Path.home() / "Downloads"
# The SDK folder name contains a CJK comma, so locate it rather than hardcode it.
candidates = sorted(DOWNLOADS.glob("RV1126B_Linux_IPC_SDK*/RV1126B_Linux_IPC_SDK_V*.tgz"))
if not candidates:
    raise SystemExit("no SDK .tgz found under Downloads")
SDK = candidates[-1]
print("using", SDK, SDK.stat().st_size, flush=True)
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt")
OUT.mkdir(parents=True, exist_ok=True)

WANT_DIRS = (
    "arch/arm64/boot/dts/rockchip/",
    "include/dt-bindings/pinctrl/",
    "include/dt-bindings/clock/rockchip,rv1126b",
    "include/dt-bindings/power/rockchip,rv1126b",
    "include/dt-bindings/soc/rockchip",
)
SENSOR_DIR = "drivers/media/i2c/"

sensors: list[str] = []
saved = 0
scanned = 0
t0 = time.time()

with tarfile.open(SDK, "r|gz") as tf:
    for m in tf:
        scanned += 1
        if scanned % 200000 == 0:
            print(
                f"... {scanned} entries, {saved} saved, {time.time() - t0:.0f}s",
                flush=True,
            )
        name = m.name.replace("\\", "/")
        if not m.isfile():
            continue

        low = name.lower()
        if SENSOR_DIR in low and (low.endswith(".c") or low.endswith(".h")):
            sensors.append(f"{m.size}\t{name}")
            continue

        if not any(d in name for d in WANT_DIRS):
            continue
        if not (
            name.endswith(".dts")
            or name.endswith(".dtsi")
            or name.endswith(".h")
            or name.endswith("Makefile")
        ):
            continue
        if m.size > 4 * 1024 * 1024:
            continue

        fo = tf.extractfile(m)
        if fo is None:
            continue
        data = fo.read()
        dest = OUT / Path(name).name
        # keep pinctrl headers distinguishable from dts files
        if "dt-bindings" in name:
            dest = OUT / ("binding_" + Path(name).name)
        dest.write_bytes(data)
        saved += 1
        if saved % 25 == 0:
            print(f"saved {saved}: {name}", flush=True)

(OUT / "_sensor_drivers.txt").write_text("\n".join(sorted(sensors)), encoding="utf-8")
print(f"DONE scanned={scanned} saved={saved} sensors={len(sensors)} in {time.time() - t0:.0f}s")
