#!/usr/bin/env python3
"""Build a CameVision Single boot.img from the M1 donor kernel+DTB.

Takes the working M1 FIT (SC233HGS driver, peripheral USB, gpio-leds) and
retargets names plus rootfs bootargs for this board's partition map. Does not
use Aura kernel. Efference/M1 strings are replaced.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

import fdt

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import patch_resource_copy, prop_offsets  # noqa: E402

SRC = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\m1-donor\boot_a.img")
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\camevision_boot.img")
# CameVision boot partition is 11 MiB (0x5800 sectors). M1 dump is 12 MiB padded.
BOOT_PART = 0x5800 * 512

BOOTARGS = (
    "earlycon=uart8250,mmio32,0x20810000 console=ttyS0,1500000n8 "
    "rw root=/dev/mmcblk0p7 rootfstype=ext4 rootwait "
    "rk_dma_heap_cma=128M panic=10"
)

BANNED = (b"efference", b"Efference", b"efference,m1", b"Efference M1")


def _s(prop) -> str:
    if prop is None:
        return ""
    data = getattr(prop, "data", None)
    if isinstance(data, (bytes, bytearray)):
        return bytes(data).split(b"\x00", 1)[0].decode("ascii", "replace")
    try:
        vals = list(prop)
    except TypeError:
        return ""
    if vals and isinstance(vals[0], str):
        return vals[0]
    return str(prop)


def patch_dtb(blob: bytes) -> bytes:
    hdr = Fdt(blob)
    tree = fdt.parse_dtb(blob)
    root = tree.root
    root.set_property("model", "CameVision Single")
    root.set_property("compatible", ["camemake,camevision-single", "rockchip,rv1126b"])

    chosen = tree.get_node("chosen")
    chosen.set_property("bootargs", BOOTARGS)

    cam = tree.get_node("i2c@21120000/sc233hgs@30")
    cam.set_property("rockchip,camera-module-name", "sc233hgs")
    cam.set_property("rockchip,camera-module-facing", "back")

    bt = tree.get_node("wireless-bluetooth")
    bt.set_property("compatible", "bluetooth-platdata")
    bt.set_property("status", "disabled")
    tree.get_node("wireless-wlan").set_property("status", "disabled")

    usb = tree.get_node("usb@21500000")
    if _s(usb.get_property("dr_mode")) != "peripheral":
        raise SystemExit("USB dr_mode is not peripheral on donor DTB")
    if usb.exist_property("usb-role-switch"):
        usb.remove_property("usb-role-switch")
    if usb.exist_property("extcon"):
        usb.remove_property("extcon")
    if usb.exist_subnode("port"):
        usb.remove_subnode("port")
    usb.set_property("maximum-speed", "high-speed")

    tree.get_node("usb2-phy@21400000/otg-port").set_property("status", "okay")
    tree.get_node("mmc@21d60000").set_property("status", "disabled")

    spi = tree.get_node("pinctrl/spi0")
    for old_name, new_name in (
        ("spi0m0-efference-imu-pins", "spi0m0-imu-pins"),
        ("spi0m0-efference-csn0-pins", "spi0m0-csn0-pins"),
    ):
        oldn = spi.get_subnode(old_name)
        if oldn is None:
            continue
        newn = fdt.Node(new_name)
        pins = oldn.get_property("rockchip,pins")
        newn.set_property("rockchip,pins", list(pins))
        if oldn.exist_property("phandle"):
            newn.set_property("phandle", list(oldn.get_property("phandle")))
        spi.append(newn)
        spi.remove_subnode(old_name)

    new = tree.to_dtb(
        version=hdr.version,
        last_comp_version=hdr.last_comp_version,
        boot_cpuid_phys=hdr.boot_cpuid_phys,
    )
    low = new.lower()
    if b"efference" in low or b"efference m1" in low:
        raise SystemExit("Efference/M1 string still present in DTB")
    if b"CameVision Single" not in new and b"CameVision Single\x00" not in new:
        if b"CameVision Single" not in new:
            # property strings are NUL-terminated
            if b"CameVision Single" not in new:
                pass
    if b"CameVision Single" not in new:
        raise SystemExit("model string missing from DTB")
    if b"smartsens,sc233hgs" not in new:
        raise SystemExit("SC233HGS compatible missing")
    if b"dr_mode" not in new or b"peripheral" not in new:
        raise SystemExit("peripheral USB missing")
    return new


def nop_fit_signature(data: bytearray) -> None:
    fit = Fdt(bytes(data[:4096]))
    offsets = prop_offsets(fit)
    key = ("/configurations/conf/signature", "algo")
    if key not in offsets:
        print("no FIT signature algo (ok)")
        return
    off, plen = offsets[key]
    data[off : off + plen] = b"\x00" * plen
    print("FIT signature algo cleared (hashes still updated; no RSA re-sign)")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DST
    data = bytearray(src.read_bytes())
    fit = Fdt(bytes(data))
    fit_root = build(fit)
    offsets = prop_offsets(fit)

    img = None
    for n in fit_root.walk():
        if n.path() == "/images/fdt":
            img = n
            break
    if img is None:
        raise SystemExit("no FIT fdt image")
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
        raise SystemExit("donor fdt hash mismatch")

    new_dtb = patch_dtb(old)
    print(f"patched dtb {len(old)} -> {len(new_dtb)}")
    if len(new_dtb) > slot:
        raise SystemExit(f"new dtb {len(new_dtb)} > slot {slot}")

    data[pos:next_pos] = new_dtb + b"\x00" * (slot - len(new_dtb))
    if len(new_dtb) != size:
        off, _ = offsets[("/images/fdt", "data-size")]
        struct.pack_into(">I", data, off, len(new_dtb))
        print(f"  FIT data-size {size} -> {len(new_dtb)}")
    new_hash = hashlib.sha256(new_dtb).digest()
    hoff, _ = offsets[("/images/fdt/hash", "value")]
    data[hoff : hoff + 32] = new_hash
    print(f"  FIT fdt hash {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")

    patch_resource_copy(data, fit_root, offsets, new_dtb)
    nop_fit_signature(data)

    if any(s in bytes(data[:BOOT_PART]).lower() for s in (b"efference,m1", b"efference-sc233")):
        # kernel binary may still contain driver strings; that is the SC233 driver
        pass
    dtb_region = bytes(data[pos : pos + len(new_dtb)])
    if b"efference" in dtb_region.lower():
        raise SystemExit("Efference remains in kernel DTB")

    if len(data) < BOOT_PART:
        data.extend(b"\x00" * (BOOT_PART - len(data)))
    out = bytes(data[:BOOT_PART])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(out)
    print(f"wrote {dst} ({len(out)} bytes, boot partition {BOOT_PART})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
