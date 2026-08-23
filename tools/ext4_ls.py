#!/usr/bin/env python3
"""List directories inside an ext4 image, optionally recursively.

Usage:
    ext4_ls.py <image> <path> [more paths...] [--depth N] [--grep PATTERN]
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

FT = {1: "f", 2: "d", 3: "chr", 4: "blk", 5: "fifo", 6: "sock", 7: "link"}


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def parse_sb(img):
    sb = 1024
    if img[sb + 0x38 : sb + 0x3A] != b"\x53\xef":
        raise SystemExit("not ext4")
    return {
        "bs": 1024 << u32(img, sb + 0x18),
        "inodes_per_group": u32(img, sb + 0x28),
        "inode_size": u16(img, sb + 0x58),
        "first_data_block": u32(img, sb + 0x14),
        "desc_size": 64 if (u32(img, sb + 0x60) & 0x80) else 32,
    }


def group_inode_table(img, sb, group):
    bs = sb["bs"]
    # group descriptors always live in the block right after the superblock
    gdb = sb["first_data_block"] + 1
    off = gdb * bs + group * sb["desc_size"]
    t = u32(img, off + 8)
    if sb["desc_size"] >= 64:
        t |= u32(img, off + 0x28) << 32
    return t


def inode_off(img, sb, ino):
    g = (ino - 1) // sb["inodes_per_group"]
    i = (ino - 1) % sb["inodes_per_group"]
    return group_inode_table(img, sb, g) * sb["bs"] + i * sb["inode_size"]


def extent_blocks(img, sb, ioff, base):
    """Walk an extent tree of arbitrary depth, returning file blocks in order."""
    entries = u16(img, base + 2)
    depth = u16(img, base + 6)
    out: list[int] = []
    for e in range(entries):
        eoff = base + 12 + e * 12
        if depth == 0:
            ee_len = u16(img, eoff + 4)
            if ee_len > 0x8000:
                ee_len -= 0x8000
            start = u32(img, eoff + 8) | (u16(img, eoff + 6) << 32)
            out.extend(range(start, start + ee_len))
        else:
            child = u32(img, eoff + 4) | (u16(img, eoff + 8) << 32)
            cbase = child * sb["bs"]
            if u16(img, cbase) != 0xF30A:
                raise SystemExit("bad extent child magic")
            out.extend(extent_blocks(img, sb, ioff, cbase))
    return out


def read_ino(img, sb, ino):
    ioff = inode_off(img, sb, ino)
    mode = u16(img, ioff)
    size = u32(img, ioff + 4)
    # i_size_high shares its slot with i_dir_acl, so only trust it for files
    if (mode & 0xF000) == 0x8000:
        size |= u32(img, ioff + 0x6C) << 32
    flags = u32(img, ioff + 0x20)
    if flags & 0x10000000:
        # inline data: the payload lives in the 60-byte i_block area
        return mode, size, img[ioff + 0x28 : ioff + 0x28 + min(size, 60)]
    if flags & 0x80000:
        base = ioff + 0x28
        if u16(img, base) != 0xF30A:
            return mode, size, b""
        try:
            blocks = extent_blocks(img, sb, ioff, base)
        except SystemExit:
            return mode, size, b""
    else:
        # fast symlink: target stored inline
        if (mode & 0xF000) == 0xA000 and size < 60:
            return mode, size, img[ioff + 0x28 : ioff + 0x28 + size]
        blocks = [u32(img, ioff + 0x28 + i * 4) for i in range(12)]
        blocks = [b for b in blocks if b]
    data = b"".join(img[b * sb["bs"] : (b + 1) * sb["bs"]] for b in blocks)
    return mode, size, data[:size]


def listdir(img, sb, ino):
    _, _, data = read_ino(img, sb, ino)
    out = []
    off = 0
    while off + 8 <= len(data):
        child, rec_len, name_len, ftype = struct.unpack_from("<IHBB", data, off)
        if rec_len == 0:
            break
        name = data[off + 8 : off + 8 + name_len].decode("utf-8", "replace")
        if child and name not in (".", ".."):
            out.append((name, child, ftype))
        off += rec_len
    return sorted(out)


def resolve(img, sb, path):
    ino = 2
    for part in [p for p in path.strip("/").split("/") if p]:
        for name, child, _ in listdir(img, sb, ino):
            if name == part:
                ino = child
                break
        else:
            raise FileNotFoundError(path)
    return ino


def walk(img, sb, path, ino, depth, maxdepth, pat, out):
    for name, child, ftype in listdir(img, sb, ino):
        full = f"{path.rstrip('/')}/{name}"
        kind = FT.get(ftype, "?")
        try:
            mode, size, data = read_ino(img, sb, child)
        except Exception:
            mode, size, data = 0, 0, b""
        extra = ""
        if kind == "link":
            extra = " -> " + data[:120].decode("utf-8", "replace")
        line = f"{kind} {size:>10} {full}{extra}"
        if pat is None or pat.search(full):
            out.append(line)
        if kind == "d" and depth < maxdepth:
            walk(img, sb, full, child, depth + 1, maxdepth, pat, out)


def main():
    args = [a for a in sys.argv[1:]]
    depth = 1
    pat = None
    if "--depth" in args:
        i = args.index("--depth")
        depth = int(args[i + 1])
        del args[i : i + 2]
    if "--grep" in args:
        i = args.index("--grep")
        pat = re.compile(args[i + 1], re.I)
        del args[i : i + 2]

    cat = False
    if "--cat" in args:
        args.remove("--cat")
        cat = True

    img = Path(args[0]).read_bytes()
    sb = parse_sb(img)

    if cat:
        for path in args[1:]:
            print(f"\n===== {path} =====")
            try:
                ino = resolve(img, sb, path)
            except FileNotFoundError:
                print("  (missing)")
                continue
            _, size, data = read_ino(img, sb, ino)
            sys.stdout.buffer.write(data[:20000])
            if size > 20000:
                print(f"\n... truncated, total {size} bytes ...")
            print()
        return

    for path in args[1:]:
        print(f"\n===== {path} =====")
        try:
            ino = resolve(img, sb, path)
        except FileNotFoundError:
            print("  (missing)")
            continue
        out: list[str] = []
        walk(img, sb, path, ino, 0, depth, pat, out)
        for line in out:
            print("  " + line)
        print(f"  ({len(out)} entries)")


if __name__ == "__main__":
    main()
