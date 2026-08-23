#!/usr/bin/env python3
"""Rebuild the RV1126B USB gadget DTB with a real FDT library (not in-place bytes).

Stock Aura DTB: OTG PHY disabled, Type-C HUSB311 role-switch, dr_mode=otg.
This board has a CH221K sink and no HUSB311. The shipped kernel matches
rockchip,rk3576-dwc3 (rv1126b-dwc3 is absent); do not reorder compatible.
GPIO0_A5 is also SDMMC0_DET, so sdmmc0 must be off or the green LED is dead.

Edits:
  otg-port status okay, vbus-supply -> vcc5v0-sys
  dwc3 dr_mode peripheral; drop extcon / usb-role-switch / port
  USB2-only (usb3-phy disabled)
  husb311 disabled (frees GPIO0_A6 red LED)
  sdmmc0 disabled (frees GPIO0_A5 green LED)
  gpio-leds on GPIO0_A6/A5/A4 (this kernel has no /sys/class/gpio)
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

import fdt
from fdt import Node

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import find, patch_resource_copy, prop_offsets  # noqa: E402

STOCK = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\boot_usb_gadget.img")


def patch_tree(blob: bytes) -> bytes:
    hdr = Fdt(blob)
    tree = fdt.parse_dtb(blob)

    otg = tree.get_node("usb2-phy@21400000/otg-port")
    otg.set_property("status", "okay")
    # Stock points at the missing Type-C VBUS regulator. vcc5v0-sys is phandle 149.
    otg.set_property("vbus-supply", [149])

    usb = tree.get_node("usb@21500000")
    usb.set_property("dr_mode", "peripheral")
    usb.set_property("phy-names", ["usb2-phy", "usb3-phy"])
    usb.set_property("phys", [195, 196, 4])
    if usb.exist_property("maximum-speed"):
        usb.remove_property("maximum-speed")
    if usb.exist_property("usb-role-switch"):
        usb.remove_property("usb-role-switch")
    if usb.exist_subnode("port"):
        usb.remove_subnode("port")
    extcon = list(usb.get_property("extcon"))
    if extcon != [193]:
        raise SystemExit(f"extcon {extcon}, expected usb2-phy 193")

    tree.get_node("usb3-phy@21410000").set_property("status", "okay")
    tree.get_node("i2c@21120000/husb311@4e").set_property("status", "disabled")
    tree.get_node("mmc@21d60000").set_property("status", "disabled")

    g0 = list(tree.get_node("pinctrl/gpio@20600000").get_property("phandle"))[0]
    if g0 != 145:
        raise SystemExit(f"gpio0 phandle {g0}, expected 145")

    def max_phandle(n, m: int = 0) -> int:
        ph = n.get_property("phandle")
        if ph is not None:
            m = max(m, list(ph)[0])
        for c in n.nodes:
            m = max_phandle(c, m)
        return m

    new_ph = max_phandle(tree.root) + 1
    pinctrl = tree.get_node("pinctrl")
    grp = pinctrl.get_subnode("status-led")
    if grp is None:
        grp = Node("status-led")
        pinctrl.append(grp)
    pins = grp.get_subnode("status-led-pins")
    if pins is None:
        pins = Node("status-led-pins")
        grp.append(pins)
    # bank 0, pins A4/A5/A6, func GPIO, pull-none (same cell layout as stock pinctrl)
    pins.set_property("rockchip,pins", [0, 4, 0, 0x101, 0, 5, 0, 0x101, 0, 6, 0, 0x101])
    pins.set_property("phandle", [new_ph])

    leds = tree.get_node("leds")
    leds.set_property("pinctrl-names", "default")
    leds.set_property("pinctrl-0", [new_ph])
    work = leds.get_subnode("work-led")
    work.set_property("status", "disabled")
    if work.exist_property("linux,default-trigger"):
        work.remove_property("linux,default-trigger")
    # STATUS_LED_R GPIO0_A6 / G GPIO0_A5 / B GPIO0_A4, common-anode ACTIVE_LOW
    for name, pin, label, default in (
        ("led-red", 6, "status:red", "off"),
        ("led-green", 5, "status:green", "on"),
        ("led-blue", 4, "status:blue", "off"),
    ):
        node = leds.get_subnode(name)
        if node is None:
            node = Node(name)
            leds.append(node)
        node.set_property("gpios", [g0, pin, 1])
        node.set_property("label", label)
        node.set_property("default-state", default)

    new = tree.to_dtb(
        version=hdr.version,
        last_comp_version=hdr.last_comp_version,
        boot_cpuid_phys=hdr.boot_cpuid_phys,
    )
    check = fdt.parse_dtb(new)
    usb2 = check.get_node("usb@21500000")
    dr = usb2.get_property("dr_mode")
    if list(dr) != ["peripheral"]:
        raise SystemExit(f"dr_mode round-trip {dr}")
    compat = list(usb2.get_property("compatible"))
    if compat != ["rockchip,rv1126b-dwc3", "rockchip,rk3576-dwc3", "snps,dwc3"]:
        raise SystemExit(f"compatible {compat}")
    phys = list(usb2.get_property("phys"))
    if phys != [195, 196, 4]:
        raise SystemExit(f"phys {phys}")
    names = list(usb2.get_property("phy-names"))
    if names != ["usb2-phy", "usb3-phy"]:
        raise SystemExit(f"phy-names {names}")
    if usb2.exist_property("usb-role-switch"):
        raise SystemExit("usb-role-switch still present")
    if usb2.exist_subnode("port"):
        raise SystemExit("port still present")
    if list(usb2.get_property("extcon")) != [193]:
        raise SystemExit("usb2-phy extcon missing")
    if list(check.get_node("usb3-phy@21410000").get_property("status")) != ["okay"]:
        raise SystemExit("usb3-phy disabled")
    p0 = list(check.get_node("leds").get_property("pinctrl-0"))
    if not p0:
        raise SystemExit("leds pinctrl-0 missing")
    if usb2.exist_subnode("port"):
        raise SystemExit("port still present")
    for path, pin, label in (
        ("leds/led-red", 6, "status:red"),
        ("leds/led-green", 5, "status:green"),
        ("leds/led-blue", 4, "status:blue"),
    ):
        node = check.get_node(path)
        gpios = list(node.get_property("gpios"))
        if gpios[1:] != [pin, 1]:
            raise SystemExit(f"{path} gpios {gpios}")
        if list(node.get_property("label")) != [label]:
            raise SystemExit(f"{path} label {list(node.get_property('label'))}")
    if list(check.get_node("leds/work-led").get_property("status")) != ["disabled"]:
        raise SystemExit("work-led still enabled")
    st = check.get_node("usb2-phy@21400000/otg-port").get_property("status")
    if list(st) != ["okay"]:
        raise SystemExit(f"otg status {st}")
    vbus = list(check.get_node("usb2-phy@21400000/otg-port").get_property("vbus-supply"))
    if vbus != [149]:
        raise SystemExit(f"vbus-supply {vbus}")
    if list(check.get_node("mmc@21d60000").get_property("status")) != ["disabled"]:
        raise SystemExit("sdmmc0 still enabled")
    if list(check.get_node("i2c@21120000/husb311@4e").get_property("status")) != ["disabled"]:
        raise SystemExit("husb311 still enabled")
    print(f"  fdtlib dtb {len(blob)} -> {len(new)} bytes")
    return new


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else STOCK
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    data = bytearray(src.read_bytes())

    fit = Fdt(bytes(data))
    fit_root = build(fit)
    offsets = prop_offsets(fit)
    img = find(fit_root, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    next_pos = len(data)
    for n in fit_root.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    slot = next_pos - pos
    print(f"fdt at {pos:#x} size {size}, slot {slot}")

    old_hash = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            old_hash = c.get("value")
    old = bytes(data[pos : pos + size])
    if hashlib.sha256(old).digest() != old_hash:
        raise SystemExit("stock fdt hash mismatch")

    print("applying USB gadget edits with fdt library:")
    new_dtb = patch_tree(old)
    if len(new_dtb) > slot:
        raise SystemExit(f"new dtb {len(new_dtb)} > slot {slot}")

    data[pos:next_pos] = new_dtb + b"\x00" * (slot - len(new_dtb))
    if len(new_dtb) != size:
        off, plen = offsets[("/images/fdt", "data-size")]
        struct.pack_into(">I", data, off, len(new_dtb))
        print(f"  FIT data-size {size} -> {len(new_dtb)}")
    new_hash = hashlib.sha256(new_dtb).digest()
    hoff, hlen = offsets[("/images/fdt/hash", "value")]
    data[hoff : hoff + 32] = new_hash
    print(f"  FIT fdt hash {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")

    patch_resource_copy(data, fit_root, offsets, new_dtb)

    if data.find(b"RSCE") != src.read_bytes().find(b"RSCE"):
        raise SystemExit("RSCE moved")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(data))
    print(f"wrote {dst} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
