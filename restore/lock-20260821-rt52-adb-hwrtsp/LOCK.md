# LOCK — CameVision Single — 2026-08-21

Frozen snapshot of the board as inspected ~05:58–06:05 (host local). Do not flash Luckfox Aura. Do not swap kernels. Do not change USB gadget. Next work is part-by-part on top of this.

## Product
- Board: CameVision Single (same SoC family as M1)
- SoC: Rockchip RV1126B, 1 GB DDR4, Samsung eMMC 14912 MB
- USB gadget: ADB only, `2207:0006`, strings CameMake / CameVision Single, serial `0558fa189447bc45`
- Windows may still show “Nexus 4 / occam” — that is adbd’s default model string, not a phone

## What is running (live)
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT` (bryan@tronlong, 2026-07-15)
- Hostname in rootfs: `luckfox` (Buildroot 2025.02.6) — cosmetic only
- Sensor: SC233HGS i2c3@0x30, chip id `0xcb61`, STREAMON 1920x1200@30 NV12 on `/dev/video13`
- Grab: `isp_grab.py` ~27.8 fps, `/dev/shm/isp.nv12` = 3456000 bytes
- kmpp: `/userdata/kmpp-rt52.ko` loaded, `/dev/mpp_service` present
- `hw_rtsp.py` process is up and binds `:8554`, but encoder calls fail: `mpi_enc_test` not on PATH after S99 boot (binary lives at `/oem/usr/bin/mpi_enc_test`)
- 3A: not running. S99 cannot exec `rkaiq_3A_server` (same PATH). Coredumps from earlier session. IQ JSON is on disk; matching `.bin` is not
- Wi-Fi: no `wlan0`. RTSP reachability is USB ADB forward `tcp:8554`
- RAM: ~990 MB, no swap. Boot uptime was ~2 min at inspect (board had rebooted; clock is 1970)

## eMMC images this lock refers to
Flash only with `restore-camevision.ps1` (CameVision boot, not Aura kernel).

| LBA | name | file | sha256 prefix |
|-----|------|------|----------------|
| 0x0 | env | env.img | 65499dc7e1a8e203 |
| 0x40 | idblock | idblock.img | 48104dd4197ed183 |
| 0x440 | uboot | uboot.img | b9950b76bf2fa5ce |
| 0x2440 | boot | camevision_boot.img | 240918545aa22316 |
| 0x7C40 | userdata | aura-stock userdata.img (empty fs donor only) | b62ef1bd68294f64 |
| 0x207C40 | oem | oem_noko.img | 20c13c92ff215b78 |
| 0x607C40 | rootfs | rootfs_bootstable.img (S21 does not dd eMMC) | 2cd38c6d24a030e2 |

Full hashes: `MANIFEST.sha256`. Source copies stay in `known-good-20260819-camera-adb` plus `rootfs_bootstable.img`.

## Boot init (locked)
- S20: start S50 ADB **before** e2fsck/resize
- S21: log to `/tmp/cv.log` only — never `dd` to mmc LBA 33600
- S40: `ifup -a &`
- S50: ADB only (`usb_adb_en`), no UVC
- S99: sleep 12, then `/userdata/camevision-stream.sh`

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- `upgrade_tool db` twice in one Maskrom session
- Live USB gadget rebind (ADB → UVC)
- `insmod rockit`
- Feed NV12 to `mpi_enc_test` via fifo
- Hold BOOT after `rd`

## Next parts (not done in this lock)
1. PATH `/oem/usr/bin` so S99 finds `mpi_enc_test` and `rkaiq_3A_server`
2. IQ `.bin` for 3A
3. Host `adb forward tcp:8554 tcp:8554` after every USB replug
