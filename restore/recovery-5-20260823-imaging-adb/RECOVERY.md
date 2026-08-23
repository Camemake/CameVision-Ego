# Recovery 5 — CameVision Ego — 2026-08-23 (dual ISP + ADB)

Working **dual-camera ISP** restore point. USB stays **ADB**.

Recovery 4 was the first Ego DTB (Cam 1 still NACK). This package is
the last proven live boot: Cam 0 + Cam 1, RKAIQ 3A, side-by-side
1920×1200 preview.

Do not flash Luckfox Aura. Do not reboot this board into UVC.

## Product
- Board: CameVision Ego V1.I1, Rockchip RV1126B
- RAM: Samsung `K4A8G165WG` 16-bit 1 GB
- eMMC: `BWCTAK611G16G`
- Sensors: SmartSens SC233HGS ×2, chip id `0xcb61`
- IMU: `LSM6DSVQTR` ×2
- USB gadget: ADB, VID `0x2207` PID `0x0006`, serial `4857b9cbd0b99e0b`
- Strings: CameMake / **CameVision Ego**
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT`
- Live model: `CameVision Ego`

## Proven live (2026-08-23)
- Cam 0: I2C3 `3-0030` → CSI RX0 / `csi2-dphy0` / `rkisp-vir0` → `/dev/video24`
- Cam 1: I2C-GPIO `6-0030` → CSI RX1 / `csi2-dphy3` / `rkisp-vir2` → `/dev/video32`
- Hardware `/i2c@21130000` **disabled** (PCB swapped I2C4 SCL/SDA)
- RKAIQ `rkaiq_3A_server --silent` with backlight IQ
- Preview: http://127.0.0.1:8765/ — two 1920×1200 ISP NV12 feeds, `hflip,vflip` (180°), no text

Not in this restore: consumer microSD (1.8 V VDD rail), Wi-Fi STA join.

## Images

| What | File |
|---|---|
| **Flash this boot** | `camevision_boot_ego.img` (11 MiB) |
| Compiled DTB (from that FIT) | `device-tree/rv1126b-camevision-ego.dtb` |
| Board source | `device-tree/rv1126b-camevision-ego.dts` |
| ADB gadget (keep as S50) | `overlay/S50usbdevice.adb` |
| Live preview | `overlay/ego_mjpeg.py`, `overlay/cv_ego_start_live.py` |
| IQ | `overlay/iqfiles/sc233hgs_efference-sc233hgs_default.json` |

Full eMMC rebuild (Maskrom, loader **once**):

| LBA | name | file |
|---|---|---|
| 0x0 | env | `../known-good-20260819-camera-adb/env.img` |
| 0x40 | idblock | `../known-good-20260819-camera-adb/idblock.img` |
| 0x440 | uboot | `../known-good-20260819-camera-adb/uboot.img` |
| 0x2440 | boot | `camevision_boot_ego.img` (this folder) |
| 0x7C40 | userdata | Aura stock `userdata.img` (clean) |
| 0x207C40 | oem | `../known-good-20260819-camera-adb/oem_noko.img` |
| 0x607C40 | rootfs | `../known-good-20260819-camera-adb/rootfs_bootstable.img` |

Loader: `../known-good-20260819-camera-adb/rv1126b_spl_loader_k4a8g.bin`

Then push `overlay/` and run `python tools/cv_ego_start_live.py`.

## Restore boot only (board already on ADB)

```
python tools/cv_flash_imaging_boot.py
```

or `flash-boot-ego.ps1` in this folder. USB must stay ADB.

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- `upgrade_tool db` twice in one Maskrom session
- Reboot Ego into UVC
- Extra leftover `S50usbdevice.*` in `/etc/init.d`
- `insmod rockit` / `insmod_ko.sh`
- Hold BOOT after `rd`
- Change `sdio-pwrseq` reset polarity and flash without a Maskrom plan
