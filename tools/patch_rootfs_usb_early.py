#!/usr/bin/env python3
"""Start the USB gadget before S20 mounts/resize can block init.

S20linkmount resize2fs/e2fsck on a huge/corrupt partition would delay S50
forever, so the host sees a green LED and no device.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

SRC = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\rootfs_adbwait.img")
DST = SRC

S20_PREFIX = b"""#!/bin/sh
# CameVision: bind ADB gadget before resize2fs/e2fsck can block
/etc/init.d/S50usbdevice start
"""

S21_LOG = b"""#!/bin/sh
{
echo CVLOG
cat /proc/cmdline
echo UDC:
ls /sys/class/udc 2>/dev/null
echo UDCFILE:
cat /sys/kernel/config/usb_gadget/rockchip/UDC 2>/dev/null
dmesg | grep -iE 'usb|dwc|udc|gadget' | tail -80
} > /tmp/cv.log
dd if=/tmp/cv.log of=/dev/mmcblk0 bs=512 seek=33600 conv=fsync,notrunc
exit 0
"""


def patch_s20(data: bytes) -> bytes:
    if data.startswith(S20_PREFIX):
        return data
    if not data.startswith(b"#!/bin/sh\n"):
        raise SystemExit("S20 missing shebang")
    out = S20_PREFIX + data[len(b"#!/bin/sh\n") :]
    if b"/etc/init.d/S50usbdevice start" not in out:
        raise SystemExit("S20 usb inject failed")
    return out


def patch_s40(data: bytes) -> bytes:
    old = b"\t/sbin/ifup -a\n"
    new = b"\t/sbin/ifup -a &\n"
    if data.count(old) != 1:
        if b"/sbin/ifup -a &\n" in data:
            return data
        raise SystemExit(f"S40 ifup matches {data.count(old)}")
    return data.replace(old, new)


def main() -> int:
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    p20 = patch_file(img, sb, "/etc/init.d/S20linkmount", patch_s20)
    p21 = patch_file(img, sb, "/etc/init.d/S21appinit", lambda _d: S21_LOG)
    p40 = patch_file(img, sb, "/etc/init.d/S40network", patch_s40)
    DST.write_bytes(bytes(img))
    verify_file(DST, "/etc/init.d/S20linkmount", p20)
    verify_file(DST, "/etc/init.d/S21appinit", p21)
    verify_file(DST, "/etc/init.d/S40network", p40)
    print(f"wrote {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
