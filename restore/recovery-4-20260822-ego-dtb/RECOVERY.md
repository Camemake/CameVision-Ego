# Recovery 4 — CameVision Ego — 2026-08-22 (Ego DTB, ADB)

First **Ego-specific** restore point. Recovery 3 is the Single camera
stack (`restore/recovery-3-20260822-uvc-wifi-rkaiq`). This package is
the Recovery 3 kernel/rootfs **plus** the compiled Ego device tree.

USB stays **ADB**. Do not reboot this board into UVC.

## Product
- Board: CameVision Ego V1.I1, Rockchip RV1126B
- RAM: Samsung `K4A8G165WG` 16-bit 1 GB (PDF `K4A4G165WG` is wrong)
- eMMC: `BWCTAK611G16G` (same part as Single)
- IMU: `LSM6DSVQTR` ×2 (PDF `LSM6DSV320XTR` is wrong)
- USB gadget: ADB, VID `0x2207` PID `0x0006`, serial `b9129b95306c7715`
- Strings: CameMake / **CameVision Ego** / `CVEgo`
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT`
- Live model: `CameVision Ego` (`camemake,camevision-ego`)

## Proven live (2026-08-22)
- Boot.img on eMMC matches this package
  (`sha256 28cf1d7b90079a05941ef7419b005e64a5bddafbc3cc342034d50154e46e3b27`)
- Linux + ADB + eMMC
- I2C devices: RK801 `0-0027`, RV-3028 `2-0052`, SC233 nodes `3-0030` and `4-0030`
- Dual CIF/ISP video nodes present (`rkisp_mainpath` on `/dev/video24` and `/dev/video32`)

Not proven yet: sensor chip-id (both SC233 still NACK, `-5`), IMU whoami,
microSD, Wi-Fi on the moved GPIOs.

## Images

| What | File |
|---|---|
| **Flash this boot** | `camevision_boot_ego.img` (11 MiB) |
| Rollback to Single DTB | `boot_before_ego.img` (Recovery 3 wifi+IMU tree) |
| Compiled DTB | `device-tree/rv1126b-camevision-ego.dtb` |
| Board source | `device-tree/rv1126b-camevision-ego.dts` |
| ADB gadget (keep as S50) | `overlay/S50usbdevice.adb` |

Rootfs / oem / userdata are still Recovery 3. Full eMMC rebuild uses
Recovery 3 `restore-camevision.ps1`, then flash this boot.

Loader (Maskrom, once per session):
`restore/known-good-20260819-camera-adb/rv1126b_spl_loader_k4a8g.bin`

## Restore boot only (board already running ADB)

```
python tools/cv_flash_ego_boot.py
```

or from this folder: `flash-boot-ego.ps1`. That `dd`s `camevision_boot_ego.img`
to `/dev/mmcblk0p4` and reboots. USB must stay ADB.

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- `upgrade_tool db` twice in one Maskrom session
- Reboot Ego into UVC
- Extra leftover `S50usbdevice.*` in `/etc/init.d` (`rcS` runs `S??*`)
- `insmod rockit` / `insmod_ko.sh`
- `camevision-uvc-h264.py` or `isp_grab.py` burst
- Hold BOOT after `rd`
