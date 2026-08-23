#!/usr/bin/env python3
"""Disable Aura out-of-tree .ko loads.

Those modules are built for the Aura kernel. insmod into the M1 kernel oopses,
and this board's cmdline is panic=10 oops=panic — green LED then reboot.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\oem.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\oem_noko.img")

STUB = b"""#!/bin/sh
# CameVision: do not insmod Aura .ko into the M1 kernel
exit 0
"""


def transform(_data: bytes) -> bytes:
    return STUB


def main() -> int:
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    DST.parent.mkdir(parents=True, exist_ok=True)
    last = b""
    for target in ("/usr/ko/insmod_ko.sh", "/usr/ko/insmod_wifi.sh"):
        last = patch_file(img, sb, target, transform)
        DST.write_bytes(bytes(img))
        verify_file(DST, target, last)
    print(f"wrote {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
