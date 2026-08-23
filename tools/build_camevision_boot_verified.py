#!/usr/bin/env python3
"""Build a boot image that is the M1 FIT with one in-place bootargs edit.

Does not reserialize the DTB. USB, LED, SC233HGS, and FIT structure stay as
read from the working M1. Only the root device is pointed at this board's
existing ext4 rootfs (p7), then FIT/resource sha256 are recomputed.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import prop_offsets  # noqa: E402

SRC = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\m1-donor\boot_a.img")
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\camevision_boot.img")
BOOT_PART = 0x5800 * 512

# same length replacements inside the existing bootargs property
# pstore_blk must NOT point at the ext4 root (p7). That logs panics onto the
# mounted rootfs, corrupts it, and the red LED is wired as the panic trigger.
_PSTORE = b"pstore_blk.blkdev=/dev/mmcblk0p13"
EDITS = [
    (b"root=/dev/mmcblk0p9", b"root=/dev/mmcblk0p7"),
    (b"rootfstype=erofs", b"rootfstype=ext4 "),
    (_PSTORE, b" " * len(_PSTORE)),
]


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


def patch_bytes(blob: bytearray, what: str) -> None:
    for old, new in EDITS:
        if len(old) != len(new):
            raise SystemExit(f"length mismatch {old!r}")
        n = blob.count(old)
        if n < 1:
            raise SystemExit(f"{what}: {old!r} not found")
        blob[:] = blob.replace(old, new)
        print(f"  {what}: {old.decode()} -> {new.decode()} ({n} hits)")


def main() -> int:
    raw = SRC.read_bytes()
    print("verify donor FIT")
    verify_hashes(raw, "donor")
    used = 6695424 + 1473024
    if not all(b == 0 for b in raw[used:]):
        raise SystemExit("donor padding is not zeros, refuse to trim")
    if used >= BOOT_PART:
        raise SystemExit("FIT does not fit 11MiB boot partition")

    data = bytearray(raw)
    images, root = fit_images(bytes(data))
    fpos, fsize, _, _ = images["/images/fdt"]
    rpos, rsize, _, _ = images["/images/resource"]

    fdt = bytearray(data[fpos : fpos + fsize])
    patch_bytes(fdt, "fit-fdt")
    if b"mmcblk0p9" in fdt or b"rootfstype=erofs" in fdt:
        raise SystemExit("p9/erofs still in fdt")
    if b"smartsens,sc233hgs" not in fdt or b"peripheral" not in fdt:
        raise SystemExit("camera/USB strings missing after patch")
    if b"gpio-leds" not in fdt:
        raise SystemExit("gpio-leds missing")
    data[fpos : fpos + fsize] = fdt

    res = bytearray(data[rpos : rpos + rsize])
    patch_bytes(res, "resource")
    data[rpos : rpos + rsize] = res

    # recompute FIT sha256 only (do not touch RSA signature node)
    offsets = prop_offsets(Fdt(bytes(data)))
    new_fdt_hash = hashlib.sha256(bytes(data[fpos : fpos + fsize])).digest()
    hoff, hlen = offsets[("/images/fdt/hash", "value")]
    if hlen != 32:
        raise SystemExit("fdt hash length")
    data[hoff : hoff + 32] = new_fdt_hash

    new_res_hash = hashlib.sha256(bytes(data[rpos : rpos + rsize])).digest()
    hoff, hlen = offsets[("/images/resource/hash", "value")]
    data[hoff : hoff + 32] = new_res_hash

    # resource entry sha1 over rk-kernel.dtb
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
            # FIT resource hash must include this entry-hash change
            new_res_hash = hashlib.sha256(bytes(data[rpos : rpos + rsize])).digest()
            hoff, _ = offsets[("/images/resource/hash", "value")]
            data[hoff : hoff + 32] = new_res_hash
        i += 1

    verify_hashes(bytes(data), "patched")
    out = bytes(data[:BOOT_PART])
    DST.write_bytes(out)
    print(f"wrote {DST} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
