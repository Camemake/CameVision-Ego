# Recovery 2 — CameVision Single — 2026-08-21 (Wi-Fi + BLE + IMU)

Second restore point. Recovery 1 is `restore/lock-20260821-rt52-adb-hwrtsp`.
This package is the **working** board config: ADB camera stream, LSM6 IMU on
SPI1, VS6621S80 Wi-Fi STA + BLE, Seekwave F26.26.3.1 firmware, RT52 modules.

Do not flash Luckfox Aura. Do not change the USB gadget. Do not wipe userdata
unless you also re-apply `overlay/` (kmpp, Wi-Fi kos, stream, firmware).

## Product
- Board: CameVision Single (same SoC family as M1)
- SoC: Rockchip RV1126B, 1 GB DDR4, Samsung eMMC
- USB gadget: ADB only, `2207:0006`, strings CameMake / CameVision Single
- Serial: `0558fa189447bc45`
- UDC `21500000.usb` state `configured`
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT` (bryan@tronlong, 2026-07-15)
- Wi-Fi/BT: VS6621S80 / SWT6621-S, SDIO `1FFE:6621`
- IMU: LSM6DSVQTR on SPI1 (`lsm6dsv_accel` / `lsm6dsv_gyro`)

## Proven live (2026-08-21)
- `wlan0` joins `Camemake R&D center` → `192.168.1.23`, ping gateway OK
- `hci0` UP RUNNING, Bluetooth 5.4, BD `60:48:9C:B9:D5:FF`
- IMU IIO devices present after `camevision_boot_wifi_imu.img`
- RTSP over ADB forward still works; do not bind UVC

## eMMC images (base flash)

Flash with `restore-camevision.ps1` from this folder. It does **not** write
empty Aura userdata.

| LBA | name | file |
|-----|------|------|
| 0x0 | env | `known-good-20260819-camera-adb/env.img` |
| 0x40 | idblock | `known-good-20260819-camera-adb/idblock.img` |
| 0x440 | uboot | `known-good-20260819-camera-adb/uboot.img` |
| 0x2440 | boot | `known-good-20260819-camera-adb/camevision_boot.img` then Wi-Fi/IMU boot |
| 0x207C40 | oem | `known-good-20260819-camera-adb/oem_noko.img` |
| 0x607C40 | rootfs | `known-good-20260819-camera-adb/rootfs_bootstable.img` |

After ADB is up:
1. `apply-overlay.ps1` — scripts, kmpp, Seekwave FW, RT52 Wi-Fi/BT kos
2. `flash-boot-wifi-imu.ps1` — SPI1 IMU + `wifi_chip_type=vs6621` DTB (reboots)

Or flash `camevision_boot_wifi_imu.img` from this folder instead of the stock
boot image if you already know Maskrom is safe.

## Overlay contents (`overlay/`)
- Init: S20 / S21 / S40 / S50 (ADB-only) / **S99** (IMU + Wi-Fi/BLE + stream)
- `/userdata/camevision-wifi.sh` — load RT52 stack, join WPA, bring up `hci0`
- `/userdata/camevision-imu.sh`, `imu-live.sh`
- `/userdata/swt6621.sh` — NPI AT over `/dev/ATC`
- `/userdata/wpa_camevision.conf` — SSID `Camemake R&D center`
- `/userdata/swt6621-rt52/*.ko` — real `6.1.141-rt52 preempt_rt` modules
- `/userdata/swt6621_fw/*` — Seekwave **F26.26.3.1** SDIO firmware
- `/userdata/kmpp-rt52.ko` — H.264 for RTSP
- `insmod_wifi.sh` on oem → exec `camevision-wifi.sh` (never rockit)

## Boot init
- S20: start S50 ADB **before** e2fsck/resize
- S21: log to `/tmp/cv.log` only — never `dd` to eMMC
- S40: `ifup -a &`
- S50: ADB only (`usb_adb_en`), no UVC
- S99: IMU (~8s), Wi-Fi+BLE (~10s), stream (~12s if `/dev/video13`)
- PATH: `/oem/usr/bin` via profile.d

## Host
```
adb -s 0558fa189447bc45 forward tcp:8554 tcp:8554
ffplay -rtsp_transport tcp rtsp://127.0.0.1:8554/live
```

Wi-Fi IP (when AP assigns): check `wpa_cli -i wlan0 status` on device.
RTSP can also be opened on the LAN IP once Wi-Fi is up.

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- `upgrade_tool db` twice in one Maskrom session
- Live USB gadget rebind (ADB → UVC) / boot-time UVC
- `insmod rockit`
- Use vermagic-patched Aura Wi-Fi kos (`wifi-rt52/*_rt52.ko`) — they need `__mutex_init`
- Hold BOOT after `rd`
- Wipe userdata without re-applying this overlay

## Restore
1. Fingers off BOOT. Hold BOOT, tap RESET, wait for Maskrom (`2207:110F`).
2. Run `restore-camevision.ps1`.
3. **Release BOOT completely.** Unplug/replug USB-C if needed, tap RESET only.
4. When ADB is `2207:0006`, run `apply-overlay.ps1`.
5. Run `flash-boot-wifi-imu.ps1` (or already flashed Wi-Fi/IMU boot).
6. After reboot: IMU + Wi-Fi + BLE + stream start from S99. Do not restart S50.
