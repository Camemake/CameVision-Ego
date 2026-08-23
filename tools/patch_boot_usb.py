#!/usr/bin/env python3
"""Turn the RV1126B USB3 port into an always-on USB device in the shipped boot.img.

The stock device tree has the OTG port of the USB2 PHY disabled and hands role
detection to a Type-C PD controller that this board does not have, so
/sys/class/udc stays empty and no gadget can ever bind. This rewrites the FDT
that is embedded in the boot.img FIT:

  /usb2-phy@21400000/otg-port   status  disabled -> okay, drop vbus-supply
  /usb@21500000 (dwc3)          dr_mode otg -> peripheral, drop usb-role-switch,
                                extcon and the Type-C role-switch port
  /i2c@21120000/husb311@4e      status  okay -> disabled (chip not fitted)

The new FDT is padded back to the original data-size so no other FIT sub-image
moves, then the sha256 in the FIT header is recomputed.

Usage:
    patch_boot_usb.py <boot.img> <out.img>
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, Node, build, printable_strings  # noqa: E402

FDT_BEGIN_NODE = 0x1
FDT_END_NODE = 0x2
FDT_PROP = 0x3
FDT_END = 0x9


# ----------------------------------------------------------------- tree edit --
def find(root: Node, path: str) -> Node:
    for n in root.walk():
        if n.path() == path:
            return n
    raise SystemExit(f"node not found: {path}")


def set_prop(root: Node, path: str, name: str, value: bytes) -> None:
    node = find(root, path)
    for i, (k, v) in enumerate(node.props):
        if k == name:
            old = printable_strings(v)
            node.props[i] = (name, value)
            print(f"  {path}: {name} {old} -> {printable_strings(value)}")
            return
    node.props.append((name, value))
    print(f"  {path}: {name} added = {printable_strings(value)}")


def del_prop(root: Node, path: str, name: str) -> None:
    node = find(root, path)
    before = len(node.props)
    node.props = [(k, v) for k, v in node.props if k != name]
    print(f"  {path}: {name} {'removed' if len(node.props) < before else 'ABSENT'}")


def del_node(root: Node, path: str) -> None:
    parent_path, _, child = path.rpartition("/")
    parent = find(root, parent_path or "/")
    before = len(parent.children)
    parent.children = [c for c in parent.children if c.name != child]
    print(f"  {path}: node {'removed' if len(parent.children) < before else 'ABSENT'}")


# ---------------------------------------------------------------- serialize ---
def serialize(root: Node, mem_rsvmap: bytes, boot_cpuid: int) -> bytes:
    strings = bytearray()
    offsets: dict[str, int] = {}

    def string_off(name: str) -> int:
        """Offset of name in the strings block, reusing suffixes like dtc does.

        Every string is NUL terminated, so any occurrence of "name\\0" inside the
        block is a valid offset for that name. Without this the block grows and
        the blob no longer fits its slot in the boot image.
        """
        if name in offsets:
            return offsets[name]
        needle = name.encode("ascii") + b"\x00"
        found = bytes(strings).find(needle)
        if found < 0:
            found = len(strings)
            strings.extend(needle)
        offsets[name] = found
        return found

    body = bytearray()

    def pad4(b: bytearray) -> None:
        while len(b) % 4:
            b.append(0)

    def emit(node: Node) -> None:
        body.extend(struct.pack(">I", FDT_BEGIN_NODE))
        body.extend(node.name.encode("ascii") + b"\x00")
        pad4(body)
        for k, v in node.props:
            body.extend(struct.pack(">III", FDT_PROP, len(v), string_off(k)))
            body.extend(v)
            pad4(body)
        for c in node.children:
            emit(c)
        body.extend(struct.pack(">I", FDT_END_NODE))

    emit(root)
    body.extend(struct.pack(">I", FDT_END))

    off_mem_rsvmap = 40
    off_dt_struct = off_mem_rsvmap + len(mem_rsvmap)
    while off_dt_struct % 8:
        off_dt_struct += 1
    off_dt_strings = off_dt_struct + len(body)
    total = off_dt_strings + len(strings)

    out = bytearray(total)
    struct.pack_into(
        ">10I",
        out,
        0,
        0xD00DFEED,
        total,
        off_dt_struct,
        off_dt_strings,
        off_mem_rsvmap,
        17,
        16,
        boot_cpuid,
        len(strings),
        len(body),
    )
    out[off_mem_rsvmap : off_mem_rsvmap + len(mem_rsvmap)] = mem_rsvmap
    out[off_dt_struct : off_dt_struct + len(body)] = body
    out[off_dt_strings : off_dt_strings + len(strings)] = strings
    return bytes(out)


def prop_offsets(fdt: Fdt) -> dict[tuple[str, str], tuple[int, int]]:
    """Map (node path, property name) -> (value offset in blob, length).

    Lets us patch a property value in place instead of searching for its bytes.
    """
    out: dict[tuple[str, str], tuple[int, int]] = {}
    pos = fdt.off_dt_struct
    limit = fdt.off_dt_struct + fdt.size_dt_struct
    stack: list[str] = []
    while pos < limit:
        (token,) = struct.unpack_from(">I", fdt.blob, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            end = fdt.blob.find(b"\x00", pos)
            stack.append(fdt.blob[pos:end].decode("ascii", "replace"))
            pos = (end + 1 + 3) & ~3
        elif token == FDT_END_NODE:
            stack.pop()
        elif token == FDT_PROP:
            plen, nameoff = struct.unpack_from(">II", fdt.blob, pos)
            pos += 8
            path = "/" + "/".join(p for p in stack[1:] if p)
            out[(path, fdt.string(nameoff))] = (pos, plen)
            pos = (pos + plen + 3) & ~3
        elif token == FDT_END:
            break
    return out


def resource_dtb_slot(blob: bytes) -> tuple[int, int, int, int, int]:
    """Locate rk-kernel.dtb inside a Rockchip resource image.

    Returns (data offset, current size, slot size, entry offset, stored hash size).
    struct resource_entry { tag[4]; name[220]; hash[32]; hash_size; f_offset; f_size; }
    """
    if blob[:4] != b"RSCE":
        raise SystemExit("resource image magic is not RSCE")
    hdr_blocks, entry_blocks = struct.unpack_from("<BB", blob, 8)
    entries = []
    i = 0
    while True:
        off = hdr_blocks * 512 + i * entry_blocks * 512
        if blob[off : off + 4] != b"ENTR":
            break
        name = blob[off + 4 : off + 224].split(b"\x00")[0].decode("ascii", "replace")
        hash_size, f_offset, f_size = struct.unpack_from("<III", blob, off + 256)
        entries.append((name, off, hash_size, f_offset, f_size))
        i += 1

    target = next((e for e in entries if e[0] == "rk-kernel.dtb"), None)
    if target is None:
        raise SystemExit("resource image has no rk-kernel.dtb")
    _, entry_off, hash_size, f_offset, f_size = target
    start = f_offset * 512
    # the slot runs to whichever entry starts next, else to the end of the image
    nxt = len(blob)
    for _, _, _, other_off, _ in entries:
        o = other_off * 512
        if start < o < nxt:
            nxt = o
    return start, f_size, nxt - start, entry_off, hash_size


def read_mem_rsvmap(fdt: Fdt) -> bytes:
    off = fdt.off_mem_rsvmap
    end = off
    while True:
        addr, size = struct.unpack_from(">QQ", fdt.blob, end)
        end += 16
        if addr == 0 and size == 0:
            break
    return fdt.blob[off:end]


def patch_resource_copy(
    data: bytearray, fit_root: Node, offsets: dict, new_dtb: bytes
) -> None:
    """Replace the rk-kernel.dtb copy that also lives in the resource image.

    U-Boot can take the kernel device tree from either the FIT fdt image or this
    copy, so both have to say the same thing. The per-entry hash and the FIT
    sha256 over the whole resource image are recomputed.
    """
    res = find(fit_root, "/images/resource")
    rpos = struct.unpack(">I", res.get("data-position"))[0]
    rsize = struct.unpack(">I", res.get("data-size"))[0]
    blob = bytes(data[rpos : rpos + rsize])

    start, cur_size, slot, entry_off, hash_size = resource_dtb_slot(blob)
    print(
        f"\nresource rk-kernel.dtb at {rpos + start:#x} size {cur_size}, slot {slot}"
    )
    if len(new_dtb) > slot:
        raise SystemExit(f"new fdt does not fit the resource slot ({slot})")

    stored = blob[entry_off + 224 : entry_off + 224 + hash_size]
    if hash_size == 20:
        calc = hashlib.sha1(blob[start : start + cur_size]).digest()
    elif hash_size == 32:
        calc = hashlib.sha256(blob[start : start + cur_size]).digest()
    else:
        raise SystemExit(f"unexpected entry hash size {hash_size}")
    if calc != stored:
        raise SystemExit(
            "resource entry hash does not match its data, refusing to patch\n"
            f"  stored {stored.hex()}\n  calc   {calc.hex()}"
        )
    print(f"  entry hash ({hash_size}-byte) verified")

    # write the new blob into the slot, zero the rest of it
    abs_start = rpos + start
    data[abs_start : abs_start + slot] = new_dtb + b"\x00" * (slot - len(new_dtb))

    if len(new_dtb) != cur_size:
        struct.pack_into("<I", data, rpos + entry_off + 264, len(new_dtb))
        print(f"  entry f_size {cur_size} -> {len(new_dtb)}")

    new_entry_hash = (
        hashlib.sha1(new_dtb).digest()
        if hash_size == 20
        else hashlib.sha256(new_dtb).digest()
    )
    data[rpos + entry_off + 224 : rpos + entry_off + 224 + hash_size] = new_entry_hash
    print(f"  entry hash updated: {stored.hex()[:16]}... -> {new_entry_hash.hex()[:16]}...")

    # and the FIT hash over the resource image as a whole
    res_hash = None
    for c in res.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            res_hash = c.get("value")
    if res_hash is None:
        raise SystemExit("no sha256 hash node for /images/resource")
    hoff, hlen = offsets[("/images/resource/hash", "value")]
    if hlen != 32 or bytes(data[hoff : hoff + 32]) != res_hash:
        raise SystemExit("resource hash offset does not hold the expected digest")
    new_res = hashlib.sha256(bytes(data[rpos : rpos + rsize])).digest()
    data[hoff : hoff + 32] = new_res
    print(f"  resource sha256 updated: {res_hash.hex()[:16]}... -> {new_res.hex()[:16]}...")


# --------------------------------------------------------------------- main ---
def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = bytearray(src.read_bytes())

    fit = Fdt(bytes(data))
    fit_root = build(fit)
    offsets = prop_offsets(fit)
    img = find(fit_root, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]

    # how far the fdt may grow before it would collide with the next sub-image
    next_pos = len(data)
    for n in fit_root.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    slot = next_pos - pos
    print(f"fdt sub-image at {pos:#x} size {size}, slot to next image {slot}")

    old_hash = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            old_hash = c.get("value")
    if old_hash is None:
        raise SystemExit("no sha256 hash node for /images/fdt")
    if hashlib.sha256(bytes(data[pos : pos + size])).digest() != old_hash:
        raise SystemExit("stored fdt hash does not match, refusing to patch")
    print("stored fdt hash verified")

    dtb = Fdt(bytes(data[pos : pos + size]))
    root = build(dtb)
    rsv = read_mem_rsvmap(dtb)

    print("\napplying edits:")
    set_prop(root, "/usb2-phy@21400000/otg-port", "status", b"okay\x00")
    del_prop(root, "/usb2-phy@21400000/otg-port", "vbus-supply")
    set_prop(root, "/usb@21500000", "dr_mode", b"peripheral\x00")
    del_prop(root, "/usb@21500000", "usb-role-switch")
    del_prop(root, "/usb@21500000", "extcon")
    del_node(root, "/usb@21500000/port")
    set_prop(root, "/i2c@21120000/husb311@4e", "status", b"disabled\x00")

    new_dtb = serialize(root, rsv, dtb.boot_cpuid_phys)
    print(f"\nnew fdt {len(new_dtb)} bytes (original {size})")
    if len(new_dtb) > slot:
        raise SystemExit(f"new fdt is {len(new_dtb) - slot} bytes too big for the slot")

    # The sub-images are 512-byte aligned, which leaves spare bytes after the
    # fdt. Grow into those and zero the rest of the slot so the kernel and
    # resource images stay exactly where they are.
    data[pos:next_pos] = new_dtb + b"\x00" * (slot - len(new_dtb))

    if len(new_dtb) != size:
        off, plen = offsets[("/images/fdt", "data-size")]
        if plen != 4:
            raise SystemExit("data-size is not a single cell")
        struct.pack_into(">I", data, off, len(new_dtb))
        print(f"data-size at {off:#x} updated: {size} -> {len(new_dtb)}")

    new_hash = hashlib.sha256(bytes(data[pos : pos + len(new_dtb)])).digest()
    hoff, hlen = offsets[("/images/fdt/hash", "value")]
    if hlen != 32 or bytes(data[hoff : hoff + 32]) != old_hash:
        raise SystemExit("hash value offset does not hold the expected digest")
    data[hoff : hoff + 32] = new_hash
    print(f"hash at {hoff:#x} updated: {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")

    patch_resource_copy(data, fit_root, offsets, new_dtb)

    dst.write_bytes(bytes(data))
    print(f"\nwrote {dst} ({len(data)} bytes, unchanged size)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
