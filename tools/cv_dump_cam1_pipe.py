#!/usr/bin/env python3
from __future__ import annotations
import hashlib, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings
from patch_boot_usb import find

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\camevision_boot_ego.img")


def dump(n, indent=0):
    pad = "  " * indent
    print(f"{pad}{n.path() or '/'}")
    for k, v in n.props:
        if k in ("phandle", "linux,phandle"):
            print(f"{pad}  {k} = <{struct.unpack('>I', v)[0]:#x}>")
            continue
        s = printable_strings(v)
        if s:
            print(f"{pad}  {k} = {s}")
        elif v and len(v) % 4 == 0:
            cells = " ".join(f"{c:#x}" for c in struct.unpack(f">{len(v)//4}I", v))
            print(f"{pad}  {k} = <{cells}>")
        else:
            print(f"{pad}  {k} = {v[:48]!r}")
    for c in n.children:
        dump(c, indent + 1)


def main() -> int:
    data = BOOT.read_bytes()
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    tree = build(Fdt(data[pos : pos + size]))
    root = find(tree, "/")
    print("=== mipi/dphy children ===")
    for c in root.children:
        if any(x in c.name for x in ("mipi", "dphy", "rkcif-mipi", "rkisp-vir")):
            print(c.name, "status=", printable_strings(c.get("status") or b""),
                  "hw=", c.get("rockchip,hw").hex() if c.get("rockchip,hw") else None)
    print()
    for p in (
        "/csi2-dphy0",
        "/csi2-dphy1",
        "/mipi0-csi2",
        "/mipi1-csi2",
        "/csi2-dphy0-hw@21c40000",
        "/csi2-dphy1-hw@21c50000",
        "/mipi0-csi2-hw@21c00000",
        "/mipi1-csi2-hw@21c10000",
        "/rkcif-mipi-lvds",
        "/rkcif-mipi-lvds1",
    ):
        try:
            dump(find(tree, p))
        except Exception as e:
            print(p, "MISSING", e)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
