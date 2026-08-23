#!/usr/bin/env python3
"""List the entries of the Rockchip resource sub-image inside boot.img.

Matters because older Rockchip flows keep a second copy of the kernel device
tree here as rk-kernel.dtb, and U-Boot may prefer it over the FIT fdt.
"""
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

path = Path(sys.argv[1]) if len(sys.argv) > 1 else BOOT
data = path.read_bytes()

print("FDT magics in file:")
for off, size in find_fdts(data):
    print(f"  offset {off:#x} totalsize {size}")

fit = Fdt(data)
root = build(fit)
pos = size = None
for n in root.walk():
    if n.path() == "/images/resource":
        pos = struct.unpack(">I", n.get("data-position"))[0]
        size = struct.unpack(">I", n.get("data-size"))[0]
if pos is None:
    raise SystemExit("no resource image")

blob = data[pos : pos + size]
print(f"\nresource image at {pos:#x} size {size}, magic {blob[:4]!r}")
if blob[:4] != b"RSCE":
    raise SystemExit("unexpected resource magic")

(ver, idx_ver) = struct.unpack_from("<HH", blob, 4)
hdr_blocks, entry_blocks = struct.unpack_from("<BB", blob, 8)
print(f"version {ver} index_version {idx_ver} header_blocks {hdr_blocks} "
      f"entry_blocks {entry_blocks}")

# struct resource_entry { tag[4]; name[220]; hash[32]; hash_size; f_offset; f_size; }
# all in one 512-byte block each, walked until the tag stops being "ENTR"
i = 0
while True:
    off = hdr_blocks * 512 + i * entry_blocks * 512
    if blob[off : off + 4] != b"ENTR":
        break
    name = blob[off + 4 : off + 224].split(b"\x00")[0].decode("ascii", "replace")
    hash_size, f_offset, f_size = struct.unpack_from("<III", blob, off + 256)
    start = f_offset * 512
    head = blob[start : start + 8]
    print(
        f"  [{i}] {name!r} f_offset={f_offset} blocks ({start:#x} in resource, "
        f"{pos + start:#x} in file) f_size={f_size} hash_size={hash_size} "
        f"head={head.hex()}"
    )
    if head[:4] == b"\xd0\x0d\xfe\xed":
        (total,) = struct.unpack_from(">I", blob, start + 4)
        print(f"       ^ flattened device tree, totalsize {total}")
        print(f"       entry hash field: {blob[off + 224:off + 256].hex()}")
    i += 1
print(f"{i} real entries")
