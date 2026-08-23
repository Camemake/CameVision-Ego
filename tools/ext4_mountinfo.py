#!/usr/bin/env python3
"""Print the ext4 superblock fields that record whether a filesystem was mounted.

A freshly built image has mount count 0, no last-mounted path and no lifetime
write counter. If the board ever boots Linux and mounts the partition read-write,
the kernel updates these fields. Reading them back from eMMC therefore tells us
whether the kernel got as far as mounting, without needing a serial console.

Usage:
    ext4_mountinfo.py <image-or-partition-dump> [...]
"""
from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

SB = 1024


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def stamp(v: int) -> str:
    if v == 0:
        return "never"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(v)) + " UTC"


for arg in sys.argv[1:]:
    p = Path(arg)
    with p.open("rb") as f:
        head = f.read(SB + 0x400)
    print(f"===== {p.name} ({p.stat().st_size} bytes) =====")
    if head[SB + 0x38 : SB + 0x3A] != b"\x53\xef":
        print("  not an ext4 superblock here")
        continue

    state = u16(head, SB + 0x3A)
    print(f"  volume name      {head[SB + 0x78:SB + 0x88].split(bytes(1))[0]!r}")
    print(f"  last mounted on  {head[SB + 0x88:SB + 0xC8].split(bytes(1))[0]!r}")
    print(f"  mount count      {u16(head, SB + 0x34)} of max {u16(head, SB + 0x36)}")
    print(f"  last mount time  {stamp(u32(head, SB + 0x2C))}")
    print(f"  last write time  {stamp(u32(head, SB + 0x30))}")
    print(f"  last fsck time   {stamp(u32(head, SB + 0x40))}")
    print(f"  state            {state:#x} ({'clean' if state & 1 else 'NOT clean'})")
    print(f"  lifetime written {u64(head, SB + 0x150)} KiB")
    print(f"  free blocks      {u32(head, SB + 0x0C)} of {u32(head, SB + 0x4)}")
    print(f"  free inodes      {u32(head, SB + 0x10)} of {u32(head, SB + 0x0)}")
