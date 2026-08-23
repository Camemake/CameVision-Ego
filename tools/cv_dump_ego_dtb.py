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
            print(f"{pad}  {k} = {v[:40]!r}")
    for c in n.children:
        dump(c, indent + 1)


def main():
    data = BOOT.read_bytes()
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    blob = data[pos : pos + size]
    stored = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            stored = c.get("value")
    calc = hashlib.sha256(blob).digest()
    print(f"FIT fdt pos={pos:#x} size={size} hash_ok={calc == stored}")
    print(f"root props: {[k for k,_ in find(build(Fdt(blob)), '/').props]}")
    tree = build(Fdt(blob))
    for p in (
        "/",
        "/i2c@21120000/sc233hgs@30",
        "/i2c@21130000",
        "/spi@211e0000",
        "/spi@211f0000/imu@0",
        "/mmc@21d60000",
        "/wireless-wlan",
        "/sc233hgs-avdd",
        "/sc233hgs-dvdd",
        "/vcc1v5-cam",
        "/vcc1v8-sd",
        "/csi2-dphy1",
        "/mipi1-csi2",
        "/pinctrl/i2c4/i2c4m2-pins",
        "/pinctrl/spi0/spi0m2-clk-pins",
        "/pinctrl/wireless-wlan/wifi-wake-host",
        "/pinctrl/wireless-wlan/wifi-soc-pwctl",
        "/usb@21500000",
        "/gpio-charger",
    ):
        dump(find(tree, p))
        print()


if __name__ == "__main__":
    main()
