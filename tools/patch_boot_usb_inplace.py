#!/usr/bin/env python3
"""In-place USB gadget enable for the stock RV1126B boot.img DTB.

Does NOT reserialize the tree. Applied to both DTB copies (FIT fdt and
resource rk-kernel.dtb), then hashes are recomputed. No string-table edits.

  1. otg-port status              "disabled" -> "okay" padded to 9 bytes
  2. otg-port vbus-supply         typec GPIO regulator -> vcc5v0_sys
  3. husb311 / sdmmc0 status      "okay" -> "fail" (same 5 bytes)
  4. NOP usb-role-switch and extcon properties; NOP Type-C port node
  5. keep compatible order (rk3576-dwc3 is what the kernel matches)
  6. dr_mode otg -> peripheral by taking 8 bytes from the following phys
     header; rebuild phys as usb2-only
  7. work-led gpios               GPIO0_C7 -> GPIO0_A5 ACTIVE_LOW (D1 green)
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import find, prop_offsets, resource_dtb_slot  # noqa: E402

FDT_BEGIN_NODE = 0x1
FDT_END_NODE = 0x2
FDT_PROP = 0x3
FDT_NOP = 0x4
FDT_END = 0x9

STOCK = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\boot_usb_gadget.img")


def patch_one_dtb(dtb: bytearray) -> list[str]:
    orig_len = len(dtb)
    fdt = Fdt(bytes(dtb))
    offs = prop_offsets(fdt)
    log: list[str] = []

    voff, plen = offs[("/usb2-phy@21400000/otg-port", "status")]
    old = bytes(dtb[voff : voff + plen])
    if old != b"disabled\x00":
        raise SystemExit(f"otg-port status unexpected: {old!r}")
    if plen != 9:
        raise SystemExit(f"otg-port status len {plen}, expected 9")
    dtb[voff : voff + plen] = b"okay\x00\x00\x00\x00\x00"
    log.append(f"otg-port status {old!r} -> okay (padded)")

    voff, plen = offs[("/usb2-phy@21400000/otg-port", "vbus-supply")]
    old = bytes(dtb[voff : voff + plen])
    if old != b"\x00\x00\x00\x9a":
        raise SystemExit(f"otg-port vbus-supply unexpected: {old.hex()}")
    dtb[voff : voff + plen] = b"\x00\x00\x00\x95"
    log.append("otg-port vbus-supply 0x9a (typec) -> 0x95 (vcc5v0_sys)")

    a = "/usb@21500000"
    v_dr, l_dr = offs[(a, "dr_mode")]
    v_phys, l_phys = offs[(a, "phys")]
    if l_dr != 4 or bytes(dtb[v_dr : v_dr + 4]) != b"otg\x00":
        raise SystemExit(f"dr_mode unexpected {bytes(dtb[v_dr:v_dr+l_dr])!r}")
    if l_phys != 12:
        raise SystemExit(f"phys len {l_phys}")
    phys_hdr = v_phys - 12
    if phys_hdr != v_dr + 4:
        raise SystemExit(f"dr_mode not adjacent to phys: {v_dr:#x} {phys_hdr:#x}")
    tag, oldlen, phys_nameoff = struct.unpack_from(">III", dtb, phys_hdr)
    if tag != 3 or oldlen != 12:
        raise SystemExit("phys header unexpected")
    struct.pack_into(">I", dtb, v_dr - 8, 11)
    peri = bytes([0x70, 0x65, 0x72, 0x69, 0x70, 0x68, 0x65, 0x72, 0x61, 0x6C, 0x00, 0x00])
    dtb[v_dr : v_dr + 12] = peri
    new_phys_hdr = v_dr + 12
    struct.pack_into(">III", dtb, new_phys_hdr, 3, 4, phys_nameoff)
    dtb[new_phys_hdr + 12 : new_phys_hdr + 16] = b"\x00\x00\x00\xc3"
    log.append("dr_mode peripheral; phys usb2-only (in-place, Linux previously stayed up)")

    voff, plen = offs[(a, "phy-names")]
    if plen != 18 or bytes(dtb[voff : voff + 9]) != b"usb2-phy" + bytes([0]):
        raise SystemExit(f"phy-names unexpected {bytes(dtb[voff:voff+plen])!r}")
    struct.pack_into(">I", dtb, voff - 8, 9)
    dtb[voff + 12 : voff + 20] = struct.pack(">II", 4, 4)
    log.append("phy-names usb2-phy only")

    nop_prop(dtb, *offs[(a, "usb-role-switch")])
    log.append("NOP usb-role-switch")

    nop_subtree(dtb, Fdt(bytes(dtb)), "/usb@21500000/port")
    log.append("NOP /usb@21500000/port")

    root = build(Fdt(bytes(dtb)))
    if "/usb@21500000/port" in {n.path() for n in root.walk()}:
        raise SystemExit("port node still present after NOP")
    dwc = find(root, "/usb@21500000")
    if dwc.get("dr_mode") != b"peripheral\x00":
        raise SystemExit(f"dr_mode {dwc.get('dr_mode')!r}")
    if dwc.get("phys") != b"\x00\x00\x00\xc3":
        raise SystemExit(f"phys {dwc.get('phys')!r}")
    if dwc.get("extcon") != b"\x00\x00\x00\xc1":
        raise SystemExit(f"extcon {dwc.get('extcon')!r}")
    names = [k for k, _ in dwc.props]
    if "usb-role-switch" in names:
        raise SystemExit("usb-role-switch still present")
    if find(root, "/leds/work-led").get("gpios") != b"\x00\x00\x00\x91\x00\x00\x00\x17\x00\x00\x00\x00":
        raise SystemExit("work-led was modified")
    if find(root, "/mmc@21d60000").get("status") != b"okay\x00":
        raise SystemExit("sdmmc0 was modified")
    if b"rockchip,pmugrf\x00" not in bytes(dtb):
        raise SystemExit("clobbered rockchip,pmugrf string")

    if len(dtb) != orig_len:
        raise SystemExit(f"DTB size changed {orig_len} -> {len(dtb)}")
    return log


def pack_prop(nameoff: int, value: bytes) -> bytes:
    pad = (4 - (len(value) % 4)) % 4
    return struct.pack(">III", FDT_PROP, len(value), nameoff) + value + bytes(pad)


def expand_dr_mode_peripheral(dtb: bytearray, offs: dict, a: str) -> None:
    """Grow dr_mode to 'peripheral' by consuming the next empty snps quirk.

    phys, phy-names, and phy_type are copied verbatim so the USB3 combphy
    still binds. The 12-byte empty quirk becomes 8 bytes of extra dr_mode
    value plus one FDT_NOP. Nothing after that quirk moves.
    """
    keys = ("dr_mode", "phys", "phy-names", "phy_type", "snps,dis_enblslpm_quirk")
    props = []
    for name in keys:
        voff, plen = offs[(a, name)]
        hdr = voff - 12
        end = (voff + plen + 3) & ~3
        tag, oldlen, nameoff = struct.unpack_from(">III", dtb, hdr)
        if tag != 3 or oldlen != plen:
            raise SystemExit(f"{name} header mismatch")
        props.append((name, hdr, end, plen, nameoff, bytes(dtb[voff : voff + plen])))
    for (_, _h, end, *rest), (name, hdr, *rest2) in zip(props, props[1:]):
        if end != hdr:
            raise SystemExit(f"{name} not adjacent to previous property")
    if props[-1][3] != 0:
        raise SystemExit("first snps quirk is not empty")

    peri = b"peripheral" + bytes([0])
    blob = b"".join(
        [
            pack_prop(props[0][4], peri),
            pack_prop(props[1][4], props[1][5]),
            pack_prop(props[2][4], props[2][5]),
            pack_prop(props[3][4], props[3][5]),
        ]
    )
    start = props[0][1]
    stop = props[-1][2]
    leftover = stop - start - len(blob)
    if leftover < 0 or leftover % 4:
        raise SystemExit(f"dr_mode rewrite leftover {leftover}")
    blob += struct.pack(">I", FDT_NOP) * (leftover // 4)
    if len(blob) != stop - start:
        raise SystemExit("dr_mode rewrite size mismatch")
    dtb[start:stop] = blob


def nop_prop(dtb: bytearray, voff: int, plen: int) -> None:
    hdr = voff - 12
    end = (voff + plen + 3) & ~3
    if (end - hdr) % 4:
        raise SystemExit("unaligned nop_prop")
    for o in range(hdr, end, 4):
        struct.pack_into(">I", dtb, o, FDT_NOP)


def nop_subtree(dtb: bytearray, fdt: Fdt, path: str) -> None:
    """Replace a node and its children with FDT_NOP tokens. Size unchanged."""
    parts = [p for p in path.split("/") if p]
    stack: list[str] = []
    start_at: int | None = None
    target_depth: int | None = None
    pos = fdt.off_dt_struct
    limit = fdt.off_dt_struct + fdt.size_dt_struct
    while pos < limit:
        tok_off = pos
        (token,) = struct.unpack_from(">I", dtb, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            end = dtb.find(0, pos)
            name = bytes(dtb[pos:end]).decode("ascii", "replace")
            pos = (end + 1 + 3) & ~3
            stack.append(name)
            if [n for n in stack if n] == parts:
                start_at = tok_off
                target_depth = len(stack)
        elif token == FDT_END_NODE:
            if start_at is not None and len(stack) == target_depth:
                if (pos - start_at) % 4:
                    raise SystemExit(f"{path}: unaligned nop span")
                for o in range(start_at, pos, 4):
                    struct.pack_into(">I", dtb, o, FDT_NOP)
                return
            if stack:
                stack.pop()
        elif token == FDT_PROP:
            plen, _nameoff = struct.unpack_from(">II", dtb, pos)
            pos += 8
            pos = (pos + plen + 3) & ~3
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            raise SystemExit(f"bad FDT token {token:#x} at {tok_off:#x}")
    raise SystemExit(f"node not found: {path}")


def update_fit_hash(data: bytearray, path: str, blob: bytes, old_hash: bytes) -> None:
    fit = Fdt(bytes(data[:2048] if len(data) > 2048 else data))
    # walk only the FIT header FDT
    fit = Fdt(data[: struct.unpack(">I", bytes(data[4:8]))[0]])
    offs = prop_offsets(fit)
    hoff, hlen = offs[(path, "value")]
    if hlen != 32 or bytes(data[hoff : hoff + 32]) != old_hash:
        raise SystemExit(f"{path}: hash slot mismatch")
    new_hash = hashlib.sha256(blob).digest()
    data[hoff : hoff + 32] = new_hash
    print(f"  {path} {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else STOCK
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    data = bytearray(src.read_bytes())

    fit = Fdt(bytes(data))
    root = build(fit)
    img = find(root, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    fdt_old = bytes(data[pos : pos + size])
    fdt_hash = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            fdt_hash = c.get("value")
    if hashlib.sha256(fdt_old).digest() != fdt_hash:
        raise SystemExit("stock fdt hash mismatch, refusing")

    dtb = bytearray(fdt_old)
    print("FIT fdt edits:")
    for line in patch_one_dtb(dtb):
        print(" ", line)
    data[pos : pos + size] = dtb
    update_fit_hash(data, "/images/fdt/hash", bytes(dtb), fdt_hash)

    res = find(root, "/images/resource")
    rpos = struct.unpack(">I", res.get("data-position"))[0]
    rsize = struct.unpack(">I", res.get("data-size"))[0]
    rblob = bytearray(data[rpos : rpos + rsize])
    start, f_size, _slot, entry_off, hash_size = resource_dtb_slot(bytes(rblob))
    if f_size != size:
        raise SystemExit(f"resource dtb size {f_size} != fit fdt {size}")
    if bytes(rblob[start : start + f_size]) != fdt_old:
        raise SystemExit("resource rk-kernel.dtb is not a copy of the FIT fdt")

    print("resource rk-kernel.dtb edits:")
    rdtb = bytearray(rblob[start : start + f_size])
    for line in patch_one_dtb(rdtb):
        print(" ", line)
    rblob[start : start + f_size] = rdtb
    stored = bytes(rblob[entry_off + 224 : entry_off + 224 + hash_size])
    calc = hashlib.sha1(fdt_old).digest() if hash_size == 20 else hashlib.sha256(fdt_old).digest()
    if calc != stored:
        raise SystemExit("resource entry hash mismatch before patch")
    new_entry = hashlib.sha1(bytes(rdtb)).digest() if hash_size == 20 else hashlib.sha256(bytes(rdtb)).digest()
    rblob[entry_off + 224 : entry_off + 224 + hash_size] = new_entry
    print(f"  entry hash {stored.hex()[:16]}... -> {new_entry.hex()[:16]}...")
    data[rpos : rpos + rsize] = rblob

    res_hash = None
    for c in res.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            res_hash = c.get("value")
    update_fit_hash(data, "/images/resource/hash", bytes(data[rpos : rpos + rsize]), res_hash)

    n = sum(a != b for a, b in zip(src.read_bytes(), bytes(data)))
    n += abs(len(data) - src.stat().st_size)
    print(f"\nbytes different from stock: {n} (includes hashes)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(data))
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
