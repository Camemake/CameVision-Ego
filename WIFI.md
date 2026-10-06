# CameVision Wi‑Fi — rebuild notes for Ego

Working reference: CameVision Single Gen2, 2026-09-02, after replacing Q1 with a **BSS84LT1G**.
Target: CameVision Ego (same VS6621S80, same Q1 circuit, different wake/INT pads).

Copy the **power/reset path and the driver stack**. Do **not** copy Single GPIO2_A4 / GPIO2_A5 onto Ego — those balls are the microSD host.

---

## 1. What “working” looks like

On Single Gen2, after a real BSS84 (not sitting on SOT-523 pads):

- Kernel: `mmc2: new SDIO card at address 0001` about 28 ms after 400 kHz
- Sysfs: `/sys/bus/sdio/devices/mmc2:0001:1` with `SDIO_ID=1FFE:6621`
- `WIFI_RST` (linux gpio **106**) stays **low** after enum (CHIP_EN on)
- `skw_sdio_lite` + `swt6621s_wifi` (rt52) → `wlan0` → STA (example lease `192.168.1.26`)
- Log line: `WIFI_READY`

If `1FFE:6621` is missing, **stop**. Do not load drivers. The STA script is not the bug.

---

## 2. Hardware (Ego rework — same as Single)

**Module:** VS6621S80 / SWT6621-S (Ego **U14**)

**Power sequence (vendor datasheet):**

1. V3P3 (3.3 V) ramps
2. VDDIO (1.8 V) after 3.3 V is up
3. CHIP_EN goes high (high = enable)
4. CHIP_EN must be **low ≥ 50 ms**, then rise (T4)

### Q1

| | Wrong (stock) | Right (Gen1 / proven) |
|---|---|---|
| Part | CB2301T-2.8A | **BSS84LT1G** |
| Package | SOT-523 | **SOT-23** |
| Vgs(th) | ~1.0 V | −0.8…−2.0 V (typ ~−1.7 V) |

Circuit on both boards:

- Source = **+3.3V_MAIN**
- Gate = **WIFI_RST** through **R20 220 Ω** (1.8 V GPIO)
- Drain = **CHIP_EN** (U14.12) + **R21 100 k** to GND + **C36 100 nF**
- “Off” is only Vgs = **1.8 − 3.3 = −1.5 V**

The CB2301T stays **on** at −1.5 V. CHIP_EN never falls, the ROM never gets a reset edge, the host sees CMD5 timeout (400→100 kHz). A typical BSS84 turns off. That is the hardware fix.

**Mount:** dead-bug with three short wires, or a real SOT-23 land. Do **not** press the SOT-23 onto the SOT-523 copper. Single enumerated once that way, then the joint opened and the board looked like the CB2301T again.

BSS84 pinout: **1 = G, 2 = S, 3 = D**.

- Pin 1 G → gate pad (R20 side)
- Pin 2 S → +3.3V_MAIN
- Pin 3 D → CHIP_EN (U14.12 / R21 / C36)

### Meter (before any software)

| WIFI_RST (gpio 106) | CHIP_EN U14.12 | V3P3 U14.9 | VDDIO U14.22 |
|---|---|---|---|
| 0 V (run) | **~3.3 V** | 3.3 V | 1.8 V |
| 1.8 V (reset) | **~0 V** | 3.3 V if the rail is always-on | 1.8 V |

On Ego, Q1 also gates the 3.3 V rail. Then U14.9 should track CHIP_EN (3.3 V when RST is low, 0 V when RST is high). If pin 12 does not toggle, the FET is not switching.

---

## 3. Ego pads — do not clone Single GPIO2

SDMMC1 balls are the same. Wake and INT are **not**.

| Net | VS6621 pin | Ego SoC | Linux gpio | Single (do not copy) |
|---|---|---|---|---|
| SDIO CLK | 17 | GPIO3_A0 B22 | — | same |
| SDIO CMD | 16 | GPIO3_A1 B21 | — | same |
| SDIO D0 | 18 | GPIO3_A2 A22 | — | same |
| SDIO D1 | 19 | GPIO3_A3 A23 | — | same |
| SDIO D2 | 14 | GPIO3_A4 A20 | — | same |
| SDIO D3 | 15 | GPIO3_A5 B20 | — | same |
| CHIP_EN / Q1 gate | 12 | **GPIO3_B2** 1B16 **WIFI_RST** | **106** | same pin, same job |
| HOST_WAKE_WL | 34 | **GPIO3_B6** B16 | **110** | Single used GPIO2_A4 = gpio 68 |
| WL_WAKE_HOST | 13 | **GPIO3_B7** A16 | **111** | Single used GPIO2_A5 = gpio 69 |
| UART TXD (SDIO strap) | 42 | GPIO3_B0 B17 (SoC UART2 RX) | — | same; must idle **high** |
| UART RXD | 43 | GPIO3_B1 A17 | — | same |

**Never** drive Ego GPIO2_A4 / GPIO2_A5 for Wi‑Fi.

CMD/DAT pull-ups: 47 kΩ to **+1.8V_MAIN** (Ego R66, R74–R77). VCCIO3 is 1.8 V. Host `ios` may still say `signal voltage 3.30 V` if `vqmmc` is missing — ignore that; the pads are 1.8 V.

---

## 4. Device tree

Match working Single **pwrseq polarity** and Ego **silk**.

This is what enumerated on Single (live FIT):

```dts
sdio_pwrseq: sdio-pwrseq {
	compatible = "mmc-pwrseq-simple";
	pinctrl-names = "default";
	pinctrl-0 = <&wifi_reg_on>;
	reset-gpios = <&gpio3 RK_PB2 GPIO_ACTIVE_HIGH>;	/* flags 0 */
	post-power-on-delay-ms = <200>;	/* 500 also fine; T4 min is 50 ms */
};
```

`GPIO_ACTIVE_HIGH` means:

- assert = B2 **high** → Q1 off → CHIP_EN low
- deassert = B2 **low** → Q1 on → CHIP_EN high
- wait `post-power-on-delay-ms`, then CMD5

`mmc@21f60000` / `&sdmmc1`:

- `status = "okay"`
- `bus-width = <4>`
- `cap-sdio-irq`, `no-sd`, `no-mmc`
- `non-removable`, `keep-power-in-suspend`
- `mmc-pwrseq = <&sdio_pwrseq>`
- `vmmc` = always-on 3.3 V dummy — do **not** hang vmmc on GPIO3_B2 (pwrseq owns that pin)
- Working Single had **no `vqmmc-supply`**. Ego source DTS has `vqmmc-supply = <&vcc_1v8>`. Either is OK if VCCIO3 is 1.8 V. Do not invent a 3.3 V I/O domain.

WLAN / BT:

```dts
wireless_wlan: wireless-wlan {
	compatible = "wlan-platdata";
	wifi_chip_type = "vs6621";
	pinctrl-names = "default";
	pinctrl-0 = <&wifi_wake_host &wifi_pwctl_en>;
	WIFI,host_wake_irq = <&gpio3 RK_PB7 GPIO_ACTIVE_HIGH>;	/* Ego A16 */
	status = "okay";
};
```

Pinctrl:

```dts
wifi_reg_on: wifi-reg-on {
	rockchip,pins = <3 RK_PB2 RK_FUNC_GPIO &pcfg_output_low>;
};

wifi_pwctl_en: wifi-pwctl-en {
	rockchip,pins = <3 RK_PB6 RK_FUNC_GPIO &pcfg_output_high>;	/* HOST_WAKE */
};

wifi_wake_host: wifi-wake-host {
	rockchip,pins = <3 RK_PB7 RK_FUNC_GPIO &pcfg_pull_up>;
};
```

**`BT,power_gpio` must not be GPIO3_B2.** On Single it shares B2 and pwrseq wins. On Ego, BT driving B2 high kills Q1. Park BT power on a dummy (Ego wifi FIT patch already moved it to GPIO3_A7).

UART2 must probe **before** mmc pwrseq so U14.42 stays high (SDIO strap). Ego already has `ttyS2` up around 0.86 s.

Checked-in Ego sources:

- `device-tree/rv1126b-camevision-ego.dts`
- `tools/cv_ego_wifi_fix_dtb.py`

After the BSS84 rework, flash that boot DTB. Do not go back to a FIT that uses `GPIO_ACTIVE_LOW` on B2.

---

## 5. Software after `1FFE:6621` exists

**Kernel:** `6.1.141-rt52` (same as Single).

**Modules and firmware** (from Single):

`CameVision Single/restore/recovery-2-20260821-adb-stream/overlay/`

| Path | What |
|---|---|
| `swt6621-rt52/` | `cfg80211`, `mac80211`, `skw_sdio_lite`, `swt6621s_wifi`, `skwbt`, plus `libarc4`, `gf128mul`, `ctr`, `ccm`, `aes_generic` |
| `swt6621_fw/` | `SWT6621S_DRAM_SDIO.bin`, `SWT6621S_IRAM_SDIO.bin`, `SWT6621S_NV_SDIO.bin` |

If `SWT6621S_NV_SDIO.bin` is missing, copy `SWT6621S_NV_SDIO_ALONE.bin` to that name (and to `SEEKWAVE_NV_SWT6621S.bin` if the loader asks).

Aura stock kos fail on this RT kernel (`__mutex_init`). Use **rt52** only.

Bring-up order (from Single `camevision-wifi.sh`):

1. Wait until `/sys/bus/sdio/devices/mmc2:0001:1` exists (up to 40 s). Else exit.
2. Check `SDIO_ID=1FFE:6621`
3. `echo /userdata/swt6621_fw > /sys/module/firmware_class/parameters/path`
4. `insmod` cfg80211 → mac80211 → crypto helpers → **skw_sdio_lite** → sleep 1 → **swt6621s_wifi**
5. Wait for `wlan0`, `ip link set wlan0 up`
6. `wpa_supplicant -B -i wlan0 -c /userdata/wpa_camevision.conf -D nl80211`
7. `udhcpc` / `dhcpcd`

Do **not** insmod rockit or camera kos for Wi‑Fi. Do **not** steal gpio 106 from pwrseq. On Ego, if userspace needs HOST_WAKE, export **gpio 110** high — not gpio 68.

STA conf: copy Single overlay `wpa_camevision.conf` (SSID `Camemake R&D center`). Do not rewrite it.

Script reference:

`CameVision Single/restore/recovery-2-20260821-adb-stream/overlay/camevision-wifi.sh`

---

## 6. Pass / fail on Ego (ADB)

```sh
cat /sys/bus/sdio/devices/mmc2:0001:1/uevent
# expect SDIO_ID=1FFE:6621

mount -t debugfs none /sys/kernel/debug 2>/dev/null
grep gpio-106 /sys/kernel/debug/gpio
# after success: reset out lo

grep 'gpio3-0' /sys/kernel/debug/pinctrl/*/pinmux-pins
# expect function sdmmc1

dmesg | grep mmc2
# success: 400 kHz then ~50 MHz, "new SDIO card"
# fail:    400 → 300 → 200 → 100 kHz, no card

ip -4 addr show wlan0
cat /userdata/wifi.log
```

`400→300→200→100 kHz` then gpio-106 **out hi** means the chip never answered; pwrseq powered it off. Same as Single with the CB2301T.

---

## 7. Do not do this

- Unbind `21f60000.mmc` while `skw_sdio_lite` is loaded — firmware hangs (`check CP-ready time out`). Soft reboot may still enum; firmware stays dead until a **hard power cut**.
- `echo 1 > /sys/class/mmc_host/mmc2/force_rescan` — does **not** re-run pwrseq on this SDIO host.
- Unbind `pwrseq_simple` while mmc is bound — kernel panic (`panic=10`).
- Treat mmc2 as a memory-card socket. It is the VS6621 SDIO function only.
- Copy Single `camevision-hw.sh` (`gpio 68`) onto Ego.

---

## 8. Order of work on a reworked Ego

Default flash (Maskrom, empty board, BSS84 already fitted):

```
python tools/cv_ego_flash.py
```

That is **flash V0.2** (`restore/release-0.2-20260902`): Wi-Fi DTB, RV-3028 trickle, CameVision partitions, stereo page, STA on boot, RTC `S11hwclock`, pylib. USB stays ADB.

Manual order if you are not flashing:

1. Confirm BSS84: CHIP_EN (and V3P3 if Q1 switches the rail) toggles with B2.
2. Boot the Ego Wi‑Fi FIT (`ACTIVE_HIGH` on B2, INT on B7, wake on B6, BT off B2).
3. If `1FFE:6621` appears, push rt52 kos + firmware + `camevision-wifi.sh` + `wpa_camevision.conf` and run the script.
4. If CHIP_EN toggles and there is still no function, look at the bus/strap (CMD pull-up, U14.42 not high) — not Q1.

Hardware fix: Q1 = BSS84, mounted so it stays connected.
Software fix: Single pwrseq polarity + Ego B6/B7 map + rt52 stack after enum.
