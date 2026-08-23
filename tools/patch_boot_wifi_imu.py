#!/usr/bin/env python3
"""Retarget the flashed CameVision boot DTB for this board's Wi-Fi and SPI IMU.

Hardware (V2.1 schematic, not M1):
  Wi-Fi  VS6621S80 on SDMMC1, SDIO 1FFE:6621
         WIFI_SOC_PWCTL GPIO2_A4, WIFI_RST GPIO3_B2, WIFI_INT GPIO2_A5
  IMU    LSM6DSVQTR on SPI1_M0 (schematic nets named SPI0_*):
         GPIO6_B4 CLK, GPIO6_B3 MISO, GPIO6_B2 MOSI, GPIO6_B1 CSN0
         IMU_INT1 GPIO3_B4, IMU_INT2 GPIO6_C1
  SPI1 CSN1 is GPIO6_B0 = CAM_PWDN — must not be claimed.

Does not touch USB (peripheral, high-speed) or the camera graph.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, Node, build, printable_strings  # noqa: E402
from patch_boot_usb import (  # noqa: E402
    find,
    patch_resource_copy,
    prop_offsets,
    read_mem_rsvmap,
    serialize,
    set_prop,
)

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\restore\known-good-20260819-camera-adb\camevision_boot.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\camevision_boot_wifi_imu.img")


def set_cells(node: Node, name: str, cells: list[int]) -> None:
    raw = struct.pack(f">{len(cells)}I", *cells)
    for i, (k, v) in enumerate(node.props):
        if k == name:
            old = " ".join(f"{c:#x}" for c in struct.unpack(f">{len(v)//4}I", v)) if v else ""
            node.props[i] = (name, raw)
            print(f"  {node.path()}: {name} <{old}> -> <{' '.join(f'{c:#x}' for c in cells)}>")
            return
    node.props.append((name, raw))
    print(f"  {node.path()}: {name} added")


def ensure_empty(node: Node, name: str) -> None:
    if node.get(name) is None:
        node.props.append((name, b""))
        print(f"  {node.path()}: {name} added (empty)")


def move_imu(root: Node) -> None:
    spi0 = find(root, "/spi@211e0000")
    spi1 = find(root, "/spi@211f0000")
    imu = next((c for c in spi0.children if c.name == "imu@0"), None)
    if imu is None:
        raise SystemExit("spi0 has no imu@0")
    spi0.children = [c for c in spi0.children if c is not imu]
    imu.parent = spi1
    if any(c.name == "imu@0" for c in spi1.children):
        raise SystemExit("spi1 already has imu@0")
    spi1.children.append(imu)
    print("  moved /spi@211e0000/imu@0 -> /spi@211f0000/imu@0")

    set_prop(root, "/spi@211e0000", "status", b"disabled\x00")
    set_prop(root, "/spi@211f0000", "status", b"okay\x00")
    # clk (GPIO6_B4/B3/B2) + csn0 (GPIO6_B1). Drop csn1 (GPIO6_B0 = CAM_PWDN).
    set_cells(spi1, "pinctrl-0", [0xBD, 0xBE])

    ensure_empty(imu, "spi-cpha")
    ensure_empty(imu, "spi-cpol")
    # LSM6DSV SPI is mode 3; keep 1 MHz until the bus is proven.
    set_cells(imu, "spi-max-frequency", [1_000_000])


def patch_wifi(root: Node) -> None:
    wlan = find(root, "/wireless-wlan")
    set_prop(root, "/wireless-wlan", "wifi_chip_type", b"vs6621\x00")
    set_prop(root, "/wireless-wlan", "status", b"okay\x00")
    bt = find(root, "/wireless-bluetooth")
    set_prop(root, "/wireless-bluetooth", "compatible", b"bluetooth-platdata\x00")
    set_prop(root, "/wireless-bluetooth", "status", b"okay\x00")
    # SDIO host already okay with pwrseq + vmmc; leave mmc@21f60000 alone.
    _ = wlan, bt


def verify(dtb: bytes) -> None:
    tree = build(Fdt(dtb))
    usb = find(tree, "/usb@21500000")
    if printable_strings(usb.get("dr_mode")) != ["peripheral"]:
        raise SystemExit("USB dr_mode lost")
    if printable_strings(usb.get("maximum-speed")) != ["high-speed"]:
        raise SystemExit("USB maximum-speed lost")
    if usb.get("usb-role-switch") is not None or usb.get("extcon") is not None:
        raise SystemExit("USB role-switch/extcon came back")
    cam = find(tree, "/i2c@21120000/sc233hgs@30")
    if printable_strings(cam.get("compatible")) != ["smartsens,sc233hgs"]:
        raise SystemExit("camera compatible lost")
    spi0 = find(tree, "/spi@211e0000")
    spi1 = find(tree, "/spi@211f0000")
    if printable_strings(spi0.get("status")) != ["disabled"]:
        raise SystemExit("spi0 not disabled")
    if printable_strings(spi1.get("status")) != ["okay"]:
        raise SystemExit("spi1 not okay")
    if any(c.name == "imu@0" for c in spi0.children):
        raise SystemExit("imu still on spi0")
    imu = next(c for c in spi1.children if c.name == "imu@0")
    if printable_strings(imu.get("compatible")) != ["st,lsm6dsv"]:
        raise SystemExit("imu compatible lost")
    pinctrl = struct.unpack(f">{len(spi1.get('pinctrl-0'))//4}I", spi1.get("pinctrl-0"))
    if pinctrl != (0xBD, 0xBE):
        raise SystemExit(f"spi1 pinctrl still has extra CS: {pinctrl}")
    wlan = find(tree, "/wireless-wlan")
    if printable_strings(wlan.get("wifi_chip_type")) != ["vs6621"]:
        raise SystemExit("wifi_chip_type not vs6621")
    bt = find(tree, "/wireless-bluetooth")
    if printable_strings(bt.get("compatible")) != ["bluetooth-platdata"]:
        raise SystemExit("BT compatible not rewritten")
    print("verify ok: USB HS peripheral, SC233HGS, SPI1 IMU, VS6621")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DST
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
        raise SystemExit("stored fdt hash mismatch")

    dtb = Fdt(old)
    root = build(dtb)
    print("edits:")
    move_imu(root)
    patch_wifi(root)
    new_dtb = serialize(root, read_mem_rsvmap(dtb), dtb.boot_cpuid_phys)
    print(f"new fdt {len(new_dtb)} (was {size}, slot {slot})")
    if len(new_dtb) > slot:
        raise SystemExit(f"DTB {len(new_dtb) - slot} bytes too big")
    verify(new_dtb)

    data[pos:next_pos] = new_dtb + b"\x00" * (slot - len(new_dtb))
    if len(new_dtb) != size:
        off, plen = offsets[("/images/fdt", "data-size")]
        if plen != 4:
            raise SystemExit("data-size is not a cell")
        struct.pack_into(">I", data, off, len(new_dtb))
        print(f"FIT data-size {size} -> {len(new_dtb)}")
    new_hash = hashlib.sha256(new_dtb).digest()
    hoff, _ = offsets[("/images/fdt/hash", "value")]
    data[hoff : hoff + 32] = new_hash
    print(f"FIT fdt hash {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")
    patch_resource_copy(data, fit_root, offsets, new_dtb)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(data))
    print(f"wrote {dst} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
