#!/usr/bin/env python3
"""Minimal FDT walker to print leds / pwrctrl / sdmmc0 / gpio nodes."""
from pathlib import Path
import struct

boot = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\boot.img")
data = boot.read_bytes()
# kernel dtb is last FIT image typically; use the 182352-byte blob at 0x800 (first real dtb)
off, sz = 0x800, 182352
blob = data[off : off + sz]

FDT_BEGIN_NODE = 0x1
FDT_END_NODE = 0x2
FDT_PROP = 0x3
FDT_NOP = 0x4
FDT_END = 0x9

off_dt_struct = struct.unpack(">I", blob[8:12])[0]
off_dt_strings = struct.unpack(">I", blob[12:16])[0]
size_dt_struct = struct.unpack(">I", blob[36:40])[0]

def align4(x):
    return (x + 3) & ~3

def get_str(off):
    end = blob.find(b"\x00", off_dt_strings + off)
    return blob[off_dt_strings + off : end].decode("ascii", "replace")

pos = off_dt_struct
path = []
want = ("led", "pwrctrl", "sdmmc0", "gpio0", "rk801", "pinctrl")
while pos < off_dt_struct + size_dt_struct:
    token = struct.unpack_from(">I", blob, pos)[0]
    pos += 4
    if token == FDT_BEGIN_NODE:
        end = blob.find(b"\x00", pos)
        name = blob[pos:end].decode("ascii", "replace")
        pos = align4(end + 1)
        path.append(name)
        continue
    if token == FDT_END_NODE:
        if path:
            path.pop()
        continue
    if token == FDT_PROP:
        plen, nameoff = struct.unpack_from(">II", blob, pos)
        pos += 8
        pname = get_str(nameoff)
        pval = blob[pos : pos + plen]
        pos = align4(pos + plen)
        pth = "/".join(path)
        low = (pth + " " + pname).lower()
        if any(w in low for w in want) or any(w in pname.lower() for w in ("gpios", "led", "pwrctrl", "cd-gpios")):
            # print compact
            if plen == 0:
                show = "<empty>"
            elif plen <= 16 and all(b == 0 or 32 <= b < 127 for b in pval if True):
                # try string
                if b"\x00" in pval and all(32 <= c < 127 or c == 0 for c in pval):
                    show = pval.split(b"\x00")[0].decode()
                else:
                    show = " ".join(f"{x:08x}" for x in struct.unpack(">%dI" % (plen // 4), pval[: plen - (plen % 4)])) if plen >= 4 else pval.hex()
            elif plen >= 4 and plen % 4 == 0 and plen <= 32:
                show = " ".join(f"{x:08x}" for x in struct.unpack(">%dI" % (plen // 4), pval))
            elif b"\x00" in pval[:64] and sum(1 for c in pval[:32] if 32 <= c < 127) > 4:
                show = pval.split(b"\x00")[0].decode("ascii", "replace")[:80]
            else:
                show = pval[:24].hex() + ("..." if plen > 24 else "")
            print(f"{pth}:{pname} = {show}")
        continue
    if token == FDT_NOP:
        continue
    if token == FDT_END:
        break
    print("unknown token", token, "at", pos)
    break
