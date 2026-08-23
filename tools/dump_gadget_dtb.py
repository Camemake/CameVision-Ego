#!/usr/bin/env python3
"""Print USB and LED nodes from a boot.img FIT DTB, with phandles resolved."""
from __future__ import annotations

import sys
from pathlib import Path

import fdt

STOCK = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)
GADGET = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\boot_usb_gadget.img")


def fit_dtb(img: bytes) -> bytes:
    size = int.from_bytes(img[0x804:0x808], "big")
    return img[0x800 : 0x800 + size]


def prop_vals(p) -> list:
    if p is None:
        return []
    if type(p).__name__ == "Property":
        return []
    return list(p)


def ph_map(tree) -> dict[int, str]:
    m: dict[int, str] = {}

    def walk(n, path: str) -> None:
        p = "/" if n.name in ("/", "") else path.rstrip("/") + "/" + n.name
        ph = n.get_property("phandle")
        if ph is not None:
            m[prop_vals(ph)[0]] = p
        for c in n.nodes:
            walk(c, p if n.name not in ("/", "") else "")

    walk(tree.root, "")
    return m


def show(tree, pm: dict[int, str], path: str) -> None:
    n = tree.get_node(path)
    print(f" -- {path}")
    for p in n.props:
        vals = prop_vals(p)
        extra = ""
        if p.name in ("phys", "gpios", "vbus-supply", "extcon", "pinctrl-0") or p.name.endswith(
            "-supply"
        ):
            if vals:
                extra = " -> " + pm.get(vals[0], hex(vals[0]))
                if len(vals) > 1:
                    extra += f" rest={vals[1:]}"
        print(f"    {p.name:28s} {type(p).__name__:12s} {vals!r}{extra}")
    for c in n.nodes:
        print(f"    child {c.name}")


def dump(title: str, blob: bytes) -> None:
    print(f"==== {title} len={len(blob)}")
    tree = fdt.parse_dtb(blob)
    pm = ph_map(tree)
    for path in (
        "usb@21500000",
        "usb2-phy@21400000/otg-port",
        "usb3-phy@21410000",
        "mmc@21d60000",
        "i2c@21120000/husb311@4e",
        "leds",
    ):
        show(tree, pm, path)
    for c in tree.get_node("leds").nodes:
        show(tree, pm, "leds/" + c.name)
    print()


def main() -> int:
    dump("STOCK", fit_dtb(STOCK.read_bytes()))
    if GADGET.exists():
        dump("GADGET", fit_dtb(GADGET.read_bytes()))
    raw = fit_dtb(STOCK.read_bytes())
    t = fdt.parse_dtb(raw)
    rt = t.to_dtb(
        version=t.header.version,
        last_comp_version=t.header.last_comp_version,
        boot_cpuid_phys=t.header.boot_cpuid_phys,
    )
    usb1 = [p.name for p in fdt.parse_dtb(raw).get_node("usb@21500000").props]
    usb2 = [p.name for p in fdt.parse_dtb(rt).get_node("usb@21500000").props]
    print("noop reserialize", len(raw), "->", len(rt))
    print("usb missing after round-trip", set(usb1) - set(usb2))
    print("usb extra after round-trip", set(usb2) - set(usb1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
