#!/usr/bin/env python3
"""Aura non-RT kernel + CameVision camera/WiFi DTB (no FDT reserialize).

Base: Luckfox Aura boot.img (Linux 6.1.141, matches OEM SWT6621 modules)
Inject: FIT fdt + resource rk-kernel.dtb from camevision_boot.img
        (SC233HGS, USB peripheral HS, wireless-wlan rk96x)

CameVision FDT is smaller than Aura's slots, so it is copied in-place and
data-size / resource entry size are updated. FIT sha256 hashes recomputed.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_usb import prop_offsets  # noqa: E402

AURA = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)
CAME = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\restore\known-good-20260819-camera-adb\camevision_boot.img"
)
DST = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\build\camevision_boot_aura_kernel_camdt.img"
)


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


def set_u32_prop(blob: bytearray, offsets: dict, path_key: tuple[str, str], value: int) -> None:
    off, length = offsets[path_key]
    if length != 4:
        raise SystemExit(f"{path_key} length {length}")
    struct.pack_into(">I", blob, off, value)


def main() -> int:
    aura = bytearray(AURA.read_bytes())
    came = CAME.read_bytes()
    print("verify aura source")
    verify_hashes(bytes(aura), "aura")
    print("verify came source")
    verify_hashes(came, "came")

    a_imgs, _ = fit_images(bytes(aura))
    c_imgs, _ = fit_images(came)

    a_fpos, a_fsize, _, _ = a_imgs["/images/fdt"]
    c_fpos, c_fsize, _, _ = c_imgs["/images/fdt"]
    a_rpos, a_rsize, _, _ = a_imgs["/images/resource"]
    c_rpos, c_rsize, _, _ = c_imgs["/images/resource"]

    came_fdt = came[c_fpos : c_fpos + c_fsize]
    if b"smartsens,sc233hgs" not in came_fdt:
        raise SystemExit("came fdt missing sc233hgs")
    if b"rk96x" not in came_fdt:
        raise SystemExit("came fdt missing wifi rk96x")
    if c_fsize > a_fsize:
        raise SystemExit(f"came fdt {c_fsize} > aura slot {a_fsize}")

    print(f"inject fdt {c_fsize} into aura slot {a_fsize} @ {a_fpos}")
    aura[a_fpos : a_fpos + c_fsize] = came_fdt
    aura[a_fpos + c_fsize : a_fpos + a_fsize] = b"\x00" * (a_fsize - c_fsize)

    # Update FIT data-size for fdt to real size
    offsets = prop_offsets(Fdt(bytes(aura)))
    set_u32_prop(aura, offsets, ("/images/fdt", "data-size"), c_fsize)

    # Resource: replace rk-kernel.dtb
    res = bytearray(aura[a_rpos : a_rpos + a_rsize])
    if res[:4] != b"RSCE":
        raise SystemExit("aura resource magic")
    hdr_blocks, entry_blocks = struct.unpack_from("<BB", res, 8)
    # extract came rk-kernel.dtb
    cres = came[c_rpos : c_rpos + c_rsize]
    chdr, centry = struct.unpack_from("<BB", cres, 8)
    came_dtb = None
    i = 0
    while True:
        eoff = chdr * 512 + i * centry * 512
        if cres[eoff : eoff + 4] != b"ENTR":
            break
        name = cres[eoff + 4 : eoff + 224].split(b"\x00")[0]
        hash_size, f_offset, f_size = struct.unpack_from("<III", cres, eoff + 256)
        if name == b"rk-kernel.dtb":
            came_dtb = cres[f_offset * 512 : f_offset * 512 + f_size]
            break
        i += 1
    if not came_dtb or b"smartsens,sc233hgs" not in came_dtb:
        raise SystemExit("came resource dtb missing")

    i = 0
    while True:
        eoff = hdr_blocks * 512 + i * entry_blocks * 512
        if res[eoff : eoff + 4] != b"ENTR":
            break
        name = res[eoff + 4 : eoff + 224].split(b"\x00")[0]
        hash_size, f_offset, f_size = struct.unpack_from("<III", res, eoff + 256)
        if name == b"rk-kernel.dtb":
            start = f_offset * 512
            if len(came_dtb) > f_size:
                raise SystemExit(f"came dtb {len(came_dtb)} > aura entry {f_size}")
            print(f"inject resource rk-kernel.dtb {len(came_dtb)} into slot {f_size}")
            res[start : start + len(came_dtb)] = came_dtb
            res[start + len(came_dtb) : start + f_size] = b"\x00" * (f_size - len(came_dtb))
            struct.pack_into("<I", res, eoff + 256 + 8, len(came_dtb))  # f_size
            if hash_size == 20:
                h = hashlib.sha1(came_dtb).digest()
            elif hash_size == 32:
                h = hashlib.sha256(came_dtb).digest()
            else:
                raise SystemExit(f"entry hash size {hash_size}")
            res[eoff + 224 : eoff + 224 + hash_size] = h
            print("  resource entry hash updated")
            break
        i += 1
    else:
        raise SystemExit("rk-kernel.dtb entry not found in aura resource")

    aura[a_rpos : a_rpos + a_rsize] = res

    # Recompute FIT image hashes (fdt uses new data-size; hash over that size)
    offsets = prop_offsets(Fdt(bytes(aura)))
    # refresh sizes from blob after our data-size edit
    a_imgs2, _ = fit_images(bytes(aura))
    fpos, fsize, _, _ = a_imgs2["/images/fdt"]
    rpos, rsize, _, _ = a_imgs2["/images/resource"]
    if fsize != c_fsize:
        raise SystemExit(f"fdt data-size not applied: {fsize}")

    new_fdt_hash = hashlib.sha256(bytes(aura[fpos : fpos + fsize])).digest()
    hoff, hlen = offsets[("/images/fdt/hash", "value")]
    if hlen != 32:
        raise SystemExit("fdt hash length")
    aura[hoff : hoff + 32] = new_fdt_hash

    new_res_hash = hashlib.sha256(bytes(aura[rpos : rpos + rsize])).digest()
    hoff, hlen = offsets[("/images/resource/hash", "value")]
    aura[hoff : hoff + 32] = new_res_hash

    verify_hashes(bytes(aura), "merged")

    # sanity
    fdt = bytes(aura[fpos : fpos + fsize])
    for must in (b"smartsens,sc233hgs", b"rk96x", b"peripheral"):
        if must not in fdt:
            raise SystemExit(f"missing {must!r} in merged fdt")
    kern_pos, kern_size, _, _ = a_imgs2["/images/kernel"]
    kern = bytes(aura[kern_pos : kern_pos + kern_size])
    if b"6.1.141-rt52" in kern:
        raise SystemExit("rt52 leaked into aura kernel slot")
    if b"Linux version 6.1.141" not in kern and b"6.1.141" not in kern:
        print("WARN: could not confirm 6.1.141 string in compressed kernel")

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_bytes(bytes(aura))
    print(f"wrote {DST} ({len(aura)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
