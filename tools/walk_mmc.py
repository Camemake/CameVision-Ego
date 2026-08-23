#!/usr/bin/env python3
from pathlib import Path
import struct
blob = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\boot.img").read_bytes()[0x800:0x800+182352]
FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_END = 1, 2, 3, 9
off_dt_struct = struct.unpack(">I", blob[8:12])[0]
off_dt_strings = struct.unpack(">I", blob[12:16])[0]
size_dt_struct = struct.unpack(">I", blob[36:40])[0]
def align4(x): return (x+3)&~3
def get_str(off):
    end = blob.find(b"\x00", off_dt_strings+off)
    return blob[off_dt_strings+off:end].decode()
pos = off_dt_struct
path=[]
while pos < off_dt_struct+size_dt_struct:
    token=struct.unpack_from(">I", blob, pos)[0]; pos+=4
    if token==FDT_BEGIN_NODE:
        end=blob.find(b"\x00", pos); name=blob[pos:end].decode(); pos=align4(end+1); path.append(name)
        pth="/".join(path)
        if "mmc" in pth.lower() or pth.endswith("spi@") or "spi@" in pth:
            print("NODE", pth)
        continue
    if token==FDT_END_NODE:
        path.pop() if path else None; continue
    if token==FDT_PROP:
        plen,nameoff=struct.unpack_from(">II", blob, pos); pos+=8
        pname=get_str(nameoff); pval=blob[pos:pos+plen]; pos=align4(pos+plen)
        pth="/".join(path)
        if ("mmc" in pth.lower() or "spi@" in pth) and pname in ("status","compatible","cd-gpios","wp-gpios","pinctrl-0","non-removable","bus-width","num-cs"):
            if plen>=4 and plen%4==0 and plen<=16:
                show=" ".join(f"{x:08x}" for x in struct.unpack(">%dI"%(plen//4), pval))
            else:
                show=pval.split(b"\x00")[0].decode(errors="replace") if pval else ""
            print(f"  {pth}:{pname} = {show}")
        continue
    if token==FDT_END: break
