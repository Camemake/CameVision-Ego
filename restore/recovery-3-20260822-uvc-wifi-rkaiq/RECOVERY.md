# Recovery 3 — CameVision Single — 2026-08-22 (UVC + Wi-Fi + RKAIQ)

Third restore point. Recovery 2 is `restore/recovery-2-20260821-adb-stream`
(ADB USB + RTSP). Recovery 1 is `restore/lock-20260821-rt52-adb-hwrtsp`.

This package is the **working camera stack**: USB webcam **CameVision Single**,
Wi-Fi STA for debug, RKISP mainpath, standalone RKAIQ 3A, MJPEG pump.

Do not flash Luckfox Aura. Do not wipe userdata unless you also re-apply
`overlay/` (kmpp, Wi-Fi kos, IQ helper, UVC pump).

## Product
- Board: CameVision Single, Rockchip RV1126B, 1 GB DDR4, Samsung eMMC
- USB gadget: UVC only, VID `0x2207` PID `0x0016`, serial `CVSingle`
- Strings: CameMake / **CameVision Single**
- One format: MJPEG 1920×1080 @ 15 (`dwFrameInterval` 666666), `streaming_maxpacket=3072`
- UVC node: `/dev/video28`
- Debug: busybox telnetd root on `wlan0:2323` (typically `192.168.1.23`)
- Kernel: `6.1.141-rt52` `#24 SMP PREEMPT_RT`
- Sensor: SC233HGS i2c `3-0030`, ISP35 `rkisp0` `/dev/media2`
- RKISP mainpath `/dev/video13` NV12 1920×1080 (scaler) while 3A runs
- IQ: `sc233hgs_efference-sc233hgs_default.json` (live DT module `efference-sc233hgs`)
- Wi-Fi/BT: VS6621S80 / SWT6621-S, SDIO `1FFE:6621`
- IMU: LSM6DSVQTR on SPI1

## Proven live (2026-08-22)
- `wlan0` joins `Camemake R&D center` → `192.168.1.23`
- `rkaiq_3A_server --silent` → `sysctl_init/prepare/start` success
- `rkaiq_tool_server` connects to AIQ
- UVC gadget bound, pump waits for host STREAMON (never STREAMOFF per frame)
- Windows Camera: pick **CameVision Single**, MJPEG 1920×1080
- After a live ADB→UVC switch, unplug/replug USB-C so Windows re-enumerates

## eMMC images (base flash)

Flash with `restore-camevision.ps1`. It does **not** write userdata or oem
(IQ on `/oem`, kmpp/Wi-Fi kos on `/userdata`).

| LBA | name | file |
|-----|------|------|
| 0x0 | env | `known-good-20260819-camera-adb/env.img` |
| 0x40 | idblock | `known-good-20260819-camera-adb/idblock.img` |
| 0x440 | uboot | `known-good-20260819-camera-adb/uboot.img` |
| 0x2440 | boot | `known-good-20260819-camera-adb/camevision_boot.img` |
| 0x607C40 | rootfs | `known-good-20260819-camera-adb/rootfs_bootstable.img` |

Rootfs boots **ADB** (`2207:0006`) so overlay can be pushed. Overlay then
installs UVC S50. Wi-Fi/IMU DTB: `flash-boot-wifi-imu.ps1` after ADB is up.

## Overlay (`overlay/`)
- S20 / S21 / S40 — same as recovery 2 (S20 starts S50 before e2fsck)
- **S50** — UVC gadget only, telnetd `:2323`, **no dwc3 unbind**, no ISP
- `S50usbdevice.adb` — emergency ADB gadget (do not install as boot S50 unless recovering)
- **S99** — LED, IMU, Wi-Fi, RKAIQ, then UVC cam if `/userdata/uvc-webcam.on`
- `camevision-uvc-cam.sh` — RKISP FIFO + `camevision-uvc-mjpg.py` (keep STREAMON)
- `camevision-aiq.sh` — IQ install + `rkaiq_3A_server` + tool server
- `camevision-wifi.sh` + `swt6621-rt52/*.ko` + `swt6621_fw/*` F26.26.3.1
- `kmpp-rt52.ko` — JPEG/H.264 (`mpi_enc_test`)
- `iqfiles/sc233hgs_efference-sc233hgs_default.json`

## Boot init
- S50: telnetd immediately; after ~6s bind UVC (background so S99 starts)
- S99: IMU ~8s, Wi-Fi ~6s, AIQ ~10s, UVC cam ~14s
- PATH `/oem/usr/bin` via `profile.d/camevision.sh`

## Host
Debug (Wi-Fi):
```
python tools/cv_telnet.py "ps | grep -E 'rkaiq_3A|uvc-mjpg|v4l2-ctl'"
```

Camera: Windows Camera → **CameVision Single**. If the PC still shows ADB
or nothing after a gadget change, unplug USB-C 2s and plug back in.

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- `upgrade_tool db` twice in one Maskrom session
- Live ADB→UVC rebind (Windows will not see the new device)
- dwc3 unbind + ISP STREAMON in the same S50 (kernel panic)
- `camevision-uvc-h264.py` (STREAMOFF every frame)
- `isp_grab.py` burst `timeout 1 v4l2-ctl` (wedges `/dev/video13`)
- `insmod rockit` / `rk_mpi_uvc` (needs `/dev/mpi/vlog`)
- Hold BOOT after `rd`
- Extra leftover `S50usbdevice.*` in `/etc/init.d` (`rcS` runs `S??*`)

## Restore
1. Fingers off BOOT. Hold BOOT, tap RESET, wait for Maskrom (`2207:110F`).
2. Run `restore-camevision.ps1`.
3. **Release BOOT completely.** Tap RESET only if USB stays empty.
4. When ADB is `2207:0006`, run `apply-overlay.ps1` (does not restart USB).
5. Run `flash-boot-wifi-imu.ps1` if `wlan0` never appears (reboots).
6. Reboot once so UVC S50 is the gadget. Debug on Wi-Fi `:2323`.
7. Unplug/replug USB-C, open Windows Camera → CameVision Single.

Fallback USB: copy `overlay/S50usbdevice.adb` to `/etc/init.d/S50usbdevice`
over telnet, reboot. That is Recovery 2 USB behavior.
