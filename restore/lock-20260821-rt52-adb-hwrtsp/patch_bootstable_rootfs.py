#!/usr/bin/env python3
"""CameVision rootfs for a stable boot: keep ADB-first S20, kill the eMMC log poke."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\stefa\Desktop\CameVision Single\tools")
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = HERE / "rootfs_adbwait.img"
DST = HERE / "rootfs_bootstable.img"
S21 = (HERE / "overlay" / "S21appinit").read_bytes().replace(b"\r\n", b"\n")


def main() -> int:
    if b"mmcblk0" in S21 or b"seek=33600" in S21:
        raise SystemExit("refusing S21 that still writes eMMC")
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    patched = patch_file(img, sb, "/etc/init.d/S21appinit", lambda _d: S21)
    DST.write_bytes(bytes(img))
    verify_file(DST, "/etc/init.d/S21appinit", patched)
    print(f"wrote {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
