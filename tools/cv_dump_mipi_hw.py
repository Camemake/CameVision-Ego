#!/usr/bin/env python3
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build
from patch_boot_usb import find

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\camevision_boot_ego.img")
data = BOOT.read_bytes()
fit = build(Fdt(data))
img = find(fit, "/images/fdt")
pos = struct.unpack(">I", img.get("data-position"))[0]
size = struct.unpack(">I", img.get("data-size"))[0]
tree = build(Fdt(data[pos:pos+size]))
for p in (
    "/mipi2-csi2-hw@21c20000",
    "/mipi3-csi2-hw@21c30000",
    "/mipi2-csi2",
    "/mipi3-csi2",
    "/rkcif-mipi-lvds2",
):
    try:
        n = find(tree, p)
        ph = n.get("phandle")
        print(p, "phandle", hex(struct.unpack(">I", ph)[0]) if ph else None, "status", n.get("status"))
    except Exception as e:
        print(p, "MISSING", e)
