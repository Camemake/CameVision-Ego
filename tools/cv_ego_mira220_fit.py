#!/usr/bin/env python3
"""Patch V0.2 Ego boot FIT so both cameras are MIRA220.

Keeps node names (sc233hgs@30) so phandles stay put. Changes compatible,
I2C address, lanes and module name. Also retargets microSD U6 to 3.3 V
(schematic V0.3 +3.3V_SDC_PWR). Writes a new image only — does not
touch the frozen SC233HGS kit.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_ego import sprop, u32  # noqa: E402
from patch_boot_usb import (  # noqa: E402
    find,
    prop_offsets,
    read_mem_rsvmap,
    resource_dtb_slot,
    serialize,
    set_prop,
)

from cv_ego_paths import release_02, repo_root  # noqa: E402

ROOT = repo_root()
SRC = release_02() / "camevision_boot_ego.img"
DST = ROOT / "restore" / "mira220-bringup" / "camevision_boot_mira220.img"
MODULE = "camevision-mira220"


def cells(v: bytes | None) -> tuple[int, ...]:
    if not v:
        return ()
    return struct.unpack(f">{len(v) // 4}I", v)


def vcc3v3_sys_phandle(tree) -> bytes:
    for node in tree.walk():
        names = printable_strings(node.get("regulator-name") or b"") or []
        if "vcc3v3_sys" in names:
            ph = node.get("phandle")
            if ph:
                return ph
    raise SystemExit("vcc3v3_sys phandle missing")


def patch_sd_3v3(tree) -> None:
    """Keep /vcc1v8-sd node+phandle; rail is 3.3 V on this board now."""
    find(tree, "/vcc1v8-sd")
    ph = vcc3v3_sys_phandle(tree)
    set_prop(tree, "/vcc1v8-sd", "regulator-name", sprop("vcc3v3_sd"))
    set_prop(tree, "/vcc1v8-sd", "regulator-min-microvolt", u32(3_300_000))
    set_prop(tree, "/vcc1v8-sd", "regulator-max-microvolt", u32(3_300_000))
    set_prop(tree, "/vcc1v8-sd", "startup-delay-us", u32(100_000))
    set_prop(tree, "/vcc1v8-sd", "regulator-always-on", b"")
    set_prop(tree, "/vcc1v8-sd", "regulator-boot-on", b"")
    set_prop(tree, "/vcc1v8-sd", "vin-supply", ph)
    sd_ph = find(tree, "/vcc1v8-sd").get("phandle")
    set_prop(tree, "/mmc@21d60000", "vmmc-supply", sd_ph)
    set_prop(tree, "/mmc@21d60000", "vqmmc-supply", ph)
    print("  sdmmc0 vmmc=vcc3v3_sd 3.3V vqmmc=vcc3v3_sys")


def patch_dtb(blob: bytes) -> bytes:
    tree = build(Fdt(blob))
    sensors = [n for n in tree.walk() if n.name == "sc233hgs@30"]
    if len(sensors) < 1:
        raise SystemExit("no sc233hgs@30 nodes")
    for node in sensors:
        path = node.path()
        set_prop(tree, path, "compatible", b"ams,mira220\x00camevision,mira220\x00")
        set_prop(tree, path, "reg", u32(0x54))
        set_prop(tree, path, "rockchip,camera-module-name", sprop(MODULE))
        ep = None
        for child in node.children:
            if child.name == "port":
                for g in child.children:
                    if g.name == "endpoint" or g.name.startswith("endpoint"):
                        ep = g
        if ep is None:
            raise SystemExit(f"no endpoint under {path}")
        set_prop(tree, ep.path(), "data-lanes", u32(1, 2))
        print(f"  {path} -> ams,mira220 reg=0x54 lanes=2 {MODULE}")

    cam1 = find(tree, "/i2c-gpio-cam1")
    sda = list(cells(cam1.get("sda-gpios")))
    scl = list(cells(cam1.get("scl-gpios")))
    if len(sda) < 3 or len(scl) < 3:
        raise SystemExit(f"i2c-gpio-cam1 gpios sda={sda} scl={scl}")
    # This board ACKs at 0x54 with SDA=GPIO4_A6, SCL=GPIO4_A7.
    sda[1], scl[1] = 6, 7
    set_prop(tree, "/i2c-gpio-cam1", "sda-gpios", u32(*sda))
    set_prop(tree, "/i2c-gpio-cam1", "scl-gpios", u32(*scl))
    print(f"  i2c-gpio-cam1 SDA=A{sda[1]} SCL=A{scl[1]}")

    chosen = find(tree, "/chosen")
    args = chosen.get("bootargs") or b""
    extra = b" initcall_blacklist=rockchip_csi2_dphy_driver_init,rkcif_csi2_plat_drv_init,rkcif_plat_init"
    if extra.strip() not in args:
        if args.endswith(b"\x00"):
            args = args[:-1] + extra + b"\x00"
        else:
            args = args + extra + b"\x00"
        set_prop(tree, "/chosen", "bootargs", args)
        print("  bootargs + initcall_blacklist rkcif/dphy/csi2")

    for node in tree.walk():
        val = node.get("data-lanes")
        if val is None:
            continue
        if cells(val) == (1, 2, 3, 4):
            set_prop(tree, node.path(), "data-lanes", u32(1, 2))
            print(f"  {node.path()}: data-lanes 1 2 3 4 -> 1 2")

    names = []
    for node in tree.walk():
        val = node.get("rockchip,camera-module-name")
        if val is not None:
            names.extend(printable_strings(val))
    if not names or any(n != MODULE for n in names):
        raise SystemExit(f"module-name after patch: {names}")
    if printable_strings(find(tree, "/").get("model")) != ["CameVision Ego"]:
        raise SystemExit("model lost")
    usb = find(tree, "/usb@21500000")
    if printable_strings(usb.get("dr_mode")) != ["peripheral"]:
        raise SystemExit("USB dr_mode lost")
    patch_sd_3v3(tree)
    out = serialize(tree, read_mem_rsvmap(Fdt(blob)), Fdt(blob).boot_cpuid_phys)
    print(f"  dtb {len(blob)} -> {len(out)}")
    return out


def patch_dtb_sd_only(blob: bytes) -> bytes:
    tree = build(Fdt(blob))
    if printable_strings(find(tree, "/").get("model")) != ["CameVision Ego"]:
        raise SystemExit("model lost")
    usb = find(tree, "/usb@21500000")
    if printable_strings(usb.get("dr_mode")) != ["peripheral"]:
        raise SystemExit("USB dr_mode lost")
    patch_sd_3v3(tree)
    name = printable_strings(find(tree, "/vcc1v8-sd").get("regulator-name"))
    if name != ["vcc3v3_sd"]:
        raise SystemExit(f"sd regulator-name {name}")
    vmin = cells(find(tree, "/vcc1v8-sd").get("regulator-min-microvolt"))
    if vmin != (3_300_000,):
        raise SystemExit(f"sd min {vmin}")
    out = serialize(tree, read_mem_rsvmap(Fdt(blob)), Fdt(blob).boot_cpuid_phys)
    print(f"  dtb {len(blob)} -> {len(out)}")
    return out


def rewrite_fit(src: Path, dst: Path, patcher) -> None:
    raw = bytearray(src.read_bytes())
    fit = Fdt(bytes(raw))
    fit_root = build(fit)
    foff = prop_offsets(fit)
    img = find(fit_root, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    old = bytes(raw[pos : pos + size])
    stored = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            stored = c.get("value")
    if hashlib.sha256(old).digest() != stored:
        raise SystemExit("FIT fdt hash mismatch")
    new = patcher(old)
    next_pos = len(raw)
    for n in fit_root.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    slot = next_pos - pos
    if len(new) > slot:
        raise SystemExit(f"new dtb {len(new)} > slot {slot}")
    raw[pos:next_pos] = new + b"\x00" * (slot - len(new))
    soff, _ = foff[("/images/fdt", "data-size")]
    struct.pack_into(">I", raw, soff, len(new))
    hoff, _ = foff[("/images/fdt/hash", "value")]
    raw[hoff : hoff + 32] = hashlib.sha256(new).digest()

    rpos = struct.unpack_from(">I", raw, foff[("/images/resource", "data-position")][0])[0]
    rsize = struct.unpack_from(">I", raw, foff[("/images/resource", "data-size")][0])[0]
    blob = bytes(raw[rpos : rpos + rsize])
    start, f_size, res_slot, entry_off, hash_size = resource_dtb_slot(blob)
    old_res = bytes(raw[rpos + start : rpos + start + f_size])
    new_res = new if old_res == old else patcher(old_res)
    if len(new_res) > res_slot:
        raise SystemExit(f"resource dtb {len(new_res)} > slot {res_slot}")
    raw[rpos + start : rpos + start + res_slot] = new_res + b"\x00" * (res_slot - len(new_res))
    struct.pack_into("<I", raw, rpos + entry_off + 264, len(new_res))
    new_entry = hashlib.sha1(new_res).digest() if hash_size == 20 else hashlib.sha256(new_res).digest()
    raw[rpos + entry_off + 224 : rpos + entry_off + 224 + hash_size] = new_entry
    rhash_off, _ = foff[("/images/resource/hash", "value")]
    raw[rhash_off : rhash_off + 32] = hashlib.sha256(bytes(raw[rpos : rpos + rsize])).digest()

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(raw))
    print(f"wrote {dst} ({len(raw)} bytes)")


def patch_fit(src: Path, dst: Path) -> None:
    rewrite_fit(src, dst, patch_dtb)


def patch_fit_sd_only(src: Path, dst: Path) -> None:
    rewrite_fit(src, dst, patch_dtb_sd_only)


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DST
    if not src.is_file():
        raise SystemExit(f"missing {src}")
    print(f"src {src}")
    patch_fit(src, dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
