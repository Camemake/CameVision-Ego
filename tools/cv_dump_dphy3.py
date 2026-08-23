#!/usr/bin/env python3
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings
from patch_boot_usb import find

BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\camevision_boot_ego.img")
data = BOOT.read_bytes()
fit = build(Fdt(data))
img = find(fit, "/images/fdt")
pos = struct.unpack(">I", img.get("data-position"))[0]
size = struct.unpack(">I", img.get("data-size"))[0]
tree = build(Fdt(data[pos:pos+size]))

def dump(n, indent=0):
    pad = "  " * indent
    print(f"{pad}{n.path()}")
    for k, v in n.props:
        s = printable_strings(v)
        if s:
            print(f"{pad}  {k} = {s}")
        elif k == "phandle" and len(v) == 4:
            print(f"{pad}  {k} = <{struct.unpack('>I', v)[0]:#x}>")
        elif v and len(v) % 4 == 0:
            cells = " ".join(f"{c:#x}" for c in struct.unpack(f">{len(v)//4}I", v))
            print(f"{pad}  {k} = <{cells}>")
    for c in n.children:
        dump(c, indent + 1)

for p in ("/csi2-dphy3", "/csi2-dphy2", "/rkcif-mipi-lvds2", "/rkisp-vir2"):
    try:
        dump(find(tree, p))
    except Exception as e:
        print(p, e)
    print()
