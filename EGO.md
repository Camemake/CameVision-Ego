# CameVision Ego

This folder is the **CameVision Ego** project (not Dual). Schematic title
block is `CameVisionEgo` V1.I1, released 2026-07-15 (19 sheets).

Recovery 5 is the working dual-camera ISP image:
`restore/recovery-5-20260823-imaging-adb`. USB stays ADB. Do not reboot
this board into UVC.

## Schematic vs what is actually fitted

RAM and IMU MPNs in the PDF are **wrong**. eMMC is the real part on both
boards.

| Block | Schematic label | Actual |
|---|---|---|
| DDR4 U3 | `K4A4G165WG-BCWE` (512 MB) | Samsung `K4A8G165WG` 16-bit **1 GB**. Loader is `rv1126b_spl_loader_k4a8g.bin`. |
| IMU U9 / U12 | `LSM6DSV320XTR` | ST **`LSM6DSVQTR`** ×2 (`lsm6dsv_accel` / `lsm6dsv_gyro`) |
| eMMC U2A | `BWCTAK611G16G` | **`BWCTAK611G16G`** — same part on Single and Ego |

Device tree: `device-tree/rv1126b-camevision-ego.dts`.

## Board map (from the Ego schematic)

19 sheets: Top, PowerReg, SOC_Power, SOC_System, SOC_DDR, SOC_FlashMemory,
SOC_USB, SOC_ADC_Boot, SOC_COM_Audio_Camera, SOC_COM_Display,
SOC_Audio-not-used, SOC_EPHY-not-used, DDR4_16b, MIPI_Camera0,
MIPI_Camera1, WiFi_BT, uSD_Card, USB-C_PD, Battery.

### SoC / power / RTC
- Rockchip **RV1126B** (same family as Single)
- PMIC **RK801-2** on I2C0 (`I2C0_SCL/SDA_PMIC`)
- RTC **RV-3028-C7** on I2C2 (live: `2-0052`)
- Status LED D1 RGB common-anode: green GPIO0_A5, red GPIO0_A6, blue GPIO0_A4
- Boot: SARADC0_IN7 Maskrom / eMMC (same Rockchip resistor ladder)
- Ethernet PHY sheet is **not used**

### Cameras (new vs Single)
Two SmartSens **SC233HGS**, native 1920×1200. SID stuffing looks the same
on both, so each stays `0x30` on its **own** I2C bus.

| Cam | MIPI | I2C | PWDN / XSHUTDN | IMU |
|---|---|---|---|---|
| Cam 0 (U7) | CSI RX0, 4-lane + CLK0 | I2C3 `I2C3_SCL/SDA_CAM` | `CAM0_PWDN` | IMU0 on **SPI0** |
| Cam 1 (U10) | CSI RX1, 4-lane + CLK0 | I2C4 `I2C4_SCL/SDA_CAM` | `CAM1_PWDN` | IMU1 on **SPI1** |

Single DTB only has one sensor on i2c3 `3-0030`. That node already fails
on Ego (`chip id high read failed: -5`) — pinmux / power / bus is not the
Single camera wiring.

### IMUs (two, same part as Single)
- IMU0 U9: SPI0 (`SPI0_CLK/CS0/MISO/MOSI`), `IMU0_INT1/INT2`, next to Cam 0
- IMU1 U12: SPI1 (`SPI1_CLK/CS0/MISO/MOSI`), `IMU1_INT1/INT2`, next to Cam 1
- Single DTB has one LSM6 on `spi0.0` — live whoami `0xff` (wrong mux / CS)

### Storage / wireless
- eMMC on the dedicated EMMC/FSPI bus (live `mmc0`)
- microSD U6 `475710001` on **SDMMC0** (`SDMMC0_CLK/CMD/D0–D3`, `DET`, `PWREN`)
- Wi-Fi/BT **VS6621S80** U14 on **SDMMC1** + UART2 (same module as Single)
- Live: `mmc2` present, no `mmcblk1` until SD host + card are in the DTB

### USB / battery (new vs Single)
- USB-C J3 `10132328-10011LF`: USB2 + USB3 DRD, CC 5.1k, VBUS detect
- Charger **BQ24072RGTR** U13: 250 mA fast charge, 1.5 A input limit, `BAT_CHG`
- Sliding power switch + backup power-path FET
- No `/sys/class/power_supply` until a charger node is in the DTB

## Restore points

| # | Path | Meaning |
|---|---|---|
| 3 | `restore/recovery-3-20260822-uvc-wifi-rkaiq` | Single camera stack (base rootfs/oem) |
| 4 | `restore/recovery-4-20260822-ego-dtb` | First Ego DTB (Cam 1 still NACK) |
| **5** | `restore/recovery-5-20260823-imaging-adb` | Dual ISP + I2C-GPIO Cam 1 + ADB preview |
| **6** | `restore/recovery-6-20260823-stereo-depth` | **On-board stereo depth overlay (no flash)** |

Flash Ego imaging boot: `python tools/cv_flash_imaging_boot.py` or
`restore/recovery-5-20260823-imaging-adb/flash-boot-ego.ps1`.

Restore stereo only (Recovery 5 must already be live):
`python tools/cv_ego_stereo_start.py` or
`restore/recovery-6-20260823-stereo-depth/restore-stereo.ps1`.

## First Ego bring-up (2026-08-22)

- ADB serial: `b9129b95306c7715` (`2207:0006`)
- USB gadget strings: CameMake / **CameVision Ego** / `CVEgo` (ADB stays on)
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT`
- DTB model: **CameVision Ego**
- Live ADB serial: `4857b9cbd0b99e0b`

### What works (Recovery 5)
- Linux boot, ADB, eMMC
- Cam 0 I2C3 `3-0030` chip id `0xcb61` → `/dev/video24`
- Cam 1 I2C-GPIO `6-0030` chip id `0xcb61` → `/dev/video32`
- Both SPI IMUs
- Side-by-side ISP preview at http://127.0.0.1:8765/

### Not proven yet
- microSD (1.8 V VDD — consumer cards will not enumerate)
- Wi-Fi STA join
- BQ24072
