#!/usr/bin/env python3
from pathlib import Path
import struct

img = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img").read_bytes()

keys = [
    b"RkLunch",
    b"insmod_ko",
    b"S21appinit",
    b"linkmount",
    b"/oem/usr",
    b"mount /oem",
    b"mmcblk0p",
    b"start_rk",
    b"async-commit",
    b"usbdevice.sh",
    b"adbd",
]
for k in keys:
    print(repr(k), "find", img.find(k), "count", img.count(k))

# dump around /oem/usr
i = img.find(b"/oem/usr")
while i != -1 and i < img.find(b"/oem/usr") + 500000:
    ctx = img[max(0, i-60):i+80]
    s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
    if "oem" in s:
        print(hex(i), s)
    i = img.find(b"/oem/usr", i+1)
    if img.find(b"/oem/usr") >= 0 and i > img.find(b"/oem/usr") + 2000000:
        break

print("--- first 8 /oem/usr ---")
idx = 0
for n in range(8):
    i = img.find(b"/oem/usr", idx)
    if i < 0:
        break
    print(hex(i), "".join(chr(c) if 32 <= c < 127 else "." for c in img[i-40:i+70]))
    idx = i+1
