#!/usr/bin/env python3
"""Blink D1 from insmod_ko.sh via /sys/class/leds (no GPIO sysfs on this kernel)."""
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
DST = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\oem_led.img")
TARGET = "/usr/ko/insmod_ko.sh"

LED = b"""#!/bin/sh
# CameVision Single D1 RGB GPIO0_A6/A5/A4 common-anode active-low
(
	base=0
	for d in /sys/class/gpio/gpiochip*; do
		[ -f "$d/base" ] || continue
		lab=`cat "$d/label" 2>/dev/null`
		echo "$lab" | grep -q "20600000\\|gpio0" && base=`cat "$d/base"` && break
	done
	R=$((base + 6)); G=$((base + 5)); B=$((base + 4))
	for n in $R $G $B; do
		echo $n > /sys/class/gpio/export 2>/dev/null
		echo out > /sys/class/gpio/gpio$n/direction 2>/dev/null
		echo 1 > /sys/class/gpio/gpio$n/value 2>/dev/null
	done
	while true; do
		echo 1 > /sys/class/gpio/gpio$R/value
		echo 0 > /sys/class/gpio/gpio$G/value
		echo 1 > /sys/class/gpio/gpio$B/value
		sleep 1
		echo 1 > /sys/class/gpio/gpio$R/value
		echo 1 > /sys/class/gpio/gpio$G/value
		echo 0 > /sys/class/gpio/gpio$B/value
		sleep 1
	done
) >/dev/null 2>&1 &

"""


def strip_led(data: bytes) -> bytes:
    rest = data.split(b"\n", 1)[1] if data.startswith(b"#!/bin/sh") else data
    start = rest.find(b"# CameVision Single")
    if start < 0:
        return rest
    end = rest.find(b") >/dev/null 2>&1 &\n", start)
    if end < 0:
        return rest
    rest = rest[:start] + rest[end + len(b") >/dev/null 2>&1 &\n") :]
    return rest.lstrip(b"\n")


def transform(data: bytes) -> bytes:
    out = LED + strip_led(data)
    if not out.startswith(b"#!/bin/sh"):
        raise SystemExit("shebang missing")
    if b"base + 6" not in out or b"gpio$G" not in out:
        raise SystemExit("gpio LED script missing")
    return out


def main() -> int:
    img = bytearray(SRC.read_bytes())
    sb = parse_sb(bytes(img))
    DST.parent.mkdir(parents=True, exist_ok=True)
    last = b""
    for target in ("/usr/ko/insmod_ko.sh", "/usr/ko/insmod_wifi.sh"):
        last = patch_file(img, sb, target, transform)
        DST.write_bytes(bytes(img))
        verify_file(DST, target, last)
        print(last.decode(errors="replace").split(") >/dev/null", 1)[0][:280])
    print(f"wrote {DST} ({DST.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
