# Release 1 — CameVision Ego — 2026-08-24

This is the **baseline** to continue from. USB stays **ADB**. Software
overlay on Recovery 5. It does **not** flash boot, rootfs, or oem.

Do not flash Luckfox Aura. Do not reboot this board into UVC.

## Product
- Board: CameVision Ego V1.I1, Rockchip RV1126B
- Sensors: SmartSens SC233HGS ×2, LSM6DSVQTR ×2
- USB gadget: ADB. Serials: `4857b9cbd0b99e0b`, `53feb42973ff9142`
- Live: http://127.0.0.1:8081/
- Calibrate: http://127.0.0.1:8081/cal
- IMU HUD: http://127.0.0.1:8083/ (also `/imu` on 8081)

The stereo web service starts on the **board** at boot (`S99ego-stereo` →
`/userdata/camevision-stereo.sh`). USB stays ADB, so the **host** must restore
port forwards after every plug. Install once on the PC:

```
python tools/cv_ego_autostart.py --install
```

That watcher deploys the overlay, starts the service if it is down, forwards
8081/8083, and opens the page whenever an Ego appears.

## Proven in this release
- Dual ISP colour (AWB / CCM / gamma on). 3A reattaches if a grab restart drops it.
- Hardware FSYNC/EFSYNC: both eyes triggered together at **12.5 fps** (50 Hz aligned).
- AE anti-flicker **50 Hz normal**, exposure locked on 20 ms steps.
- On-board SGBM depth, 640×400 grid, jet heatmap. Depth CSS `scale(-1,-1)` is the correct view.
- Display: left pane `/ov1` LEFT CAM1 IMU1, right pane `/ov0` RIGHT CAM0 IMU0. Do not swap eyes.
- Checkerboard calibration at `/cal`. IMU HUD left running.

## Overlay

| What | File |
|---|---|
| Stereo + web + cal | `overlay/ego_stereo.py` |
| FSYNC / EFSYNC trigger | `overlay/ego_cam_sync.py` |
| Calibration page | `overlay/ego_calib.html` |
| IMU HUD | `overlay/ego_imu_hud.py` |
| Native matcher | `overlay/libego_stereo.so` |
| Matcher source | `overlay/stereo_native.c` |
| 50 Hz IQ | `overlay/iqfiles/sc233hgs_efference-sc233hgs_default.json` |
| Boot start | `overlay/camevision-stereo.sh`, `overlay/S99ego-stereo` |
| Deploy from host | `overlay/cv_ego_stereo_start.py` |
| Auto page on plug | `overlay/cv_ego_autostart.py` (`--install` at Windows logon) |
| Manual forwards | `overlay/cv_ego_page.py` |

Python wheels stay on the board at `/userdata/pylib`. This pack does not reinstall them.

## Restore (board already on Recovery 5 + ADB)

From the project root:

```
python tools/cv_ego_stereo_start.py
python tools/cv_ego_autostart.py --install
```

or `restore-release1.ps1` in this folder. After `--install`, plugging USB is enough.

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- Reboot Ego into UVC
- Kill `rkaiq_3A_server` or `ego_imu_hud.py` unless ISP blocks are off
- Change depth CSS orientation or matcher eye order
- Reuse Single's GPIO4_A2 / GPIO4_A7 for sync (those are CAM1 PWDN and I2C4 SDA on Ego)
