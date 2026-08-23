#!/usr/bin/env python3
"""Rewrite the contents of a file inside an ext4 image, offline.

The new content is written into the blocks the file already owns, so the extent
tree never changes and only i_size is updated. Refuses to run if the content
would not fit in the allocated blocks.

Importable: patch_file(img, sb, path, transform).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent))
from ext4_ls import extent_blocks, listdir, parse_sb, u32  # noqa: E402


def inode_off(img, sb, ino: int) -> int:
    gdb = sb["first_data_block"] + 1
    g = (ino - 1) // sb["inodes_per_group"]
    i = (ino - 1) % sb["inodes_per_group"]
    doff = gdb * sb["bs"] + g * sb["desc_size"]
    table = u32(img, doff + 8)
    if sb["desc_size"] >= 64:
        table |= u32(img, doff + 0x28) << 32
    return table * sb["bs"] + i * sb["inode_size"]


def resolve(img, sb, path: str) -> int:
    ino = 2
    for part in [p for p in path.strip("/").split("/") if p]:
        for name, child, _ in listdir(img, sb, ino):
            if name == part:
                ino = child
                break
        else:
            raise SystemExit(f"not found: {path}")
    return ino


def read_file(img, sb, path: str) -> tuple[int, int, list[int], bytes]:
    ino = resolve(img, sb, path)
    ioff = inode_off(img, sb, ino)
    size = u32(img, ioff + 4)
    if not u32(img, ioff + 0x20) & 0x80000:
        raise SystemExit(f"{path}: not extent-mapped, unsupported")
    blocks = extent_blocks(img, sb, ioff, ioff + 0x28)
    data = b"".join(img[b * sb["bs"] : (b + 1) * sb["bs"]] for b in blocks)[:size]
    return ino, ioff, blocks, data


def patch_file(
    img: bytearray, sb: dict, path: str, transform: Callable[[bytes], bytes]
) -> bytes:
    ino, ioff, blocks, data = read_file(bytes(img), sb, path)
    capacity = len(blocks) * sb["bs"]
    print(f"{path}: inode {ino} size {len(data)} blocks {len(blocks)} capacity {capacity}")

    patched = transform(data)
    print(f"  new size {len(patched)} ({len(patched) - len(data):+d} bytes)")
    if len(patched) > capacity:
        raise SystemExit(f"  does not fit: {len(patched)} > {capacity}")

    padded = patched + b"\x00" * (capacity - len(patched))
    for i, b in enumerate(blocks):
        img[b * sb["bs"] : (b + 1) * sb["bs"]] = padded[i * sb["bs"] : (i + 1) * sb["bs"]]
    struct.pack_into("<I", img, ioff + 4, len(patched))
    return patched


def verify_file(image_path: Path, path: str, expect: bytes) -> None:
    img = image_path.read_bytes()
    sb = parse_sb(img)
    _, _, _, data = read_file(img, sb, path)
    if data != expect:
        raise SystemExit(f"verification failed for {path}")
    print(f"  verified {path}: {len(data)} bytes re-read from {image_path.name}")


def main() -> int:
    src, dst, path, oldf, newf = sys.argv[1:6]
    old = Path(oldf).read_bytes().replace(b"\r\n", b"\n")
    new = Path(newf).read_bytes().replace(b"\r\n", b"\n")

    img = bytearray(Path(src).read_bytes())
    sb = parse_sb(bytes(img))

    def transform(data: bytes) -> bytes:
        hits = data.count(old)
        if hits != 1:
            raise SystemExit(f"search text found {hits} times, need exactly 1")
        return data.replace(old, new)

    patched = patch_file(img, sb, path, transform)
    Path(dst).write_bytes(bytes(img))
    verify_file(Path(dst), path, patched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
