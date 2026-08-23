#!/usr/bin/env python3
"""Dump ext4 superblock fields and the root inode so layout problems are visible."""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


img = Path(sys.argv[1]).read_bytes()
print(f"file size {len(img)}")
sb = 1024
print(f"magic at 0x438: {img[sb + 0x38:sb + 0x3A].hex()}  (expect 53ef)")

inodes_count = u32(img, sb + 0x0)
blocks_count = u32(img, sb + 0x4)
first_data_block = u32(img, sb + 0x14)
log_bs = u32(img, sb + 0x18)
blocks_per_group = u32(img, sb + 0x20)
inodes_per_group = u32(img, sb + 0x28)
inode_size = u16(img, sb + 0x58)
feat_compat = u32(img, sb + 0x5C)
feat_incompat = u32(img, sb + 0x60)
feat_ro = u32(img, sb + 0x64)
desc_size = u16(img, sb + 0xFE)

print(f"inodes_count       {inodes_count}")
print(f"blocks_count       {blocks_count}")
print(f"first_data_block   {first_data_block}")
print(f"block size         {1024 << log_bs}")
print(f"blocks_per_group   {blocks_per_group}")
print(f"inodes_per_group   {inodes_per_group}")
print(f"inode_size         {inode_size}")
print(f"feat_compat        {feat_compat:#x}")
print(f"feat_incompat      {feat_incompat:#x}  (0x80=64bit, 0x40=extents, 0x2=filetype)")
print(f"feat_ro_compat     {feat_ro:#x}")
print(f"s_desc_size        {desc_size}")

bs = 1024 << log_bs
eff_desc = desc_size if (feat_incompat & 0x80) else 32
gdb = 1 if bs == 1024 else (first_data_block + 1)
print(f"group desc block   {gdb}  entry size {eff_desc}")

for g in range(min(3, max(1, blocks_count // max(1, blocks_per_group) + 1))):
    off = gdb * bs + g * eff_desc
    bb = u32(img, off + 0)
    ib = u32(img, off + 4)
    it = u32(img, off + 8)
    if eff_desc >= 64:
        it |= u32(img, off + 0x28) << 32
    print(f"group {g}: block_bitmap={bb} inode_bitmap={ib} inode_table={it}")

it0 = u32(img, gdb * bs + 8)
if eff_desc >= 64:
    it0 |= u32(img, gdb * bs + 0x28) << 32
root = it0 * bs + (2 - 1) * inode_size
print(f"\nroot inode at file offset {root:#x}")
print("first 64 bytes:", img[root : root + 64].hex())
print(f"i_mode  {u16(img, root):#o}")
print(f"i_size  {u32(img, root + 4)}")
print(f"i_flags {u32(img, root + 0x20):#x}  (0x80000=extents, 0x10000000=inline)")
print("i_block[0:16]:", img[root + 0x28 : root + 0x38].hex())
print(f"extent magic {u16(img, root + 0x28):#x} (expect f30a)")
