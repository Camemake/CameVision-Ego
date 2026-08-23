#!/usr/bin/env python3
"""Inspect the flashed CameVision boot DTB + kernel for Wi-Fi / IMU support."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from kernel_strings import find_kernel, lz4_decompress  # noqa: E402

BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\restore\known-good-20260819-camera-adb\camevision_boot.img"
)
MARKERS = [
    b"st,lsm6dsv",
    b"st,lsm6dso",
    b"st,lsm6dsx",
    b"st_lsm6dsx",
    b"st_lsm6dsv",
    b"lsm6dsv",
    b"WHO_AM_I",
    b"vs6621",
    b"swt6621",
    b"skw_sdio",
    b"rk96x",
    b"1FFE",
]


def find_node(root, path: str):
    for n in root.walk():
        if n.path() == path:
            return n
    return None


def dump_node(n, indent=0) -> None:
    pad = "  " * indent
    print(f"{pad}{n.path() or '/'}")
    for k, v in n.props:
        s = printable_strings(v)
        if s:
            print(f"{pad}  {k} = {s}")
        elif len(v) % 4 == 0 and v:
            cells = " ".join(f"{c:#x}" for c in struct.unpack(f">{len(v)//4}I", v))
            print(f"{pad}  {k} = <{cells}>")
        else:
            print(f"{pad}  {k} = {v[:32]!r}")
    for c in n.children:
        dump_node(c, indent + 1)


def main() -> int:
    data = BOOT.read_bytes()
    fit = Fdt(data)
    root = build(fit)
    fdt_img = None
    for n in root.walk():
        if n.path() == "/images/fdt":
            fdt_img = n
            break
    pos = struct.unpack(">I", fdt_img.get("data-position"))[0]
    size = struct.unpack(">I", fdt_img.get("data-size"))[0]
    next_pos = len(data)
    for n in root.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    print(f"FIT fdt at {pos:#x} size {size} slot {next_pos-pos}")
    dtb = Fdt(data[pos : pos + size])
    tree = build(dtb)
    for path in (
        "/wireless-wlan",
        "/wireless-bluetooth",
        "/sdio-pwrseq",
        "/spi@211e0000",
        "/spi@211f0000",
        "/mmc@21f60000",
        "/usb@21500000",
        "/pinctrl/spi1",
        "/pinctrl/imu",
        "/pinctrl/wireless-wlan",
        "/pinctrl/sdio-pwrseq",
    ):
        n = find_node(tree, path)
        print("\n====", path, "====")
        if n is None:
            print("MISSING")
        else:
            dump_node(n)

    print("\n==== kernel markers ====")
    kpos, ksize, kcomp = find_kernel(data)
    blob = data[kpos : kpos + ksize]
    raw = lz4_decompress(blob) if kcomp == "lz4" else blob
    print(f"kernel {kcomp} decompressed {len(raw)}")
    for m in MARKERS:
        print(f"  {m.decode():16s} {'present' if m in raw else 'ABSENT':8s} count={raw.count(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
