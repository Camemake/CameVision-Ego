#!/usr/bin/env python3
"""Compile the CameVision Ego board DTB into a flashable boot.img.

There is no host dtc + rv1126b.dtsi here, so this retargets the proven
Recovery 3 FIT DTB (wifi+IMU Single tree) to the Ego schematic pin map
and serializes it back into the FIT + resource rk-kernel.dtb slots.

Does not flash. USB stays peripheral / ADB.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dtb_decompile import Fdt, Node, build, printable_strings  # noqa: E402
from patch_boot_usb import (  # noqa: E402
    find,
    prop_offsets,
    read_mem_rsvmap,
    serialize,
    set_prop,
)

SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\restore\recovery-3-20260822-uvc-wifi-rkaiq\camevision_boot_wifi_imu.img"
)
DST = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\camevision_boot_ego.img")
DTB_OUT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\device-tree\rv1126b-camevision-ego.dtb")
BOOT_PART = 0x5800 * 512

# Live phandles we must keep.
CRU = 0x2
GPIO0 = 0x95
GPIO3 = 0xB9
GPIO4 = 0x9C
GPIO2 = 0xFC
VCC_3V3 = 0xBB
VCC_1V8 = 0xBC
AVDD = 0x9D
DOVDD = 0x9E
DVDD = 0x9F
CAM0_CLK_PINS = 0xA0
CAM0_EP = 0x16
DPHY0_IN = 0xA1
ISP_HW = 0x34
DVBM = 0x35
CIF_HW = 0x2C
VPSS_HW = 0x41
LVDS1 = 0x31
LVDS2 = 0x32
ISP1 = 0x39
ISP2 = 0x3B
MIPI0_HW = (0x21, 0x22, 0x23, 0x24)
DPHY_HW = (0x14, 0x15)
PCFG_PULL_NONE = 0xEC
PCFG_PULL_DOWN = 0xED
PCFG_PULL_UP = 0xEE
PCFG_I2C = 0xF1
PCFG_SPI = 0xF5
PCFG_OUT_HIGH = 0xF7
SDMMC0_CLK = 0xD0
SDMMC0_CMD = 0xD1
SDMMC0_DETN = 0xD2
SDMMC0_BUS4 = 0xD3
SDMMC0_IDLE = 0xD4
CLK_CAM0 = 0x6D  # CLK_MIPI0_OUT2IO
CLK_CAM1 = 0x6E  # CLK_MIPI1_OUT2IO
LINK_FREQ = (0x0, 0x1017DF80, 0x0, 0x1823CF40)


def u32(*cells: int) -> bytes:
    return struct.pack(f">{len(cells)}I", *cells)


def sprop(text: str) -> bytes:
    return text.encode("ascii") + b"\x00"


def empty() -> bytes:
    return b""


def set_cells(node: Node, name: str, cells: list[int]) -> None:
    raw = u32(*cells)
    for i, (k, v) in enumerate(node.props):
        if k == name:
            node.props[i] = (name, raw)
            print(f"  {node.path()}: {name} updated")
            return
    node.props.append((name, raw))
    print(f"  {node.path()}: {name} added")


def set_bytes(node: Node, name: str, value: bytes) -> None:
    for i, (k, _) in enumerate(node.props):
        if k == name:
            node.props[i] = (name, value)
            print(f"  {node.path()}: {name} updated")
            return
    node.props.append((name, value))
    print(f"  {node.path()}: {name} added")


def ensure_empty(node: Node, name: str) -> None:
    if node.get(name) is None:
        node.props.append((name, b""))
        print(f"  {node.path()}: {name} added (empty)")


def add_phandle(node: Node, ph: int) -> None:
    set_cells(node, "phandle", [ph])


def max_phandle(root: Node) -> int:
    m = 0
    for n in root.walk():
        v = n.get("phandle")
        if v and len(v) == 4:
            m = max(m, struct.unpack(">I", v)[0])
    return m


def clone_node(src: Node, name: str | None = None) -> Node:
    n = Node(name or src.name)
    n.props = [(k, bytes(v)) for k, v in src.props]
    for c in src.children:
        ch = clone_node(c)
        ch.parent = n
        n.children.append(ch)
    return n


def add_child(parent: Node, child: Node, after: str | None = None) -> Node:
    child.parent = parent
    if after is None:
        parent.children.append(child)
        return child
    for i, c in enumerate(parent.children):
        if c.name == after:
            parent.children.insert(i + 1, child)
            return child
    parent.children.append(child)
    return child


def pins(parent: Node, name: str, cells: list[int], ph: int) -> Node:
    n = Node(name, parent)
    n.props = [("rockchip,pins", u32(*cells)), ("phandle", u32(ph))]
    parent.children.append(n)
    return n


def endpoint(name: str, ph: int, remote: int, extra: list[tuple[str, bytes]] | None = None) -> Node:
    n = Node(name)
    n.props = [("remote-endpoint", u32(remote)), ("phandle", u32(ph))]
    if extra:
        # keep remote/phandle last-ish; extras first is fine
        n.props = extra + n.props
    return n


def port_with(name: str, child: Node, extra: list[tuple[str, bytes]] | None = None) -> Node:
    n = Node(name)
    if extra:
        n.props = list(extra)
    add_child(n, child)
    return n


class Ph:
    def __init__(self, start: int) -> None:
        self.n = start

    def get(self) -> int:
        v = self.n
        self.n += 1
        return v


def align512(n: int) -> int:
    return (n + 511) & ~511


def patch_tree(root: Node) -> None:
    ph = Ph(max_phandle(root) + 1)
    print(f"phandles start at {ph.n:#x}")

    gpio5_ph = ph.get()
    gpio6_ph = ph.get()
    i2c4m2_ph = ph.get()
    cam1_clk_ph = ph.get()
    spi0m2_clk_ph = ph.get()
    spi0m2_cs_ph = ph.get()
    sd_cd_ph = ph.get()
    sd_pwr_ph = ph.get()
    imu0_int_ph = ph.get()
    vcc15_ph = ph.get()
    vcc18sd_ph = ph.get()
    cam1_ep = ph.get()
    dphy1_in = ph.get()
    dphy1_out = ph.get()
    mipi1_in = ph.get()
    mipi1_out = ph.get()
    cif1_in = ph.get()
    lvds1_sd = ph.get()
    isp1_ep = ph.get()
    isp1_sd = ph.get()
    vpss1_in = ph.get()

    # --- identity ---
    set_bytes(find(root, "/"), "model", sprop("CameVision Ego"))
    set_bytes(
        find(root, "/"),
        "compatible",
        b"camemake,camevision-ego\x00rockchip,rv1126b\x00",
    )

    # --- gpio banks used by Ego IMU / SD ---
    add_phandle(find(root, "/pinctrl/gpio@21900000"), gpio5_ph)  # gpio5
    add_phandle(find(root, "/pinctrl/gpio@21a00000"), gpio6_ph)  # gpio6

    # --- pinctrl groups ---
    pins(
        find(root, "/pinctrl/i2c4"),
        "i2c4m2-pins",
        [4, 7, 6, PCFG_I2C, 4, 6, 6, PCFG_I2C],
        i2c4m2_ph,
    )
    cam_clk1 = Node("cam_clk1")
    pins(cam_clk1, "cam-clk1-pins", [4, 8, 3, PCFG_PULL_NONE], cam1_clk_ph)
    add_child(find(root, "/pinctrl"), cam_clk1, after="cam_clk0")
    pins(
        find(root, "/pinctrl/spi0"),
        "spi0m2-clk-pins",
        [5, 6, 2, PCFG_SPI, 5, 5, 2, PCFG_SPI, 5, 4, 2, PCFG_SPI],
        spi0m2_clk_ph,
    )
    pins(find(root, "/pinctrl/spi0"), "spi0m2-csn0-pins", [5, 3, 2, PCFG_SPI], spi0m2_cs_ph)
    pins(find(root, "/pinctrl/imu"), "imu0-int1", [5, 9, 0, PCFG_PULL_NONE], imu0_int_ph)
    # IMU1 INT1 is GPIO6_B5 (was Single GPIO3_B4, which is now SD PWREN)
    set_cells(find(root, "/pinctrl/imu/imu-int1"), "rockchip,pins", [6, 13, 0, PCFG_PULL_NONE])
    sd_grp = Node("sd-card")
    pins(sd_grp, "sd-cd-pins", [3, 11, 0, PCFG_PULL_UP], sd_cd_ph)
    pins(sd_grp, "sd-pwren", [3, 12, 0, PCFG_OUT_HIGH], sd_pwr_ph)
    add_child(find(root, "/pinctrl"), sd_grp)

    set_cells(find(root, "/pinctrl/wireless-wlan/wifi-wake-host"), "rockchip,pins", [3, 15, 0, PCFG_PULL_UP])
    set_cells(find(root, "/pinctrl/wireless-wlan/wifi-soc-pwctl"), "rockchip,pins", [3, 14, 0, PCFG_PULL_DOWN])

    # --- camera LDOs: enable the three Ego GPIOs; DVDD is 1.2 V not 1.5 V ---
    avdd = find(root, "/sc233hgs-avdd")
    set_cells(avdd, "gpio", [GPIO0, 8, 0])  # GPIO0_B0
    ensure_empty(avdd, "enable-active-high")
    dvdd = find(root, "/sc233hgs-dvdd")
    set_cells(dvdd, "regulator-min-microvolt", [1_200_000])
    set_cells(dvdd, "regulator-max-microvolt", [1_200_000])
    set_cells(dvdd, "gpio", [GPIO0, 10, 0])  # GPIO0_B2
    ensure_empty(dvdd, "enable-active-high")

    vcc15 = Node("vcc1v5-cam")
    vcc15.props = [
        ("compatible", sprop("regulator-fixed")),
        ("regulator-name", sprop("vcc1v5_cam")),
        ("regulator-min-microvolt", u32(1_500_000)),
        ("regulator-max-microvolt", u32(1_500_000)),
        ("regulator-always-on", empty()),
        ("regulator-boot-on", empty()),
        ("gpio", u32(GPIO0, 9, 0)),  # GPIO0_B1
        ("enable-active-high", empty()),
        ("vin-supply", u32(VCC_3V3)),
        ("phandle", u32(vcc15_ph)),
    ]
    add_child(root, vcc15, after="sc233hgs-dvdd")

    vcc18sd = Node("vcc1v8-sd")
    vcc18sd.props = [
        ("compatible", sprop("regulator-fixed")),
        ("regulator-name", sprop("vcc1v8_sd")),
        ("regulator-min-microvolt", u32(1_800_000)),
        ("regulator-max-microvolt", u32(1_800_000)),
        ("gpio", u32(GPIO3, 12, 0)),  # GPIO3_B4 PWREN
        ("enable-active-high", empty()),
        ("startup-delay-us", u32(20_000)),
        ("pinctrl-names", sprop("default")),
        ("pinctrl-0", u32(sd_pwr_ph)),
        ("vin-supply", u32(VCC_1V8)),
        ("phandle", u32(vcc18sd_ph)),
    ]
    add_child(root, vcc18sd, after="vcc1v5-cam")

    # --- Cam 0: PWDN is GPIO4_A3, not GPIO4_A6 ---
    cam0 = find(root, "/i2c@21120000/sc233hgs@30")
    set_cells(cam0, "reset-gpios", [GPIO4, 3, 1])
    set_bytes(cam0, "rockchip,camera-module-facing", sprop("back"))

    # --- Cam 1 I2C: schematic nets are swapped vs I2C4_M2 ---
    # U1.1T21 GPIO4_A6 = I2C4_SDA_M2, but net is I2C4_SCL_CAM -> U10.A3 SCL
    # U1.1T22 GPIO4_A7 = I2C4_SCL_M2, but net is I2C4_SDA_CAM -> U10.B3 SDA
    # Hardware I2C4 cannot swap those functions. Bit-bang the net names.
    i2c4 = find(root, "/i2c@21130000")
    set_bytes(i2c4, "status", sprop("disabled"))

    i2c_gpio = Node("i2c-gpio-cam1")
    i2c_gpio.props = [
        ("compatible", sprop("i2c-gpio")),
        ("sda-gpios", u32(GPIO4, 7, 0)),  # GPIO4_A7 / 1T22 / I2C4_SDA_CAM
        ("scl-gpios", u32(GPIO4, 6, 0)),  # GPIO4_A6 / 1T21 / I2C4_SCL_CAM
        ("i2c-gpio,delay-us", u32(2)),
        ("#address-cells", u32(1)),
        ("#size-cells", u32(0)),
    ]

    cam1 = Node("sc233hgs@30", i2c_gpio)
    cam1.props = [
        ("compatible", sprop("smartsens,sc233hgs")),
        ("reg", u32(0x30)),
        ("clocks", u32(CRU, CLK_CAM1)),
        ("clock-names", sprop("xvclk")),
        ("assigned-clocks", u32(CRU, CLK_CAM1)),
        ("assigned-clock-rates", u32(27_000_000)),
        ("reset-gpios", u32(GPIO4, 2, 1)),  # GPIO4_A2, deassert = high
        ("avdd-supply", u32(AVDD)),
        ("dovdd-supply", u32(DOVDD)),
        ("dvdd-supply", u32(DVDD)),
        ("pinctrl-names", b"rockchip,camera_default\x00rockchip,camera_sleep\x00"),
        ("pinctrl-0", u32(cam1_clk_ph)),
        ("pinctrl-1", u32(cam1_clk_ph)),
        ("rockchip,camera-module-index", u32(1)),
        ("rockchip,camera-module-facing", sprop("front")),
        ("rockchip,camera-module-name", sprop("efference-sc233hgs")),
        ("rockchip,camera-module-lens-name", sprop("default")),
    ]
    port = Node("port", cam1)
    ep = Node("endpoint", port)
    ep.props = [
        ("remote-endpoint", u32(dphy1_in)),
        ("data-lanes", u32(1, 2, 3, 4)),
        ("link-frequencies", u32(*LINK_FREQ)),
        ("phandle", u32(cam1_ep)),
    ]
    port.children.append(ep)
    cam1.children.append(port)
    i2c_gpio.children.append(cam1)
    add_child(root, i2c_gpio, after="i2c@21130000")
    print("  added /i2c-gpio-cam1/sc233hgs@30")

    # --- CSI1 pipeline: RX1 4-lane is csi2-dphy3, not dphy1 ---
    # dphy0 = CSI0 4-lane, dphy1/2 = CSI0 split, dphy3 = CSI1 4-lane.
    dphy1 = find(root, "/csi2-dphy3")
    set_bytes(dphy1, "status", sprop("okay"))
    ports = Node("ports", dphy1)
    ports.props = [("#address-cells", u32(1)), ("#size-cells", u32(0))]
    p0 = Node("port@0", ports)
    p0.props = [("reg", u32(0)), ("#address-cells", u32(1)), ("#size-cells", u32(0))]
    e_in = Node("endpoint@1", p0)
    e_in.props = [
        ("reg", u32(1)),
        ("remote-endpoint", u32(cam1_ep)),
        ("data-lanes", u32(1, 2, 3, 4)),
        ("link-frequencies", u32(*LINK_FREQ)),
        ("phandle", u32(dphy1_in)),
    ]
    p0.children.append(e_in)
    p1 = Node("port@1", ports)
    p1.props = [("reg", u32(1)), ("#address-cells", u32(1)), ("#size-cells", u32(0))]
    e_out = Node("endpoint@0", p1)
    e_out.props = [("reg", u32(0)), ("remote-endpoint", u32(mipi1_in)), ("phandle", u32(dphy1_out))]
    p1.children.append(e_out)
    ports.children.extend([p0, p1])
    dphy1.children.append(ports)

    # CSI host 1 only accepts PHY_SPLIT_23 (2-lane half of DPHY0).
    # Cam 1 is 4-lane on CSI RX1 / DPHY1, which pairs with CSI host 2.
    mipi1 = Node("mipi2-csi2")
    mipi1.props = [
        ("compatible", sprop("rockchip,rv1126b-mipi-csi2")),
        ("rockchip,hw", u32(*MIPI0_HW)),
        ("status", sprop("okay")),
    ]
    mports = Node("ports", mipi1)
    mports.props = [("#address-cells", u32(1)), ("#size-cells", u32(0))]
    mp0 = Node("port@0", mports)
    mp0.props = [("reg", u32(0)), ("#address-cells", u32(1)), ("#size-cells", u32(0))]
    me_in = Node("endpoint@1", mp0)
    me_in.props = [("reg", u32(1)), ("remote-endpoint", u32(dphy1_out)), ("phandle", u32(mipi1_in))]
    mp0.children.append(me_in)
    mp1 = Node("port@1", mports)
    mp1.props = [("reg", u32(1)), ("#address-cells", u32(1)), ("#size-cells", u32(0))]
    me_out = Node("endpoint@0", mp1)
    me_out.props = [("reg", u32(0)), ("remote-endpoint", u32(cif1_in)), ("phandle", u32(mipi1_out))]
    mp1.children.append(me_out)
    mports.children.extend([mp0, mp1])
    mipi1.children.append(mports)
    add_child(root, mipi1, after="mipi0-csi2")
    print("  added /mipi2-csi2 for CSI host 2 / DPHY3")

    lvds1 = find(root, "/rkcif-mipi-lvds2")
    set_bytes(lvds1, "status", sprop("okay"))
    lport = Node("port", lvds1)
    lep = Node("endpoint", lport)
    lep.props = [("remote-endpoint", u32(mipi1_out)), ("phandle", u32(cif1_in))]
    lport.children.append(lep)
    lvds1.children.append(lport)

    lvds1_sditf = Node("rkcif-mipi-lvds2-sditf")
    lvds1_sditf.props = [
        ("compatible", sprop("rockchip,rkcif-sditf")),
        ("rockchip,cif", u32(LVDS2)),
        ("status", sprop("okay")),
    ]
    sdp = Node("port", lvds1_sditf)
    sde = Node("endpoint", sdp)
    sde.props = [("remote-endpoint", u32(isp1_ep)), ("phandle", u32(lvds1_sd))]
    sdp.children.append(sde)
    lvds1_sditf.children.append(sdp)
    add_child(root, lvds1_sditf, after="rkcif-mipi-lvds-sditf")

    isp1 = find(root, "/rkisp-vir2")
    set_bytes(isp1, "status", sprop("okay"))
    iport = Node("port", isp1)
    iport.props = [("#address-cells", u32(1)), ("#size-cells", u32(0))]
    iep = Node("endpoint@0", iport)
    iep.props = [("reg", u32(0)), ("remote-endpoint", u32(lvds1_sd)), ("phandle", u32(isp1_ep))]
    iport.children.append(iep)
    isp1.children.append(iport)

    isp1_sditf = Node("rkisp-vir2-sditf")
    isp1_sditf.props = [
        ("compatible", sprop("rockchip,rkisp-sditf")),
        ("rockchip,isp", u32(ISP2)),
        ("status", sprop("okay")),
    ]
    isp = Node("port", isp1_sditf)
    ise = Node("endpoint", isp)
    ise.props = [("remote-endpoint", u32(vpss1_in)), ("phandle", u32(isp1_sd))]
    isp.children.append(ise)
    isp1_sditf.children.append(isp)
    add_child(root, isp1_sditf, after="rkisp-vir0-sditf")

    vpss1 = Node("rkvpss-vir1")
    vpss1.props = [
        ("compatible", sprop("rockchip,rkvpss-vir")),
        ("rockchip,hw", u32(VPSS_HW)),
        ("status", sprop("okay")),
    ]
    vport = Node("port", vpss1)
    vep = Node("endpoint", vport)
    vep.props = [("remote-endpoint", u32(isp1_sd)), ("phandle", u32(vpss1_in))]
    vport.children.append(vep)
    vpss1.children.append(vport)
    add_child(root, vpss1, after="rkvpss-vir0")
    print("  CSI1 pipeline: dphy3 -> mipi2-csi2 -> lvds2 -> isp-vir2 -> vpss-vir1")

    # --- IMU0 on SPI0_M2 ---
    spi0 = find(root, "/spi@211e0000")
    set_bytes(spi0, "status", sprop("okay"))
    set_cells(spi0, "pinctrl-0", [spi0m2_clk_ph, spi0m2_cs_ph])
    imu0 = clone_node(find(root, "/spi@211f0000/imu@0"), "imu@0")
    set_cells(imu0, "interrupt-parent", [gpio5_ph])
    set_cells(imu0, "interrupts", [9, 4])  # GPIO5_B1, LEVEL_HIGH
    set_cells(imu0, "pinctrl-0", [imu0_int_ph])
    add_child(spi0, imu0)
    print("  added /spi@211e0000/imu@0")

    imu1 = find(root, "/spi@211f0000/imu@0")
    set_cells(imu1, "interrupt-parent", [gpio6_ph])
    set_cells(imu1, "interrupts", [13, 4])  # GPIO6_B5

    # --- microSD on SDMMC0; do not claim GPIO0_A5 (green LED / stock detn) ---
    sd = find(root, "/mmc@21d60000")
    set_bytes(sd, "status", sprop("okay"))
    set_cells(sd, "pinctrl-0", [SDMMC0_CLK, SDMMC0_CMD, SDMMC0_BUS4, sd_cd_ph])
    set_cells(sd, "pinctrl-1", [SDMMC0_IDLE])
    set_cells(sd, "bus-width", [4])
    set_cells(sd, "cd-gpios", [GPIO3, 11, 1])  # GPIO3_B3, ACTIVE_LOW
    set_cells(sd, "vmmc-supply", [vcc18sd_ph])
    set_cells(sd, "vqmmc-supply", [VCC_1V8])
    ensure_empty(sd, "cap-sd-highspeed")
    ensure_empty(sd, "disable-wp")
    ensure_empty(sd, "no-sdio")
    ensure_empty(sd, "no-mmc")

    # --- Wi-Fi INT / PWCTL moved off GPIO2 (that bank is the SD card) ---
    wlan = find(root, "/wireless-wlan")
    set_cells(wlan, "WIFI,host_wake_irq", [GPIO3, 15, 0])
    # Keep Single RST polarity. ACTIVE_LOW here sent the last flash to Maskrom.

    charger = Node("gpio-charger")
    charger.props = [
        ("compatible", sprop("gpio-charger")),
        ("charger-type", sprop("usb")),
        ("charge-status-gpios", u32(GPIO0, 7, 1)),  # GPIO0_A7, ACTIVE_LOW
        ("status", sprop("okay")),
    ]
    add_child(root, charger)
    print("  added /gpio-charger")


def verify(dtb: bytes) -> None:
    tree = build(Fdt(dtb))
    usb = find(tree, "/usb@21500000")
    if printable_strings(usb.get("dr_mode")) != ["peripheral"]:
        raise SystemExit("USB dr_mode lost")
    if printable_strings(usb.get("maximum-speed")) != ["high-speed"]:
        raise SystemExit("USB maximum-speed lost")
    if usb.get("usb-role-switch") is not None or usb.get("extcon") is not None:
        raise SystemExit("USB role-switch/extcon came back")
    root = find(tree, "/")
    if printable_strings(root.get("model")) != ["CameVision Ego"]:
        raise SystemExit("model not CameVision Ego")
    cam0 = find(tree, "/i2c@21120000/sc233hgs@30")
    rst = struct.unpack(">3I", cam0.get("reset-gpios"))
    if rst[0] != GPIO4 or rst[1] != 3:
        raise SystemExit(f"cam0 reset-gpios still {rst}")
    cam1 = find(tree, "/i2c-gpio-cam1/sc233hgs@30")
    if printable_strings(cam1.get("compatible")) != ["smartsens,sc233hgs"]:
        raise SystemExit("cam1 missing")
    clk1 = struct.unpack(">2I", cam1.get("clocks"))
    if clk1 != (CRU, CLK_CAM1):
        raise SystemExit(f"cam1 clock {clk1}")
    if printable_strings(find(tree, "/i2c@21130000").get("status")) != ["disabled"]:
        raise SystemExit("i2c4 should stay disabled; SCL/SDA are swapped on the PCB")
    i2c_gpio = find(tree, "/i2c-gpio-cam1")
    scl = struct.unpack(">3I", i2c_gpio.get("scl-gpios"))
    sda = struct.unpack(">3I", i2c_gpio.get("sda-gpios"))
    if scl != (GPIO4, 6, 0) or sda != (GPIO4, 7, 0):
        raise SystemExit(f"cam1 i2c-gpio scl {scl} sda {sda}")
    if printable_strings(find(tree, "/spi@211e0000").get("status")) != ["okay"]:
        raise SystemExit("spi0 not okay")
    find(tree, "/spi@211e0000/imu@0")
    imu1 = find(tree, "/spi@211f0000/imu@0")
    irq = struct.unpack(">2I", imu1.get("interrupts"))
    if irq[0] != 13:
        raise SystemExit(f"imu1 irq pin {irq}")
    sd = find(tree, "/mmc@21d60000")
    if printable_strings(sd.get("status")) != ["okay"]:
        raise SystemExit("sdmmc0 not okay")
    p0 = struct.unpack(f">{len(sd.get('pinctrl-0'))//4}I", sd.get("pinctrl-0"))
    if SDMMC0_DETN in p0:
        raise SystemExit("sdmmc0 still claims stock detn (GPIO0_A5 LED)")
    wake = struct.unpack(">3I", find(tree, "/wireless-wlan").get("WIFI,host_wake_irq"))
    if wake[:2] != (GPIO3, 15):
        raise SystemExit(f"wifi wake still {wake}")
    find(tree, "/mipi2-csi2")
    find(tree, "/rkcif-mipi-lvds2-sditf")
    find(tree, "/rkisp-vir2-sditf")
    find(tree, "/rkvpss-vir1")
    if printable_strings(find(tree, "/csi2-dphy3").get("status")) != ["okay"]:
        raise SystemExit("dphy3 not okay")
    if printable_strings(find(tree, "/rkcif-mipi-lvds2").get("status")) != ["okay"]:
        raise SystemExit("lvds2 not okay")
    dvdd = struct.unpack(">I", find(tree, "/sc233hgs-dvdd").get("regulator-min-microvolt"))[0]
    if dvdd != 1_200_000:
        raise SystemExit(f"dvdd still {dvdd}")
    print("verify ok: Ego identity, dual SC233, dual IMU, SD, Wi-Fi GPIOs, CSI1, USB HS peripheral")


def insert_bytes(data: bytearray, pos: int, count: int) -> None:
    data[pos:pos] = b"\x00" * count


def update_u32_be(data: bytearray, off: int, value: int) -> None:
    struct.pack_into(">I", data, off, value)


def resource_entries(blob: bytes) -> list[tuple[str, int, int, int, int]]:
    if blob[:4] != b"RSCE":
        raise SystemExit("resource magic is not RSCE")
    hdr_blocks, entry_blocks = struct.unpack_from("<BB", blob, 8)
    out = []
    i = 0
    while True:
        off = hdr_blocks * 512 + i * entry_blocks * 512
        if blob[off : off + 4] != b"ENTR":
            break
        name = blob[off + 4 : off + 224].split(b"\x00")[0].decode("ascii", "replace")
        hash_size, f_offset, f_size = struct.unpack_from("<III", blob, off + 256)
        out.append((name, off, hash_size, f_offset, f_size))
        i += 1
    return out


def nop_fit_signature(data: bytearray, offsets: dict) -> None:
    key = ("/configurations/conf/signature", "algo")
    if key not in offsets:
        print("no FIT signature algo (ok)")
        return
    off, plen = offsets[key]
    data[off : off + plen] = b"\x00" * plen
    print("FIT signature algo cleared")


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else DST
    data = bytearray(src.read_bytes())
    fit = Fdt(bytes(data))
    fit_root = build(fit)
    offsets = prop_offsets(fit)
    img = find(fit_root, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    next_pos = len(data)
    for n in fit_root.walk():
        p = n.get("data-position")
        if p is None:
            continue
        other = struct.unpack(">I", p)[0]
        if pos < other < next_pos:
            next_pos = other
    slot = next_pos - pos
    print(f"fdt at {pos:#x} size {size}, slot {slot}")

    old_hash = None
    for c in img.children:
        if printable_strings(c.get("algo") or b"") == ["sha256"]:
            old_hash = c.get("value")
    old = bytes(data[pos : pos + size])
    if hashlib.sha256(old).digest() != old_hash:
        raise SystemExit("stored fdt hash mismatch")

    dtb = Fdt(old)
    root = build(dtb)
    print("edits:")
    patch_tree(root)
    new_dtb = serialize(root, read_mem_rsvmap(dtb), dtb.boot_cpuid_phys)
    print(f"new fdt {len(new_dtb)} (was {size}, slot {slot})")
    verify(new_dtb)

    new_slot = max(slot, align512(len(new_dtb)))
    if new_slot > slot:
        delta = new_slot - slot
        print(f"expanding FIT fdt slot {slot} -> {new_slot} (+{delta})")
        insert_bytes(data, next_pos, delta)
        for path in ("/images/kernel", "/images/resource"):
            off, plen = offsets[(path, "data-position")]
            if plen != 4:
                raise SystemExit(f"{path} data-position is not a cell")
            old_p = struct.unpack_from(">I", data, off)[0]
            update_u32_be(data, off, old_p + delta)
            print(f"  {path} data-position {old_p:#x} -> {old_p + delta:#x}")
        next_pos += delta
        slot = new_slot

    data[pos:next_pos] = new_dtb + b"\x00" * (slot - len(new_dtb))
    off, plen = offsets[("/images/fdt", "data-size")]
    struct.pack_into(">I", data, off, len(new_dtb))
    new_hash = hashlib.sha256(new_dtb).digest()
    hoff, _ = offsets[("/images/fdt/hash", "value")]
    data[hoff : hoff + 32] = new_hash
    print(f"FIT fdt hash {old_hash.hex()[:16]}... -> {new_hash.hex()[:16]}...")

    # resource copy — re-read position in case the FIT slot grew
    rpos = struct.unpack_from(">I", data, offsets[("/images/resource", "data-position")][0])[0]
    rsize = struct.unpack_from(">I", data, offsets[("/images/resource", "data-size")][0])[0]
    blob = bytes(data[rpos : rpos + rsize])
    entries = resource_entries(blob)
    target = next(e for e in entries if e[0] == "rk-kernel.dtb")
    _, entry_off, hash_size, f_offset, f_size = target
    start = f_offset * 512
    nxt = rsize
    for name, _, _, other_off, _ in entries:
        o = other_off * 512
        if start < o < nxt:
            nxt = o
    res_slot = nxt - start
    print(f"resource rk-kernel.dtb size {f_size}, slot {res_slot}")
    need = align512(len(new_dtb))
    if need > res_slot:
        res_delta = need - res_slot
        print(f"expanding resource dtb slot {res_slot} -> {need} (+{res_delta})")
        insert_bytes(data, rpos + nxt, res_delta)
        rsize += res_delta
        struct.pack_into(">I", data, offsets[("/images/resource", "data-size")][0], rsize)
        delta_blocks = res_delta // 512
        for name, eoff, hs, fo, fs in entries:
            if fo * 512 > start:
                struct.pack_into("<I", data, rpos + eoff + 260, fo + delta_blocks)
                print(f"  resource {name} f_offset {fo} -> {fo + delta_blocks}")
        res_slot = need

    stored = bytes(data[rpos + entry_off + 224 : rpos + entry_off + 224 + hash_size])
    old_res_dtb = bytes(data[rpos + start : rpos + start + f_size])
    calc = hashlib.sha1(old_res_dtb).digest() if hash_size == 20 else hashlib.sha256(old_res_dtb).digest()
    if calc != stored:
        raise SystemExit("resource entry hash mismatch before patch")
    data[rpos + start : rpos + start + res_slot] = new_dtb + b"\x00" * (res_slot - len(new_dtb))
    struct.pack_into("<I", data, rpos + entry_off + 264, len(new_dtb))
    new_entry_hash = hashlib.sha1(new_dtb).digest() if hash_size == 20 else hashlib.sha256(new_dtb).digest()
    data[rpos + entry_off + 224 : rpos + entry_off + 224 + hash_size] = new_entry_hash
    print(f"  resource entry hash updated, f_size {f_size} -> {len(new_dtb)}")

    res_hash_off, _ = offsets[("/images/resource/hash", "value")]
    new_res = hashlib.sha256(bytes(data[rpos : rpos + rsize])).digest()
    data[res_hash_off : res_hash_off + 32] = new_res
    print(f"  resource sha256 updated")

    nop_fit_signature(data, offsets)

    if len(data) < BOOT_PART:
        data.extend(b"\x00" * (BOOT_PART - len(data)))
    if len(data) > BOOT_PART:
        used = rpos + rsize
        if used > BOOT_PART:
            raise SystemExit(f"boot image used {used} > partition {BOOT_PART}")
        data = data[:BOOT_PART]

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(data))
    DTB_OUT.parent.mkdir(parents=True, exist_ok=True)
    DTB_OUT.write_bytes(new_dtb)
    print(f"wrote {dst} ({len(data)} bytes)")
    print(f"wrote {DTB_OUT} ({len(new_dtb)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
