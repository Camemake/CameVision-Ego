#!/usr/bin/env python3
"""In-place DTB patch: dwc3 maximum-speed high-speed -> super-speed.

Does not reserialize the FDT. "high-speed\\0" is 11 bytes, 4-aligned with one
pad byte; "super-speed\\0" is 12 bytes and fills that slot. FIT fdt + resource
sha256 (and the resource rk-kernel.dtb entry hash) are recomputed.

USB 3.2 Gen 1 = USB 3.0 SuperSpeed 5 Gbps. This SoC has no 10 Gbps PHY.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import prop_offsets  # noqa: E402

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\restore\known-good-20260819-camera-adb\camevision_boot.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\camevision_boot_ss.img")

OLD = b"high-speed\x00"
NEW = b"super-speed\x00"
FDT_PROP = 0x3


def fit_images(data: bytes):
    root = build(Fdt(data))
    out = {}
    for n in root.walk():
        if n.path().startswith("/images/") and n.path().count("/") == 2:
            pos = struct.unpack(">I", n.get("data-position"))[0]
            size = struct.unpack(">I", n.get("data-size"))[0]
            digest = None
            for c in n.children:
                if printable_strings(c.get("algo") or b"") == ["sha256"]:
                    digest = c.get("value")
            out[n.path()] = (pos, size, digest, n)
    return out, root


def verify_hashes(data: bytes, label: str) -> None:
    images, _ = fit_images(data)
    for path, (pos, size, digest, _) in images.items():
        calc = hashlib.sha256(data[pos : pos + size]).digest()
        if calc != digest:
            raise SystemExit(f"{label} {path} HASH FAIL")
        print(f"  {label} {path} sha256 ok size={size}")


def patch_maximum_speed(blob: bytearray, what: str) -> None:
    hits = []
    start = 0
    while True:
        i = blob.find(OLD, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if not hits:
        raise SystemExit(f"{what}: {OLD!r} not found")
    patched = 0
    for i in hits:
        if i < 12:
            continue
        tag, length = struct.unpack_from(">II", blob, i - 12)
        if tag != FDT_PROP or length != len(OLD):
            print(f"  {what}: skip offset {i} tag={tag:#x} len={length}")
            continue
        struct.pack_into(">I", blob, i - 8, len(NEW))
        blob[i : i + len(NEW)] = NEW
        patched += 1
        print(f"  {what}: maximum-speed high-speed -> super-speed @ {i}")
    if patched < 1:
        raise SystemExit(f"{what}: no FDT_PROP high-speed value patched")
    if OLD in blob:
        raise SystemExit(f"{what}: high-speed still present")
    if b"super-speed\x00" not in blob:
        raise SystemExit(f"{what}: super-speed missing after patch")


def main() -> int:
    raw = SRC.read_bytes()
    print("verify source FIT")
    verify_hashes(raw, "src")

    data = bytearray(raw)
    images, _ = fit_images(bytes(data))
    fpos, fsize, _, _ = images["/images/fdt"]
    rpos, rsize, _, _ = images["/images/resource"]

    fdt = bytearray(data[fpos : fpos + fsize])
    patch_maximum_speed(fdt, "fit-fdt")
    data[fpos : fpos + fsize] = fdt

    res = bytearray(data[rpos : rpos + rsize])
    patch_maximum_speed(res, "resource")
    data[rpos : rpos + rsize] = res

    offsets = prop_offsets(Fdt(bytes(data)))
    new_fdt_hash = hashlib.sha256(bytes(data[fpos : fpos + fsize])).digest()
    hoff, hlen = offsets[("/images/fdt/hash", "value")]
    if hlen != 32:
        raise SystemExit("fdt hash length")
    data[hoff : hoff + 32] = new_fdt_hash

    blob = bytes(data[rpos : rpos + rsize])
    if blob[:4] != b"RSCE":
        raise SystemExit("resource magic")
    hdr_blocks, entry_blocks = struct.unpack_from("<BB", blob, 8)
    i = 0
    while True:
        eoff = hdr_blocks * 512 + i * entry_blocks * 512
        if blob[eoff : eoff + 4] != b"ENTR":
            break
        name = blob[eoff + 4 : eoff + 224].split(b"\x00")[0]
        hash_size, f_offset, f_size = struct.unpack_from("<III", blob, eoff + 256)
        start = f_offset * 512
        if name == b"rk-kernel.dtb":
            dtb = data[rpos + start : rpos + start + f_size]
            if hash_size == 20:
                h = hashlib.sha1(dtb).digest()
            elif hash_size == 32:
                h = hashlib.sha256(dtb).digest()
            else:
                raise SystemExit(f"entry hash size {hash_size}")
            data[rpos + eoff + 224 : rpos + eoff + 224 + hash_size] = h
            print(f"  resource entry {name.decode()} hash updated")
        i += 1

    new_res_hash = hashlib.sha256(bytes(data[rpos : rpos + rsize])).digest()
    hoff, _ = offsets[("/images/resource/hash", "value")]
    data[hoff : hoff + 32] = new_res_hash

    verify_hashes(bytes(data), "patched")
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_bytes(bytes(data))
    print(f"wrote {DST} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
