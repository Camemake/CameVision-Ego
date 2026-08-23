#!/usr/bin/env python3
"""Stock Aura S50usbdevice, but wait for a UDC before bind.

Does not change VID/PID or enable UVC. ADB fallback stays usb_adb_en.
Does not poke usb_role / otg_mode (M1 DTB is already peripheral).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\rootfs_adbwait.img")
TARGET = "/etc/init.d/S50usbdevice"

OLD = b"""	pre_run_binary
	sleep 1
	UDC=`ls /sys/class/udc/| awk '{print $1}'`
	echo $UDC > ${USB_CONFIGFS_DIR}/UDC
"""

NEW = b"""	pre_run_binary
	i=0
	UDC=
	while [ $i -lt 20 ]; do
		UDC=`ls /sys/class/udc/ 2>/dev/null | awk '{print $1}'`
		[ -n "$UDC" ] && break
		sleep 1
		i=$((i+1))
	done
	echo $UDC > ${USB_CONFIGFS_DIR}/UDC
"""


def transform(data: bytes) -> bytes:
    n = data.count(OLD)
    if n != 1:
        raise SystemExit(f"bind block matched {n} times, need 1")
    out = data.replace(OLD, NEW)
    if b'echo "usb_adb_en" >> $USB_CONFIG_FILE' not in out:
        raise SystemExit("adb fallback missing")
    if b'echo "usb_uvc_en"' in out:
        raise SystemExit("UVC enabled in fallback")
    if b"usb_role" in out or b"otg_mode" in out:
        raise SystemExit("role-switch poke leaked")
    return out


def main() -> int:
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    patched = patch_file(img, sb, TARGET, transform)
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_bytes(bytes(img))
    verify_file(DST, TARGET, patched)
    print(f"wrote {DST} ({len(img)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
