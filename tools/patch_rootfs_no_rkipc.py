#!/usr/bin/env python3
"""Stop Aura rkipc/RkLunch so it cannot oops the M1 kernel before USB starts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

SRC = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\rootfs_adbwait.img")
DST = SRC
TARGET = "/etc/init.d/S21appinit"
STUB = b"""#!/bin/sh
# CameVision: skip Aura rkipc/RkLunch (Aura ISP stack oopses the M1 kernel)
exit 0
"""


def main() -> int:
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    patched = patch_file(img, sb, TARGET, lambda _d: STUB)
    DST.write_bytes(bytes(img))
    verify_file(DST, TARGET, patched)
    print(f"wrote {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
