#!/usr/bin/env python3
"""Read named files from an ext4 image (extents, depth 0)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def parse_sb(img):
    sb = 1024
    log_bs = u32(img, sb + 0x18)
    return {
        "bs": 1024 << log_bs,
        "inodes_per_group": u32(img, sb + 0x28),
        "inode_size": u16(img, sb + 0x58),
        "first_data_block": u32(img, sb + 0x14),
        "desc_size": 64 if (u32(img, sb + 0x60) & 0x80) else 32,
    }


def group_inode_table(img, sb, group):
    bs = sb["bs"]
    gdb = 1 if bs == 1024 else (sb["first_data_block"] + 1)
    off = gdb * bs + group * sb["desc_size"]
    inode_table = u32(img, off + 8)
    if sb["desc_size"] >= 64:
        inode_table |= u32(img, off + 0x28) << 32
    return inode_table


def inode_off(img, sb, ino):
    group = (ino - 1) // sb["inodes_per_group"]
    index = (ino - 1) % sb["inodes_per_group"]
    return group_inode_table(img, sb, group) * sb["bs"] + index * sb["inode_size"]


def read_ino(img, sb, ino):
    ioff = inode_off(img, sb, ino)
    size = u32(img, ioff + 4)
    if sb["inode_size"] >= 0x80:
        size |= u32(img, ioff + 0x6C) << 32
    flags = u32(img, ioff + 0x20)
    blocks = []
    if flags & 0x80000:
        magic = u16(img, ioff + 0x28)
        if magic != 0xF30A:
            raise SystemExit("bad extent")
        entries = u16(img, ioff + 0x2A)
        depth = u16(img, ioff + 0x2E)
        if depth != 0:
            raise SystemExit("extent depth")
        for e in range(entries):
            eoff = ioff + 0x28 + 12 + e * 12
            ee_len = u16(img, eoff + 4) & 0x7FFF
            start = u32(img, eoff + 8) | (u16(img, eoff + 6) << 32)
            blocks.extend(range(start, start + ee_len))
    else:
        for i in range(12):
            b = u32(img, ioff + 0x28 + i * 4)
            if b:
                blocks.append(b)
    data = b"".join(img[b * sb["bs"] : (b + 1) * sb["bs"]] for b in blocks)
    return size, data[:size]


def find_dir(img, sb, parent, name: bytes) -> int:
    size, data = read_ino(img, sb, parent)
    off = 0
    while off + 8 <= len(data):
        ino, rec_len, name_len, ft = struct.unpack_from("<IHBB", data, off)
        if rec_len == 0:
            break
        n = data[off + 8 : off + 8 + name_len]
        if ino and n == name:
            return ino
        off += rec_len
    raise FileNotFoundError(name)


def resolve(img, sb, path: str) -> int:
    ino = 2
    for part in path.strip("/").split("/"):
        ino = find_dir(img, sb, ino, part.encode())
    return ino


def main():
    img = Path(sys.argv[1]).read_bytes()
    sb = parse_sb(img)
    for p in sys.argv[2:]:
        try:
            ino = resolve(img, sb, p)
            size, data = read_ino(img, sb, ino)
            print(f"===== {p} inode={ino} size={size} =====")
            sys.stdout.buffer.write(data[:8000] + (b"\n...truncated...\n" if size > 8000 else b""))
            if not data.endswith(b"\n"):
                print()
        except Exception as e:
            print(f"===== {p} ERROR {e} =====")


if __name__ == "__main__":
    main()
