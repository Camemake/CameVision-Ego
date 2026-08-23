#!/usr/bin/env python3
"""Patch Aura oem.img: start RGB LED green/blue 1s blink at boot."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

LED_LAUNCH = b"""# CameVision Single: D1 RGB, common anode, active-low
# R=GPIO0_A6  G=GPIO0_A5  B=GPIO0_A4
( /oem/usr/ko/status_led.sh >/dev/null 2>&1 & )
"""

LED_SCRIPT = b"""#!/bin/sh
# STATUS_LED_R GPIO0_A6, STATUS_LED_G GPIO0_A5, STATUS_LED_B GPIO0_A4
# Common anode: 0 = on, 1 = off

R=6
G=5
B=4
CHIP=/dev/gpiochip0

set_sysfs() {
	n="$1"
	v="$2"
	if [ ! -d /sys/class/gpio/gpio$n ]; then
		echo $n > /sys/class/gpio/export 2>/dev/null || true
	fi
	echo out > /sys/class/gpio/gpio$n/direction 2>/dev/null || true
	echo $v > /sys/class/gpio/gpio$n/value 2>/dev/null || true
}

set_gpiod() {
	r="$1"; g="$2"; b="$3"
	if command -v gpioset >/dev/null 2>&1; then
		gpioset -m exit $CHIP $R=$r $G=$g $B=$b 2>/dev/null && return 0
		gpioset $CHIP $R=$r $G=$g $B=$b 2>/dev/null && return 0
	fi
	return 1
}

led_off() {
	set_gpiod 1 1 1 || { set_sysfs $R 1; set_sysfs $G 1; set_sysfs $B 1; }
}

led_green() {
	set_gpiod 1 0 1 || { set_sysfs $R 1; set_sysfs $G 0; set_sysfs $B 1; }
}

led_blue() {
	set_gpiod 1 1 0 || { set_sysfs $R 1; set_sysfs $G 1; set_sysfs $B 0; }
}

# sysfs export once
if [ -w /sys/class/gpio/export ]; then
	echo $R > /sys/class/gpio/export 2>/dev/null || true
	echo $G > /sys/class/gpio/export 2>/dev/null || true
	echo $B > /sys/class/gpio/export 2>/dev/null || true
	echo out > /sys/class/gpio/gpio$R/direction 2>/dev/null || true
	echo out > /sys/class/gpio/gpio$G/direction 2>/dev/null || true
	echo out > /sys/class/gpio/gpio$B/direction 2>/dev/null || true
fi

led_off
while true; do
	led_green
	sleep 1
	led_blue
	sleep 1
done
"""


def u16(b: bytes, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


def parse_sb(img: bytes) -> dict:
    sb = 1024
    if img[sb + 0x38 : sb + 0x3A] != b"\x53\xef":
        raise SystemExit("not ext4")
    log_bs = u32(img, sb + 0x18)
    bs = 1024 << log_bs
    inodes_per_group = u32(img, sb + 0x28)
    inode_size = u16(img, sb + 0x58)
    first_data_block = u32(img, sb + 0x14)
    return {
        "bs": bs,
        "inodes_per_group": inodes_per_group,
        "inode_size": inode_size,
        "first_data_block": first_data_block,
        "desc_size": 64 if (u32(img, sb + 0x60) & 0x80) else 32,
        "feature_incompat": u32(img, sb + 0x60),
    }


def group_desc(img: bytes, sb: dict, group: int) -> tuple[int, int]:
    bs = sb["bs"]
    desc_size = sb["desc_size"]
    # group desc table starts at first_data_block+1, or block 1 if bs==1024
    gdb = 1 if bs == 1024 else (sb["first_data_block"] + 1)
    off = gdb * bs + group * desc_size
    inode_table = u32(img, off + 8)
    if desc_size >= 64:
        inode_table |= u32(img, off + 0x28) << 32
    return off, inode_table


def inode_offset(img: bytes, sb: dict, ino: int) -> int:
    group = (ino - 1) // sb["inodes_per_group"]
    index = (ino - 1) % sb["inodes_per_group"]
    _, itable = group_desc(img, sb, group)
    return itable * sb["bs"] + index * sb["inode_size"]


def inode_blocks(img: bytes, sb: dict, ino: int) -> tuple[int, int, list[int]]:
    """Return i_size, i_mode, list of logical data block numbers (direct only)."""
    ioff = inode_offset(img, sb, ino)
    mode = u16(img, ioff + 0)
    size_lo = u32(img, ioff + 4)
    size_hi = u32(img, ioff + 0x6C) if sb["inode_size"] >= 0x80 else 0
    size = size_lo | (size_hi << 32)
    flags = u32(img, ioff + 0x20)
    blocks = []
    if flags & 0x80000:  # EXT4_EXTENTS_FL
        # i_block starts at 0x28, extent header
        magic = u16(img, ioff + 0x28)
        if magic != 0xF30A:
            raise SystemExit(f"bad extent magic {magic:#x}")
        entries = u16(img, ioff + 0x2A)
        depth = u16(img, ioff + 0x2E)
        if depth != 0:
            raise SystemExit("extent tree depth > 0 not supported")
        for e in range(entries):
            eoff = ioff + 0x28 + 12 + e * 12
            ee_block = u32(img, eoff)
            ee_len = u16(img, eoff + 4)
            ee_start_hi = u16(img, eoff + 6)
            ee_start_lo = u32(img, eoff + 8)
            start = ee_start_lo | (ee_start_hi << 32)
            for i in range(ee_len & 0x7FFF):
                blocks.append(start + i)
            if ee_block != 0:
                pass
    else:
        for i in range(12):
            b = u32(img, ioff + 0x28 + i * 4)
            if b:
                blocks.append(b)
    return size, mode, blocks


def set_inode_size(img: bytearray, sb: dict, ino: int, new_size: int) -> None:
    ioff = inode_offset(img, sb, ino)
    struct.pack_into("<I", img, ioff + 4, new_size & 0xFFFFFFFF)
    if sb["inode_size"] >= 0x80:
        struct.pack_into("<I", img, ioff + 0x6C, new_size >> 32)


def read_file(img: bytes, sb: dict, ino: int) -> bytes:
    size, _, blocks = inode_blocks(img, sb, ino)
    bs = sb["bs"]
    data = b"".join(img[b * bs : (b + 1) * bs] for b in blocks)
    return data[:size]


def write_file_inplace(img: bytearray, sb: dict, ino: int, content: bytes) -> None:
    size, _, blocks = inode_blocks(img, sb, ino)
    cap = len(blocks) * sb["bs"]
    if len(content) > cap:
        raise SystemExit(
            f"file too large for allocated blocks: {len(content)} > {cap} (old size {size})"
        )
    padded = content + b"\x00" * (cap - len(content))
    bs = sb["bs"]
    for i, b in enumerate(blocks):
        img[b * bs : (b + 1) * bs] = padded[i * bs : (i + 1) * bs]
    set_inode_size(img, sb, ino, len(content))


def find_dir_ino(img: bytes, sb: dict, parent: int, name: bytes) -> int:
    data = read_file(img, sb, parent)
    off = 0
    while off + 8 <= len(data):
        ino, rec_len, name_len, file_type = struct.unpack_from("<IHBB", data, off)
        if rec_len == 0:
            break
        n = data[off + 8 : off + 8 + name_len]
        if ino and n == name:
            return ino
        off += rec_len
    raise SystemExit(f"dirent {name!r} not found in inode {parent}")


def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    img = bytearray(src.read_bytes())
    sb = parse_sb(img)
    print("block size", sb["bs"], "inode size", sb["inode_size"])

    # /oem is the fs root of oem.img
    usr = find_dir_ino(img, sb, 2, b"usr")
    ko = find_dir_ino(img, sb, usr, b"ko")
    wifi_ino = find_dir_ino(img, sb, ko, b"insmod_wifi.sh")
    wifi = read_file(img, sb, wifi_ino)
    print("insmod_wifi.sh inode", wifi_ino, "size", len(wifi))

    if b"status_led.sh" not in wifi:
        new_wifi = LED_LAUNCH + wifi
        if not new_wifi.startswith(b"#!/bin/sh"):
            # keep shebang first for busybox
            if wifi.startswith(b"#!/bin/sh"):
                rest = wifi.split(b"\n", 1)[1]
                new_wifi = b"#!/bin/sh\n" + LED_LAUNCH + rest
        write_file_inplace(img, sb, wifi_ino, new_wifi)
        print("patched insmod_wifi.sh ->", len(new_wifi))
    else:
        print("insmod_wifi.sh already launches status_led.sh")

    # Replace bringup_camemake.sh if it is unused capacity we need for a new file.
    # Put LED script in bringup_camemake.sh's unused? Better: overwrite a copy
    # by finding unused slack in a dedicated file.
    # Use hostapd_camemake.conf sibling: create by overwriting rk960_bt.sh spare?
    # We add status_led.sh by hijacking a file that is never executed: check bin/
    try:
        bin_ino = find_dir_ino(img, sb, usr, b"bin")
        bt_ino = find_dir_ino(img, sb, bin_ino, b"rk960_bt.sh")
        bt = read_file(img, sb, bt_ino)
        print("rk960_bt.sh size", len(bt), "cap check")
    except SystemExit as e:
        print(e)
        bt_ino = None
        bt = b""

    # Store LED script by replacing bringup_camemake.sh content? That file may run.
    # Prefer adding as new name by renaming unused: write into a file we create
    # via unused dirent. Simplest: write LED script INTO a new file occupying
    # bringup? No.
    #
    # Put the full LED loop inline in insmod_wifi if we cannot add a file.
    # Check whether we can reuse rk960_bt.sh if large enough, and add a dirent.
    # Easier path: embed the LED script body in insmod_wifi as a heredoc to /tmp
    # then exec. That needs no new file.

    _, _, wifi_blocks = inode_blocks(img, sb, wifi_ino)
    cap = len(wifi_blocks) * sb["bs"]
    print("insmod_wifi allocated", cap)

    # If we can fit both launch + script written to /tmp at runtime:
    # already patched a launcher expecting /oem/usr/ko/status_led.sh
    # So we MUST place status_led.sh. Overwrite rk960_bt.sh only if we also
    # add a directory entry named status_led.sh pointing at same inode? Ugly.
    #
    # Write LED_SCRIPT into a file named status_led.sh by cloning dirent of
    # an existing small/unused file and expanding? Can't allocate easily.
    #
    # Replace bringup_camemake.sh filename? Keep bringup content unused.
    # Change plan: write LED_SCRIPT over bringup_camemake.sh AND add dirent
    # status_led.sh with same inode (hardlink). Hardlink is just another dirent.

    bring_ino = find_dir_ino(img, sb, ko, b"bringup_camemake.sh")
    bring = read_file(img, sb, bring_ino)
    _, _, bring_blocks = inode_blocks(img, sb, bring_ino)
    bring_cap = len(bring_blocks) * sb["bs"]
    print("bringup_camemake.sh inode", bring_ino, "size", len(bring), "cap", bring_cap)

    if len(LED_SCRIPT) > bring_cap:
        raise SystemExit(f"LED script {len(LED_SCRIPT)} > bringup cap {bring_cap}")

    # Keep bringup content? User might want it. Don't overwrite bringup.
    # Inline the LED script into insmod_wifi instead of a separate file.

    wifi2 = read_file(img, sb, wifi_ino)
    # replace launcher with inlined background loop
    inline = b"""#!/bin/sh
# CameVision Single RGB D1: 1s green, 1s blue, common-anode active-low
# GPIO0_A6=R GPIO0_A5=G GPIO0_A4=B
led_blink() {
	R=6; G=5; B=4
	if [ -w /sys/class/gpio/export ]; then
		echo $R > /sys/class/gpio/export 2>/dev/null
		echo $G > /sys/class/gpio/export 2>/dev/null
		echo $B > /sys/class/gpio/export 2>/dev/null
		echo out > /sys/class/gpio/gpio$R/direction 2>/dev/null
		echo out > /sys/class/gpio/gpio$G/direction 2>/dev/null
		echo out > /sys/class/gpio/gpio$B/direction 2>/dev/null
	fi
	on() { echo 0 > /sys/class/gpio/gpio$1/value 2>/dev/null; }
	off() { echo 1 > /sys/class/gpio/gpio$1/value 2>/dev/null; }
	if command -v gpioset >/dev/null 2>&1; then
		while true; do
			gpioset -m exit /dev/gpiochip0 $R=1 $G=0 $B=1 2>/dev/null || gpioset /dev/gpiochip0 $R=1 $G=0 $B=1 2>/dev/null
			sleep 1
			gpioset -m exit /dev/gpiochip0 $R=1 $G=1 $B=0 2>/dev/null || gpioset /dev/gpiochip0 $R=1 $G=1 $B=0 2>/dev/null
			sleep 1
		done
	else
		while true; do
			off $R; on $G; off $B
			sleep 1
			off $R; off $G; on $B
			sleep 1
		done
	fi
}
led_blink >/dev/null 2>&1 &

"""
    orig = wifi
    if orig.startswith(b"#!/bin/sh"):
        orig_body = orig.split(b"\n", 1)[1]
    else:
        orig_body = orig
    # strip previous LED_LAUNCH if present
    if orig_body.startswith(LED_LAUNCH) or b"status_led.sh" in orig_body[:400]:
        # drop first launch lines
        lines = orig_body.splitlines(True)
        while lines and (
            lines[0].startswith(b"# CameVision")
            or lines[0].startswith(b"# R=GPIO")
            or b"status_led.sh" in lines[0]
            or lines[0].strip() == b""
        ):
            lines.pop(0)
        orig_body = b"".join(lines)

    combined = inline + orig_body
    print("combined insmod_wifi.sh", len(combined), "cap", cap)
    write_file_inplace(img, sb, wifi_ino, combined)

    # Also write a standalone file over rk960_bt.sh using a hardlink dirent
    # named status_led.sh if there is free rec_len slack in the ko directory.
    # Skip if combined already has the blinker.

    dst.write_bytes(img)
    print("wrote", dst, "bytes", len(img))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
