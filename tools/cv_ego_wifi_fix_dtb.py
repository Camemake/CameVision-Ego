#!/usr/bin/env python3
"""Patch Recovery 5 FIT for Ego VS6621: Single pwrseq + Ego INT/wake pads.

Hardware is verified. Use the same mmc-pwrseq and mmc host as working
Single: GPIO3_B2 ACTIVE_HIGH, no vqmmc (host UHS stays 3.3 V mode).
Move BT off B2 so it cannot drive the FET. Keep WIFI_INT on A16
(GPIO3_B7) pull-up and HOST_WAKE on B16 output-high.

Does not flash. USB stays ADB.
"""
from __future__ import annotations

import hashlib
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, build, printable_strings  # noqa: E402
from patch_boot_ego import sprop, u32  # noqa: E402
from patch_boot_usb import (  # noqa: E402
    del_prop,
    find,
    set_prop,
    prop_offsets,
    resource_dtb_slot,
    serialize,
    read_mem_rsvmap,
)

from cv_ego_paths import repo_root  # noqa: E402

ROOT = repo_root()
SRC = ROOT / "restore" / "recovery-5-20260823-imaging-adb" / "camevision_boot_ego.img"
DST = ROOT / "build" / "camevision_boot_ego.img"
GPIO3 = 0xB9
PCFG_PULL_NONE = 0xEC
PCFG_PULL_UP = 0xEE
PCFG_OUT_HIGH = 0xF7
MODULE = "camevision-sc233hgs"
_NAME_MAP = (
    ("efference-sc233hgs", MODULE),
    ("Efference-sc233hgs", MODULE),
    ("spi0m0-efference-imu-pins", "spi0m0-imu-pins"),
    ("spi0m0-efference-csn0-pins", "spi0m0-csn0-pins"),
    ("efference,m1", "camevision,ego"),
    ("Efference M1", "CameVision Ego"),
    ("Efference", "CameVision"),
    ("efference", "camevision"),
    ("EFFERENCE", "CAMEVISION"),
)


def cells(v: bytes) -> tuple[int, ...]:
    return struct.unpack(f">{len(v) // 4}I", v)


def _scrub_text(text: str) -> str:
    out = text
    for old, new in _NAME_MAP:
        out = out.replace(old, new)
    return out


def _scrub_module_name(tree) -> None:
    for node in list(tree.walk()):
        if "efference" in node.name.lower():
            old = node.name
            node.name = _scrub_text(node.name)
            print(f"  node {old} -> {node.name}")
        for i, (key, val) in enumerate(node.props):
            if key == "rockchip,camera-module-name":
                node.props[i] = (key, sprop(MODULE))
                print(f"  {node.path()}: {key} -> {MODULE}")
                continue
            if not isinstance(val, (bytes, bytearray)):
                continue
            if b"efference" not in bytes(val).lower():
                continue
            texts = printable_strings(val)
            if texts:
                new_texts = [_scrub_text(t) for t in texts]
                node.props[i] = (
                    key,
                    b"".join(t.encode("ascii") + b"\x00" for t in new_texts),
                )
                print(f"  {node.path()}: {key} {texts} -> {new_texts}")
                continue
            raw = bytes(val)
            for old, new in _NAME_MAP:
                raw = raw.replace(old.encode("ascii"), new.encode("ascii"))
            node.props[i] = (key, raw)
            print(f"  {node.path()}: {key} raw scrub")
    names = []
    for node in tree.walk():
        val = node.get("rockchip,camera-module-name")
        if val is not None:
            names.extend(printable_strings(val))
    if names and any(n != MODULE for n in names):
        raise SystemExit(f"camera-module-name still {names}")
    if not names:
        raise SystemExit("no camera-module-name after scrub")


def patch_dtb(blob: bytes) -> bytes:
    data = bytearray(blob)
    fdt = Fdt(bytes(data))
    offs = prop_offsets(fdt)
    rst_off, rst_len = offs[("/sdio-pwrseq", "reset-gpios")]
    if rst_len != 12:
        raise SystemExit(f"reset-gpios length {rst_len}")
    rst = cells(bytes(data[rst_off : rst_off + 12]))
    if rst[0] != GPIO3:
        raise SystemExit(f"reset-gpios unexpected {rst}")
    # Same as working Single: B2 ACTIVE_HIGH so deassert is low (run / FET on).
    data[rst_off : rst_off + 12] = struct.pack(">3I", GPIO3, 10, 0)

    bt_off, bt_len = offs[("/wireless-bluetooth", "BT,power_gpio")]
    if bt_len != 12:
        raise SystemExit(f"BT,power_gpio length {bt_len}")
    bt = cells(bytes(data[bt_off : bt_off + 12]))
    if bt[0] != GPIO3:
        raise SystemExit(f"BT,power_gpio unexpected {bt}")
    data[bt_off : bt_off + 12] = struct.pack(">3I", GPIO3, 7, 0)

    delay_off, delay_len = offs[("/sdio-pwrseq", "post-power-on-delay-ms")]
    if delay_len != 4:
        raise SystemExit(f"post-power-on-delay-ms length {delay_len}")
    delay_old = cells(bytes(data[delay_off : delay_off + 4]))[0]
    # 200 ms high (ACTIVE_HIGH assert) then deassert low, then CMD5.
    data[delay_off : delay_off + 4] = struct.pack(">I", 200)

    tree = build(Fdt(bytes(data)))
    wake_irq = find(tree, "/wireless-wlan")
    for i, (k, v) in enumerate(wake_irq.props):
        if k == "WIFI,host_wake_irq":
            # A16 GPIO3_B7, not Single 1AC18 GPIO2_A5. Input IRQ, active-high.
            wake_irq.props[i] = (k, u32(GPIO3, 15, 0))
    wake_pin = find(tree, "/pinctrl/wireless-wlan/wifi-wake-host")
    for i, (k, v) in enumerate(wake_pin.props):
        if k == "rockchip,pins":
            wake_pin.props[i] = (k, u32(3, 15, 0, PCFG_PULL_UP))
    pw_node = find(tree, "/pinctrl/wireless-wlan/wifi-soc-pwctl")
    for i, (k, v) in enumerate(pw_node.props):
        if k == "rockchip,pins":
            pw_node.props[i] = (k, u32(3, 14, 0, PCFG_OUT_HIGH))
    mmc = find(tree, "/mmc@21f60000")
    mmc.props = [(k, v) for (k, v) in mmc.props if k != "vqmmc-supply"]
    if find(tree, "/wireless-wlan").get("WIFI,poweren_gpio") is not None:
        del_prop(tree, "/wireless-wlan", "WIFI,poweren_gpio")
    rst2 = cells(find(tree, "/sdio-pwrseq").get("reset-gpios"))
    en = cells(find(tree, "/pinctrl/sdio-pwrseq/wifi-enable-h").get("rockchip,pins"))
    pins = cells(find(tree, "/pinctrl/wireless-wlan/wifi-soc-pwctl").get("rockchip,pins"))
    wake = cells(find(tree, "/wireless-wlan").get("WIFI,host_wake_irq"))
    wake_p = cells(find(tree, "/pinctrl/wireless-wlan/wifi-wake-host").get("rockchip,pins"))
    if find(tree, "/mmc@21f60000").get("vqmmc-supply") is not None:
        raise SystemExit("vqmmc-supply still present")
    if rst2 != (GPIO3, 10, 0):
        raise SystemExit(f"verify reset-gpios {rst2}")
    if en[:3] != (3, 10, 0):
        raise SystemExit(f"verify wifi-enable-h {en}")
    if pins != (3, 14, 0, PCFG_OUT_HIGH):
        raise SystemExit(f"verify wifi-soc-pwctl {pins}")
    if wake != (GPIO3, 15, 0):
        raise SystemExit(f"verify WIFI,host_wake_irq {wake}")
    if wake_p != (3, 15, 0, PCFG_PULL_UP):
        raise SystemExit(f"verify wifi-wake-host {wake_p}")
    bt2 = cells(find(tree, "/wireless-bluetooth").get("BT,power_gpio"))
    if bt2 != (GPIO3, 7, 0):
        raise SystemExit(f"verify BT,power_gpio {bt2}")

    # U5 RV-3028 V_BKUP = +VBAT_RTC, C99 11 mF. Trickle must be on or a
    # power cut returns the clock to 1970.
    rtc_path = "/i2c@20800000/rtc@52"
    set_prop(tree, rtc_path, "trickle-resistor-ohms", u32(3000))
    set_prop(tree, rtc_path, "backup-switchover-mode", u32(1))
    rtc = find(tree, rtc_path)
    ohms = cells(rtc.get("trickle-resistor-ohms") or b"")
    bsm = cells(rtc.get("backup-switchover-mode") or b"")
    if ohms != (3000,) or bsm != (1,):
        raise SystemExit(f"verify rtc trickle {ohms} bsm {bsm}")

    gpio3 = find(tree, "/pinctrl/gpio@21e00000")
    if any(c.name == "wifi-rst-hog" for c in gpio3.children):
        raise SystemExit("wifi-rst-hog still present")
    if printable_strings(find(tree, "/").get("model")) != ["CameVision Ego"]:
        raise SystemExit("model lost")
    usb = find(tree, "/usb@21500000")
    if printable_strings(usb.get("dr_mode")) != ["peripheral"]:
        raise SystemExit("USB dr_mode lost")
    _scrub_module_name(tree)
    out = serialize(tree, read_mem_rsvmap(Fdt(bytes(data))), Fdt(bytes(data)).boot_cpuid_phys)
    if b"efference" in out.lower():
        raise SystemExit("efference still present in DTB")
    delay2 = cells(find(tree, "/sdio-pwrseq").get("post-power-on-delay-ms"))[0]
    if delay2 != 200:
        raise SystemExit(f"verify post-power-on-delay-ms {delay2}")
    print(f"  reset-gpios {rst} -> {rst2} (GPIO3_B2 ACTIVE_HIGH, same as Single)")
    print(f"  post-power-on-delay-ms {delay_old} -> {delay2} ms (B2 high pulse, then low, then CMD5)")
    print(f"  wifi-enable-h {en} (B2 GPIO)")
    print("  vqmmc-supply stripped (match Single host UHS 3.3 V mode)")
    print(f"  WIFI,host_wake_irq {wake} (GPIO3_B7 A16, not GPIO2_A5)")
    print(f"  wifi-wake-host {wake_p} (B7 input pull-up)")
    print(f"  wifi-soc-pwctl {pins} (B6 HOST_WAKE output-high)")
    print(f"  BT,power_gpio {bt} -> {bt2} (GPIO3_A7)")
    print(f"  dtb {len(data)} -> {len(out)}")
    return out


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DST
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
    new = patch_dtb(old)
    print(f"src {src} fdt {size} bytes -> {len(new)}")
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
    new_res = new if old_res == old else patch_dtb(old_res)
    if len(new_res) > res_slot:
        raise SystemExit(f"resource dtb {len(new_res)} > slot {res_slot}")
    raw[rpos + start : rpos + start + res_slot] = new_res + b"\x00" * (res_slot - len(new_res))
    struct.pack_into("<I", raw, rpos + entry_off + 264, len(new_res))
    new_entry = hashlib.sha1(new_res).digest() if hash_size == 20 else hashlib.sha256(new_res).digest()
    raw[rpos + entry_off + 224 : rpos + entry_off + 224 + hash_size] = new_entry
    rhash_off, _ = foff[("/images/resource/hash", "value")]
    raw[rhash_off : rhash_off + 32] = hashlib.sha256(bytes(raw[rpos : rpos + rsize])).digest()

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.resolve() != src.resolve():
        shutil.copy2(src, dst.with_suffix(".img.bak")) if False else None
    dst.write_bytes(bytes(raw))
    if b"efference" in bytes(raw[pos:pos + len(new)]).lower():
        raise SystemExit("efference still present in FIT fdt")
    for extra in (
        ROOT / "restore" / "release-0.2-20260902" / "camevision_boot_ego.img",
        ROOT / "restore" / "updates" / "current" / "camevision_boot_ego.img",
    ):
        if extra.parent.is_dir() and dst.resolve() != extra.resolve():
            extra.write_bytes(bytes(raw))
            print(f"wrote {extra} ({len(raw)} bytes)")
    print(f"wrote {dst} ({len(raw)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
