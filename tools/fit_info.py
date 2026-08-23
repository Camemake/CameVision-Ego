#!/usr/bin/env python3
"""Describe the FIT container in a Rockchip boot.img.

Prints every sub-image with its external data offset/size and any hash or
signature nodes, so we know exactly what has to be recomputed after editing an
embedded blob.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402

BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else BOOT
    data = path.read_bytes()
    print(f"file {path.name} size {len(data)}")

    if data[:4] != b"\xd0\x0d\xfe\xed":
        raise SystemExit("no FDT magic at offset 0, not a plain FIT")

    fdt = Fdt(data)
    print(f"FIT header totalsize {fdt.totalsize} (data starts after alignment)")
    root = build(fdt)

    def prop(node, name):
        v = node.get(name)
        if v is None:
            return None
        s = printable_strings(v)
        if s:
            return s[0] if len(s) == 1 else s
        if len(v) == 4:
            return struct.unpack(">I", v)[0]
        return v

    for n in root.walk():
        path_str = n.path()
        if path_str.startswith("/images/") and path_str.count("/") == 2:
            print(f"\n=== {path_str} ===")
            for key in (
                "description",
                "type",
                "compression",
                "arch",
                "os",
                "load",
                "entry",
                "data-offset",
                "data-size",
                "data-position",
            ):
                v = prop(n, key)
                if v is not None:
                    if key in ("data-offset", "data-size", "load", "entry"):
                        print(f"  {key:14s} {v} ({v:#x})")
                    else:
                        print(f"  {key:14s} {v}")
            if n.get("data") is not None:
                print(f"  data           embedded, {len(n.get('data'))} bytes")
            for c in n.children:
                algo = prop(c, "algo")
                val = c.get("value")
                print(
                    f"  child {c.name}: algo={algo} value={val.hex() if val else None}"
                )

    print("\n=== configurations ===")
    for n in root.walk():
        if n.path().startswith("/configurations"):
            print(f"  {n.path()}")
            for k, v in n.props:
                s = printable_strings(v)
                print(f"     {k} = {s if s else v.hex()}")

    signed = [n.path() for n in root.walk() if "signature" in n.name]
    print(f"\nsignature nodes: {signed if signed else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
