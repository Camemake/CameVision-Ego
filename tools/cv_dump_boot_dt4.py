#!/usr/bin/env python3
from __future__ import annotations
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings
from patch_boot_usb import find, resource_dtb_slot

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq\camevision_boot_wifi_imu.img")


def ph(n):
    v = n.get("phandle")
    return struct.unpack(">I", v)[0] if v else None


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
            print(f"{pad}  {k} = {v[:40]!r}")
    for c in n.children:
        dump(c, indent + 1)


def main():
    data = BOOT.read_bytes()
    fit = build(Fdt(data))
    print("=== FIT images ===")
    for n in fit.walk():
        if n.get("data-position"):
            pos = struct.unpack(">I", n.get("data-position"))[0]
            size = struct.unpack(">I", n.get("data-size"))[0]
            print(f"  {n.path():40s} pos={pos:#x} size={size} end={pos+size:#x}")

    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    tree = build(Fdt(data[pos : pos + size]))

    print("\n=== pcfg ===")
    for n in tree.walk():
        if n.name.startswith("pcfg-") or n.name.startswith("pcfg_"):
            print(n.path(), "ph", ph(n), [k for k, _ in n.props])

    print("\n=== gpio banks ===")
    for n in tree.walk():
        if n.path().startswith("/pinctrl/gpio@"):
            print(n.path(), "ph", ph(n))

    print("\n=== CSI0 / cam / imu / wifi / sd ===")
    for p in (
        "/csi2-dphy0",
        "/mipi0-csi2",
        "/rkcif-mipi-lvds",
        "/rkcif-mipi-lvds-sditf",
        "/rkisp-vir0",
        "/rkisp-vir0-sditf",
        "/rkvpss-vir0",
        "/i2c@21120000/sc233hgs@30",
        "/i2c@21130000",
        "/spi@211e0000",
        "/spi@211f0000",
        "/spi@211f0000/imu@0",
        "/mmc@21d60000",
        "/wireless-wlan",
        "/sdio-pwrseq",
        "/vcc3v3-wifi",
        "/sc233hgs-avdd",
        "/sc233hgs-dovdd",
        "/sc233hgs-dvdd",
        "/mipi1-csi2-hw@21c10000",
        "/csi2-dphy1-hw@21c50000",
    ):
        try:
            dump(find(tree, p))
        except SystemExit:
            print("MISSING", p)
        print()

    res = find(fit, "/images/resource")
    rpos = struct.unpack(">I", res.get("data-position"))[0]
    rsize = struct.unpack(">I", res.get("data-size"))[0]
    start, cur, slot, entry_off, hs = resource_dtb_slot(data[rpos : rpos + rsize])
    print(f"resource rk-kernel.dtb size {cur} slot {slot} hash {hs}")


if __name__ == "__main__":
    main()
