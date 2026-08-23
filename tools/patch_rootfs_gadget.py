#!/usr/bin/env python3
"""Make the board come up as a USB webcam gadget on every boot.

/etc/init.d/S50usbdevice is Rockchip's configfs gadget setup. It takes its
function list from /tmp/.usb_config, and because /tmp is a tmpfs that file never
exists at boot, so the script always falls back to the single line it writes
itself: "usb_adb_en". That fallback is the only thing deciding what this board
presents on USB, so it is what we change.

Edits, all inside that one script:
  1. fallback function list  adb  ->  uvc first, then adb
  2. USB manufacturer string rockchip -> CameMake
  3. USB product string      rk3xxx   -> CameVision Single
  4. VID/PID/MaxPower match the working M1 gadget (39c5:0001, 900 mA)
  5. before UDC bind, wait for a UDC (M1 DTB is already peripheral)

UVC is listed first so it becomes interface 0 and the host treats the device as
a camera; adb is kept behind it so the board stays reachable for bring-up.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import parse_sb  # noqa: E402
from ext4_patch import patch_file, verify_file  # noqa: E402

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock"
    r"\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\rootfs_uvc.img")
TARGET = "/etc/init.d/S50usbdevice"


def sub_once(data: bytes, pattern: bytes, repl: bytes, what: str) -> bytes:
    matches = list(re.finditer(pattern, data))
    if len(matches) != 1:
        raise SystemExit(f"{what}: matched {len(matches)} times, need exactly 1")
    out = re.sub(pattern, repl, data, count=1)
    print(f"  {what}: ok")
    return out


def transform(data: bytes) -> bytes:
    # 1. the fallback function list
    data = sub_once(
        data,
        rb'([ \t]*)echo "usb_adb_en" >> \$USB_CONFIG_FILE',
        rb'\1echo "usb_uvc_en" >> $USB_CONFIG_FILE\n\1echo "usb_adb_en" >> $USB_CONFIG_FILE',
        "uvc added ahead of adb in the fallback config",
    )
    # 2 + 3. identify the device as this board rather than a generic Rockchip SoC
    data = sub_once(
        data,
        rb'echo "rockchip"(\s+)> \$\{USB_STRINGS_DIR\}/manufacturer',
        rb'echo "CameMake"\1> ${USB_STRINGS_DIR}/manufacturer',
        "manufacturer string",
    )
    data = sub_once(
        data,
        rb'echo "rk3xxx"(\s+)> \$\{USB_STRINGS_DIR\}/product',
        rb'echo "CameVision Single"\1> ${USB_STRINGS_DIR}/product',
        "product string",
    )
    data = sub_once(
        data,
        rb"echo 0x2207 > \$\{USB_CONFIGFS_DIR\}/idVendor",
        rb"echo 0x39c5 > ${USB_CONFIGFS_DIR}/idVendor",
        "idVendor 39c5 (same as working M1 gadget)",
    )
    data = sub_once(
        data,
        rb"echo \$PID > \$\{USB_CONFIGFS_DIR\}/idProduct",
        rb"echo 0x0001 > ${USB_CONFIGFS_DIR}/idProduct",
        "idProduct 0001 (same as working M1 gadget)",
    )
    data = sub_once(
        data,
        rb"echo 500 > \$\{USB_CONFIGS_DIR\}/MaxPower",
        rb"echo 900 > ${USB_CONFIGS_DIR}/MaxPower",
        "MaxPower 900 mA like M1",
    )
    data = sub_once(
        data,
        rb"\tpre_run_binary\n\tsleep 1\n\tUDC=`ls /sys/class/udc/\| awk '\{print \$1\}'`\n",
        rb"""	pre_run_binary
	i=0
	while [ $i -lt 20 ]; do
		for f in /sys/class/usb_role/*/role; do echo device > $f; done
		for f in /sys/devices/platform/*/otg_mode; do echo peripheral > $f; done
		UDC=`ls /sys/class/udc/ 2>/dev/null | awk '{print $1}'`
		[ -n "$UDC" ] && break
		sleep 1
		i=$((i+1))
	done
""",
        "wait up to 20s for UDC after forcing device mode",
    )
    return data


def main() -> int:
    DST.parent.mkdir(parents=True, exist_ok=True)
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    print(f"{SRC.name}: block size {sb['bs']}, inode size {sb['inode_size']}")

    patched = patch_file(img, sb, TARGET, transform)
    DST.write_bytes(bytes(img))
    print(f"wrote {DST} ({len(img)} bytes)")
    verify_file(DST, TARGET, patched)

    text = patched.decode("utf-8", "replace")
    i = text.find("Cannot find .usb_config")
    print("\n--- fallback block as flashed ---")
    print(text[max(0, i - 120) : i + 260])
    for key in ("manufacturer", "product"):
        for line in text.splitlines():
            if f"USB_STRINGS_DIR}}/{key}" in line:
                print(line.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
