#!/usr/bin/env python3
"""Dump the nodes we must rewrite for the Ego DTB."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import find  # noqa: E402

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq\camevision_boot_wifi_imu.img")


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
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    print(f"FIT fdt {pos:#x} size {size}")
    tree = build(Fdt(data[pos : pos + size]))
    print("model", printable_strings(find(tree, "/").get("model")))
    print("compat", printable_strings(find(tree, "/").get("compatible")))
    paths = [
        "/i2c@21120000",
        "/i2c@21120000/sc233hgs@30",
        "/i2c@21130000",
        "/spi@211e0000",
        "/spi@211f0000",
        "/spi@211f0000/imu@0",
        "/mmc@21d60000",
        "/mmc@21f60000",
        "/mmc@21470000",
        "/wireless-wlan",
        "/wireless-bluetooth",
        "/sdio-pwrseq",
        "/vcc3v3-wifi",
        "/gpio-leds",
        "/leds",
        "/csi2-dphy0",
        "/csi2-dphy1",
        "/mipi0-csi2",
        "/mipi1-csi2",
        "/rkcif-mipi-lvds",
        "/rkcif-mipi-lvds1",
        "/rkisp-vir0",
        "/rkisp-vir1",
        "/rkvpss-vir0",
        "/rkvpss-vir1",
        "/rkcif-mipi-lvds-sditf",
        "/rkcif-mipi-lvds1-sditf",
        "/rkisp-vir0-sditf",
        "/rkisp-vir1-sditf",
    ]
    for p in paths:
        try:
            dump(find(tree, p))
        except SystemExit:
            print(f"MISSING {p}")
        print()

    # symbols we need
    want = (
        "i2c3m1_pins", "i2c4m2_pins", "spi0m2_clk_pins", "spi0m2_csn0_pins",
        "spi1m0_clk_pins", "spi1m0_csn0_pins", "cam_clk0_pins", "cam_clk1_pins",
        "sdmmc0_clk_pins", "sdmmc0_cmd_pins", "sdmmc0_bus4_pins", "sdmmc0_detn_pins",
        "gpio0", "gpio3", "gpio4", "gpio5", "gpio6", "cru",
        "csi_dphy_input0", "csidphy0_out", "mipi0_csi2_input", "mipi0_csi2_output",
        "cif_mipi_in0", "isp_vir0", "vpss0_in", "isp_sditf0", "mipi_lvds_sditf",
    )
    sym = None
    for n in tree.walk():
        if n.name == "__symbols__":
            sym = n
            break
    print("=== symbols ===")
    for k, v in sym.props:
        if k in want:
            print(k, printable_strings(v))


if __name__ == "__main__":
    main()
