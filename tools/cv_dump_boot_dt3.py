#!/usr/bin/env python3
from __future__ import annotations
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build
from patch_boot_usb import find

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq\camevision_boot_wifi_imu.img")


def ph(n):
    v = n.get("phandle")
    return struct.unpack(">I", v)[0] if v else None


def main():
    data = BOOT.read_bytes()
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    tree = build(Fdt(data[pos : pos + struct.unpack(">I", img.get("data-size"))[0]]))

    print("=== all i2c4 / spi0 / cam_clk / mipi1 / rkvpss-vir ===")
    for n in tree.walk():
        p = n.path()
        if any(x in p for x in ("/i2c4/", "/spi0/", "/cam_clk", "mipi1", "rkvpss-vir", "rkisp-vir1", "lvds1")):
            pins = n.get("rockchip,pins")
            extra = ""
            if pins:
                extra = " pins=" + str([hex(x) for x in struct.unpack(f">{len(pins)//4}I", pins)])
            print(p, "ph", ph(n), extra)

    print("\n=== sc233 regulators ===")
    for name in ("/sc233hgs-avdd", "/sc233hgs-dovdd", "/sc233hgs-dvdd"):
        n = find(tree, name)
        for k, v in n.props:
            if k == "phandle":
                continue
            if len(v) % 4 == 0 and v:
                print(name, k, [hex(x) for x in struct.unpack(f">{len(v)//4}I", v)])
            else:
                print(name, k, v)

    print("\n=== FIT slot ===")
    size = struct.unpack(">I", img.get("data-size"))[0]
    next_pos = len(data)
    for n in fit.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    print(f"size {size} slot {next_pos-pos} room {next_pos-pos-size}")


if __name__ == "__main__":
    main()
