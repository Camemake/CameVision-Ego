#!/usr/bin/env python3
"""Dump selected FDT properties with their exact value length and bytes."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, find_fdts  # noqa: E402
from patch_boot_usb import prop_offsets  # noqa: E402

WANT = (
    "/usb2-phy@21400000/otg-port",
    "/usb@21500000",
    "/i2c@21120000/husb311@4e",
)

path = Path(sys.argv[1])
data = path.read_bytes()
off, size = max(find_fdts(data), key=lambda t: t[1])
# prefer the FIT fdt at 0x800 if present
if data[0x800:0x804] == b"\xd0\x0d\xfe\xed":
    off, size = 0x800, int.from_bytes(data[0x804:0x808], "big")
blob = data[off : off + size]
fdt = Fdt(blob)
offsets = prop_offsets(fdt)
print(f"fdt at {off:#x} size {size}")
for (p, name), (voff, plen) in sorted(offsets.items()):
    if not any(p == w or p.startswith(w + "/") for w in WANT):
        continue
    val = blob[voff : voff + plen]
    print(f"{p}  {name}  len={plen}  {val!r}")
