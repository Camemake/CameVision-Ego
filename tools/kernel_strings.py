#!/usr/bin/env python3
"""Decompress the lz4 kernel out of boot.img and search it for feature markers.

Used to confirm which gadget functions the shipped kernel actually supports
before relying on them.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402

BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\boot.img"
)
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt\kernel.bin")

MARKERS = [
    # UVC gadget (drivers/usb/gadget/function/f_uvc.c + uvc_configfs.c)
    b"streaming_maxpacket",
    b"uvc_function_",
    b"uvcvideo",
    b"webcam",
    # configfs gadget core
    b"usb_gadget",
    b"libcomposite",
    b"functionfs",
    b"mass_storage",
    b"rndis",
    b"acm_ms",
    # controller
    b"dwc3",
    b"snps,dwc3",
    # useful extras
    b"g_serial",
    b"uac1",
    b"uac2",
]


def find_kernel(data: bytes) -> tuple[int, int, str]:
    fdt = Fdt(data)
    root = build(fdt)
    for n in root.walk():
        if n.path() == "/images/kernel":
            pos = struct.unpack(">I", n.get("data-position"))[0]
            size = struct.unpack(">I", n.get("data-size"))[0]
            comp = (printable_strings(n.get("compression") or b"") or ["none"])[0]
            return pos, size, comp
    raise SystemExit("no /images/kernel")


def lz4_decompress(blob: bytes) -> bytes:
    import lz4.block
    import lz4.frame

    magic = blob[:4]
    if magic == b"\x04\x22\x4d\x18":
        return lz4.frame.decompress(blob)
    if magic == b"\x02\x21\x4c\x18":
        # legacy format: repeated [u32 compressed_size][block], 8 MiB raw blocks
        out = []
        off = 4
        while off + 4 <= len(blob):
            (clen,) = struct.unpack_from("<I", blob, off)
            off += 4
            if clen == 0 or clen > len(blob) - off:
                break
            chunk = blob[off : off + clen]
            off += clen
            out.append(lz4.block.decompress(chunk, uncompressed_size=8 * 1024 * 1024))
        return b"".join(out)
    raise SystemExit(f"unknown lz4 magic {magic.hex()}")


def main() -> int:
    data = BOOT.read_bytes()
    pos, size, comp = find_kernel(data)
    print(f"kernel at {pos:#x} size {size} compression {comp}")
    blob = data[pos : pos + size]
    print(f"first bytes {blob[:8].hex()}")

    if comp == "lz4":
        raw = lz4_decompress(blob)
    else:
        raw = blob
    print(f"decompressed {len(raw)} bytes")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(raw)

    print("\nmarker search:")
    for m in MARKERS:
        n = raw.count(m)
        print(f"  {m.decode():22s} {'present' if n else 'ABSENT ':8s} count={n}")

    # show the uvc configfs attribute neighbourhood for confidence
    i = raw.find(b"streaming_maxpacket")
    if i >= 0:
        ctx = raw[max(0, i - 200) : i + 200]
        printable = "".join(
            chr(c) if 32 <= c < 127 else "." for c in ctx
        )
        print(f"\ncontext around streaming_maxpacket at {i:#x}:\n  {printable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
