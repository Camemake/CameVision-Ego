#!/usr/bin/env python3
"""Dump FIT / FDT info from boot.img and search LED / GPIO / pwrctrl / sdmmc."""
from pathlib import Path

boot = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\boot.img")
data = boot.read_bytes()
print("boot size", len(data), "magic", data[:4])

# find FDT blobs
off = 0
fdts = []
while True:
    i = data.find(b"\xd0\x0d\xfe\xed", off)
    if i < 0:
        break
    totalsize = int.from_bytes(data[i + 4 : i + 8], "big")
    fdts.append((i, totalsize))
    off = i + 4

print("fdt count", len(fdts))
for i, (off, sz) in enumerate(fdts[:12]):
    print(f"  [{i}] off={off:#x} size={sz}")

# strings of interest in whole image
keys = [
    b"gpio-leds",
    b"status-led",
    b"work-led",
    b"user_led",
    b"pwrctrl",
    b"sdmmc0",
    b"card-detect",
    b"cd-gpios",
    b"gpio0",
    b"GPIO0_A4",
    b"GPIO0_A5",
    b"GPIO0_A6",
    b"insmod_wifi",
    b"rk801",
    b"leds",
]
for k in keys:
    n = data.count(k)
    if n:
        print(f"  count {k!r} = {n}")

# dump strings around gpio-leds / leds from last fdt (usually kernel dtb)
if len(fdts) >= 2:
    off, sz = fdts[-1]
    blob = data[off : off + sz]
    # FDT strings block
    off_dt_strings = int.from_bytes(blob[12:16], "big")
    size_dt_strings = int.from_bytes(blob[32:36], "big")
    strings = blob[off_dt_strings : off_dt_strings + size_dt_strings]
    interesting = [s for s in strings.split(b"\x00") if s and any(
        x in s.lower() for x in (b"led", b"gpio0", b"pwrctrl", b"sdmmc", b"detect", b"wifi")
    )]
    print("dtb interesting strings:")
    for s in interesting[:80]:
        print(" ", s.decode("ascii", "replace"))
