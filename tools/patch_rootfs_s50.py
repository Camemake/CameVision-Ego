#!/usr/bin/env python3
"""Write the live S50usbdevice into the Aura rootfs image."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

IMG = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\rootfs_adbwait.img")
S50 = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\S50usbdevice")
TARGET = "/etc/init.d/S50usbdevice"


def main() -> int:
    new = S50.read_bytes().replace(b"\r\n", b"\n")
    if b"Efference" in new or b"efference" in new or b"M1" in new:
        raise SystemExit("refusing S50 with old product names")
    if b"CameMake" not in new:
        raise SystemExit("CameMake missing")
    img = bytearray(IMG.read_bytes())
    sb = parse_sb(bytes(img))
    patched = patch_file(img, sb, TARGET, lambda _d: new)
    IMG.write_bytes(bytes(img))
    verify_file(IMG, TARGET, patched)
    print(f"wrote S50 into {IMG} ({len(patched)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
