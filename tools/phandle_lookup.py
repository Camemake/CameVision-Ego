#!/usr/bin/env python3
"""Resolve raw phandle values from the decompiled DTB back to their labels."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, find_fdts, printable_strings  # noqa: E402

BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)

data = BOOT.read_bytes()
off, size = max(find_fdts(data), key=lambda t: t[1])
fdt = Fdt(data[off : off + size])
root = build(fdt)

ph_to_path: dict[int, str] = {}
for n in root.walk():
    v = n.get("phandle")
    if v and len(v) == 4:
        ph_to_path[struct.unpack(">I", v)[0]] = n.path()

path_to_label: dict[str, str] = {}
for n in root.walk():
    if n.name == "__symbols__":
        for k, v in n.props:
            s = printable_strings(v)
            if s:
                path_to_label[s[0]] = k

for arg in sys.argv[1:]:
    ph = int(arg, 0)
    path = ph_to_path.get(ph, "?")
    print(f"{ph:#x} -> {path_to_label.get(path, '(no label)')}   {path}")
