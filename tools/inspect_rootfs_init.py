#!/usr/bin/env python3
from pathlib import Path

root = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img")
data = root.read_bytes()
print("rootfs", len(data), "ext4", data[0x438:0x43A].hex())
for k in (
    b"insmod_wifi.sh",
    b"/oem/usr/ko",
    b"S21",
    b"S50",
    b"S99",
    b"gpio-leds",
    b"/sys/class/leds",
    b"/sys/class/gpio",
    b"gpioset",
):
    print(k, data.find(k), "count", data.count(k))

# find init.d names
idx = 0
names = []
while True:
    i = data.find(b"S", idx)
    if i < 0 or len(names) > 40:
        break
    chunk = data[i : i + 40]
    if chunk[:3].startswith(b"S") and chunk[1:3].isdigit() and b"\x00" in chunk:
        n = chunk.split(b"\x00", 1)[0]
        if n not in names and len(n) < 32:
            names.append(n)
    idx = i + 1
print("possible Sxx", names[:30])
