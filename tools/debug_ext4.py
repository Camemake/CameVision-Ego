#!/usr/bin/env python3
from pathlib import Path
import struct

img = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img").read_bytes()
sb = 1024
print("magic", img[sb+0x38:sb+0x3A].hex())
print("log_bs", struct.unpack_from("<I", img, sb+0x18)[0])
print("blocks_per_group", struct.unpack_from("<I", img, sb+0x20)[0])
print("inodes_per_group", struct.unpack_from("<I", img, sb+0x28)[0])
print("inode_size", struct.unpack_from("<H", img, sb+0x58)[0])
print("first_data", struct.unpack_from("<I", img, sb+0x14)[0])
print("feat_incompat", hex(struct.unpack_from("<I", img, sb+0x60)[0]))
print("feat_compat", hex(struct.unpack_from("<I", img, sb+0x5C)[0]))
print("feat_ro", hex(struct.unpack_from("<I", img, sb+0x64)[0]))
print("desc_size field", struct.unpack_from("<H", img, sb+0xFE)[0] if True else None)
# s_desc_size is at 0xFE only if 64bit
feat_incompat = struct.unpack_from("<I", img, sb+0x60)[0]
print("64bit", bool(feat_incompat & 0x80), "extents", bool(feat_incompat & 0x40), "flex_bg", bool(struct.unpack_from("<I", img, sb+0x64)[0] & 0x200))

bs = 1024 << struct.unpack_from("<I", img, sb+0x18)[0]
print("bs", bs)
desc_size = struct.unpack_from("<H", img, sb+0xFE)[0] if feat_incompat & 0x80 else 32
if desc_size == 0:
    desc_size = 32
print("desc_size", desc_size)

# group 0 desc
gdb = 1 if bs == 1024 else 1  # block 1 after super at 0 for 4k
# for 4096 bs, super is in block 0, gdb at block 1
print("block0 start magic?", img[0x438:0x43A].hex())
g0 = bs * 1
print("g0 desc", img[g0:g0+desc_size].hex())
bg_inode_table_lo = struct.unpack_from("<I", img, g0+8)[0]
bg_inode_table_hi = struct.unpack_from("<I", img, g0+0x28)[0] if desc_size >= 64 else 0
itable = bg_inode_table_lo | (bg_inode_table_hi << 32)
print("inode table blk", itable)

inode_size = struct.unpack_from("<H", img, sb+0x58)[0]
# root inode 2 -> index 1
ioff = itable * bs + 1 * inode_size
print("root inode off", hex(ioff))
print("root inode raw", img[ioff:ioff+128].hex())
mode = struct.unpack_from("<H", img, ioff)[0]
print("mode", hex(mode), "size", struct.unpack_from("<I", img, ioff+4)[0])
print("flags", hex(struct.unpack_from("<I", img, ioff+0x20)[0]))
print("i_block", img[ioff+0x28:ioff+0x28+60].hex())
magic = struct.unpack_from("<H", img, ioff+0x28)[0]
print("extent magic", hex(magic), "entries", struct.unpack_from("<H", img, ioff+0x2A)[0], "depth", struct.unpack_from("<H", img, ioff+0x2E)[0])
