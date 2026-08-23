#!/usr/bin/env python3
"""Recompute the FIT sub-image sha256 hashes and compare with the stored values.

Confirms the hash covers exactly data-size bytes at data-position before we rely
on that model to patch an image.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402

BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)

path = Path(sys.argv[1]) if len(sys.argv) > 1 else BOOT
data = path.read_bytes()
fdt = Fdt(data)
root = build(fdt)

ok = True
for n in root.walk():
    p = n.path()
    if not (p.startswith("/images/") and p.count("/") == 2):
        continue
    pos = n.get("data-position")
    size = n.get("data-size")
    if pos is None or size is None:
        print(f"{p}: embedded data, skipped")
        continue
    pos = struct.unpack(">I", pos)[0]
    size = struct.unpack(">I", size)[0]
    for c in n.children:
        algo = printable_strings(c.get("algo") or b"")
        stored = c.get("value")
        if not algo or algo[0] != "sha256" or stored is None:
            continue
        calc = hashlib.sha256(data[pos : pos + size]).digest()
        match = calc == stored
        ok &= match
        print(f"{p:20s} pos={pos:<9} size={size:<9} sha256 {'MATCH' if match else 'MISMATCH'}")
        if not match:
            print(f"   stored {stored.hex()}")
            print(f"   calc   {calc.hex()}")

print("\nall hashes match" if ok else "\nhash model is wrong")
