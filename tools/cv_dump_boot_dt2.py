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


def main():
    data = BOOT.read_bytes()
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    tree = build(Fdt(data[pos : pos + size]))

    print("=== aliases ===")
    try:
        a = find(tree, "/aliases")
        for k, v in a.props:
            print(k, printable_strings(v))
    except SystemExit:
        print("no aliases")

    print("\n=== gpio phandles ===")
    for n in tree.walk():
        if n.name.startswith("gpio@"):
            print(n.path(), "ph", ph(n), "compat", printable_strings(n.get("compatible")))

    print("\n=== regulators ===")
    for n in tree.walk():
        name = printable_strings(n.get("regulator-name") or b"")
        if name:
            print(n.path(), name, "ph", ph(n))

    print("\n=== pinctrl groups of interest ===")
    keys = ("spi0", "spi1", "i2c3", "i2c4", "sdmmc0", "sdmmc1", "cam_clk", "cam/", "wifi", "wireless")
    for n in tree.walk():
        p = n.path()
        if "/pinctrl/" in p and n.get("rockchip,pins"):
            if any(k in p for k in keys):
                pins = struct.unpack(f">{len(n.get('rockchip,pins'))//4}I", n.get("rockchip,pins"))
                print(f"{p} ph={ph(n)} pins={[hex(x) for x in pins]}")

    print("\n=== max phandle ===")
    mx = 0
    for n in tree.walk():
        p = ph(n)
        if p and p > mx:
            mx = p
    print(hex(mx))

    print("\n=== csi1/rkcif1 children ===")
    for path in ("/csi2-dphy1", "/rkcif-mipi-lvds1", "/rkisp-vir1"):
        n = find(tree, path)
        print(path, "children", [c.name for c in n.children], "ph", ph(n))

    print("\n=== root children matching vcc/led/wifi/sdio ===")
    for c in tree.children:
        if any(x in c.name for x in ("vcc", "vdd", "led", "wifi", "wlan", "sdio", "charger", "sc233")):
            print(c.name, "ph", ph(c), "compat", printable_strings(c.get("compatible") or b""))


if __name__ == "__main__":
    main()
