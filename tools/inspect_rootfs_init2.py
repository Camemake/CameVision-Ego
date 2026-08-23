#!/usr/bin/env python3
from pathlib import Path

root = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img")
data = root.read_bytes()
for k in (
    b"insmod_wifi",
    b"insmod_ko",
    b"/oem/",
    b"usr/ko",
    b"rkwifi",
    b"S50wifi",
    b"S40wifi",
    b"S30wifi",
    b"S99wifi",
    b"wifi.sh",
    b"mount.*oem",
    b"/dev/mmcblk0p",
    b"blkdevparts",
    b"work_led",
    b"work-led",
    b"/sys/class/leds/",
):
    print(repr(k), "find", data.find(k), "count", data.count(k))

# dump a window around /sys/class/leds
i = data.find(b"/sys/class/leds")
if i >= 0:
    print("--- leds context ---")
    print(data[i - 80 : i + 120])

i = data.find(b"/oem/")
print("first /oem/", i)
if i >= 0:
    print(data[i : i + 80])

# find init.d directory entries by searching S10
for name in [b"S10udev", b"S20urandom", b"S40network", b"S50wifi", b"S60wifi", b"S80wifi", b"S90wifi", b"S99", b"rcS", b"inittab"]:
    print(name, data.find(name))
