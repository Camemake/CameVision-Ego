#!/usr/bin/env python3
"""Report whether given strings exist in the decompressed kernel image.

Used to tell what the shipped kernel actually supports, since the SDK tarball is
a bare git mirror and we have no kernel source to read.
"""
from __future__ import annotations

import sys
from pathlib import Path

KERNEL = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt\kernel.bin")

DEFAULT = [
    "rockchip,vbus-always-on",
    "vbus-always-on",
    "rockchip,utmi-avalid",
    "dr_mode",
    "maximum-speed",
    "usb-role-switch",
    "rv1126b-usb2phy",
    "otg-bvalid",
    "linestate",
    "vbus-supply",
    "configfs",
    "dwc3-rockchip",
    "rv1126b-usb3-phy",
    "naneng-combphy",
    "no-hnp-srp-support",
    "snps,dwc3",
    "gadget",
]

raw = KERNEL.read_bytes()
print(f"{KERNEL.name}: {len(raw)} bytes\n")
for s in sys.argv[1:] or DEFAULT:
    b = s.encode()
    n = raw.count(b)
    print(f"  {s:26s} {'present' if n else 'ABSENT':8s} count={n}")
