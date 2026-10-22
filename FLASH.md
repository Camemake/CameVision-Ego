# Flash CameVision EGO from Maskrom

Empty board or a board that already has images. USB stays the Camemake ADB gadget.

Product page: https://camemake.github.io/CameVision-Ego/  
Shop: https://www.camemake.eu/shop/cv-ego01-os-camevision-ego-dual-global-shutter-ai-stereo-camera-2414

## What you need

- CameVision EGO. Two Maskrom kits: **SC233HGS** (`restore/release-0.2-20260902`) and **AM / MIRA220** (`restore/release-2.0-am-mira220-20261009`)
- USB-C cable that carries data
- A PC with Python 3.10+ (or the offline folder, which ships its own Python)
- Rockchip USB access: Windows driver in `host/DriverAssitant_v5.14`, Linux udev in `host/linux/99-camevision-rockusb.rules`
- Partition images next to the tree (see [Images](#images))

Hardware note: Wi-Fi needs **BSS84LT1G** in Q1. See [`WIFI.md`](WIFI.md). Stereo and ADB work without that rework.

## Sequence

| Step | What to do |
|---|---|
| USB | Install USB driver. Hold **BOOT**, tap **RESET**, keep BOOT held. Device is Maskrom (`2207:110c`) or Loader. |
| Package | `python tools/cv_ego_flash.py --prebuilt --package camevision-ego` or `--package camevision-ego-am` |
| ADB | `python tools/cv_ego_page.py` |

Release BOOT when the write finishes and the board starts.

## Enter Maskrom

1. Power the board (USB-C is enough).
2. Hold **BOOT**.
3. Tap **RESET**.
4. Keep BOOT held until the tool or `upgrade_tool` sees Maskrom / Loader.

Maskrom USB id is Rockchip `2207:110c`. After the loader is written once (`db`), the same port may re-enumerate as Loader. After `rd` (reset device) and BOOT released, the gadget is ADB `2207:0006`, strings Camemake / CameVision Ego.

If nothing enumerates: try another cable, another USB port (avoid unpowered hubs), and confirm BOOT is the pad next to RST / PH.

## Partition map

`upgrade_tool` writes the 1 GB DDR loader once (`db`), then each image at a fixed LBA (`wl`). Overlay is not a partition. It is copied into `/userdata` over ADB after the board boots.

| LBA | Image | Role |
|---|---|---|
| loader (`db` once) | `rv1126b_spl_loader_k4a8g.bin` | SPL for the fitted 1 GB DDR |
| `0x0` | `env.img` | U-Boot env |
| `0x40` | `idblock.img` | idblock |
| `0x440` | `uboot.img` | U-Boot |
| `0x2440` | `camevision_boot_ego.img` or `camevision_boot_ego_am.img` | Kernel + DTB FIT (`6.1.141-rt52`) — pick the sensor kit |
| `0x7C40` | `userdata.img` | Skeleton, then overlay |
| `0x207C40` | `oem_noko.img` | rkaiq, IQ binaries, oem libs |
| `0x607C40` | `rootfs_bootstable.img` | Root filesystem |

Same addresses are printed by `tools/cv_ego_flash.py` and `tools/cv_ego_wifi_full_flash.py`.

Command-line equivalent of **Install**:

```
python tools/cv_ego_flash.py --prebuilt --package camevision-ego
python tools/cv_ego_flash.py --prebuilt --package camevision-ego-am
```

Rebuild the SC233HGS Ego boot FIT (Wi-Fi + RV-3028 DTB) then write:

```
python tools/cv_ego_flash.py --rebuild
```

Manual `upgrade_tool` (Windows names; Linux is `host/linux/upgrade_tool`):

```
host/upgrade_tool.exe db restore/release-0.2-20260902/rv1126b_spl_loader_k4a8g.bin
host/upgrade_tool.exe wl 0x0       restore/release-0.2-20260902/env.img
host/upgrade_tool.exe wl 0x40      restore/release-0.2-20260902/idblock.img
host/upgrade_tool.exe wl 0x440     restore/release-0.2-20260902/uboot.img
host/upgrade_tool.exe wl 0x2440    restore/release-0.2-20260902/camevision_boot_ego.img
host/upgrade_tool.exe wl 0x7C40    restore/release-0.2-20260902/userdata.img
host/upgrade_tool.exe wl 0x207C40  restore/release-0.2-20260902/oem_noko.img
host/upgrade_tool.exe wl 0x607C40  restore/release-0.2-20260902/rootfs_bootstable.img
host/upgrade_tool.exe rd
python tools/cv_ego_overlay_deploy.py
python tools/cv_ego_overlay_deploy_am.py
```

Do **not** write Aura boot / oem / rootfs. Those images are a different product.

## Images

The full Maskrom set lives in `restore/release-0.2-20260902/`. Clone with Git LFS so rootfs, oem and userdata come down:

```
git lfs install
git clone https://github.com/Camemake/CameVision-Ego.git
```

Required names:

```
rv1126b_spl_loader_k4a8g.bin
env.img
idblock.img
uboot.img
camevision_boot_ego.img
userdata.img
oem_noko.img
rootfs_bootstable.img
```

The boot FIT in this tree is built from `device-tree/rv1126b-camevision-ego.dts` by `tools/cv_pack_release02.py`. Overlay sources live in `restore/release-0.2-20260902/overlay/` and are mirrored under `tools/` for day-to-day edits.

**GitHub update** in the offline tool downloads the latest `Camemake/CameVision-Ego` release zip (or `main` zipball) into `restore/updates/current`.

## Overlay after ADB

The write leaves a skeleton `/userdata`. The overlay is the product:

| On the board | Source |
|---|---|
| `/userdata/ego_stereo.py` | `tools/ego_stereo.py` |
| `/userdata/libego_stereo.so` | `tools/stereo_native.c` → `build/libego_stereo.so` |
| `/userdata/ego_cam_sync.py` | `tools/ego_cam_sync.py` |
| `/userdata/ego_imu_hud.py` | `tools/ego_imu_hud.py` |
| `/userdata/ego_calib.html` | `tools/ego_calib.html` |
| `/userdata/camevision-stereo.sh` | `tools/camevision-stereo.sh` |
| `/userdata/camevision-wifi.sh` | `tools/camevision-wifi.sh` |
| `/userdata/iqfiles/` | `tools/iqfiles/` |
| `/etc/init.d/S99ego-stereo` | `tools/S99ego-stereo` |
| `/etc/init.d/S11hwclock` | `tools/S11hwclock` |

```
python tools/cv_ego_overlay_deploy.py
python tools/cv_ego_overlay_deploy_am.py
```

Board already running Recovery 5 / V0.2, no Maskrom: overlay only is enough.

## Open the live page

```
python tools/cv_ego_page.py
```

Forwards the on-board stereo page and IMU HUD, then opens a browser.

Keep it up after every plug:

```
python tools/cv_ego_autostart.py --install
```

Extended dump (identity, I2C, IMU, video, dmesg):

```
python tools/cv_ego_diag.py
```

## Boot chain

1. SPL loader → U-Boot → FIT (`camevision_boot_ego.img`)
2. `S11hwclock` loads RV-3028 so a power cut is not 1970
3. `S99ego-stereo` starts `camevision-stereo.sh`
4. that script loads kmpp, Wi-Fi (if SDIO `1FFE:6621` is up), rkaiq 3A, IMU HUD, then `ego_stereo.py`
5. the host only forwards USB and opens a browser

USB `dr_mode` stays **peripheral**. The gadget is ADB. There is no webcam profile in this package.

## Do not

- Flash a non-CameVision boot / oem / rootfs
- Switch USB to UVC
- Skip Maskrom on an empty board (overlay-only needs a running ADB gadget)
- Publish or commit PCB schematics, netlists, or the schematic PDF

## More

- Flash page: [flash.html](https://camemake.github.io/CameVision-Ego/flash.html)
- Software map: [software.html](https://camemake.github.io/CameVision-Ego/software.html)
- Pinmux / IMU precision: [hardware.html](https://camemake.github.io/CameVision-Ego/hardware.html)
- V0.2 notes: [`restore/release-0.2-20260902/RELEASE.md`](restore/release-0.2-20260902/RELEASE.md)
