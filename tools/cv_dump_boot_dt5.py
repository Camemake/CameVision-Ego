#!/usr/bin/env python3
from __future__ import annotations
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings
from patch_boot_usb import find

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
    print("boot.img", len(data))
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    tree = build(Fdt(data[pos : pos + size]))

    for p in (
        "/csi2-dphy1",
        "/rkcif-mipi-lvds1",
        "/rkisp-vir1",
        "/rkvpss-vir1",
        "/rkcif-mipi-lvds1-sditf",
        "/rkisp-vir1-sditf",
        "/csi2-dphy0-hw@21c40000",
        "/mipi0-csi2-hw@21c00000",
        "/mmc@21f60000",
        "/pinctrl/wireless-wlan",
        "/pinctrl/spi0",
        "/pinctrl/i2c4",
        "/pinctrl/cam_clk0",
        "/pinctrl/cam_clk1",
    ):
        try:
            dump(find(tree, p))
        except SystemExit:
            print("MISSING", p)
        print()

    print("=== phandle lookup 0x14 0x15 0x21-0x24 0xba 0xa0 0xa2 0xb7 0xb8 ===")
    want = {0x14, 0x15, 0x21, 0x22, 0x23, 0x24, 0xba, 0xa0, 0xa2, 0xb7, 0xb8, 0xfd, 0xfe, 0xf9, 0x2c, 0x34, 0x41, 0x31, 0x39}
    for n in tree.walk():
        p = ph(n)
        if p in want:
            print(f"  {p:#x} {n.path()}")

    print("\n=== imu pinctrl ===")
    for n in tree.walk():
        if "imu" in n.path().lower() or n.name.endswith("imu-pins") or "efference" in n.name:
            dump(n)
            print()

    # CLK_CAM in kernel
    kern = find(fit, "/images/kernel")
    kpos = struct.unpack(">I", kern.get("data-position"))[0]
    ksize = struct.unpack(">I", kern.get("data-size"))[0]
    k = data[kpos : kpos + ksize]
    for s in (b"CLK_CAM0_OUT", b"CLK_CAM1_OUT", b"clk_cam1_out", b"clk_cam0_out", b"cam1_out"):
        print(s, k.find(s))


if __name__ == "__main__":
    main()
