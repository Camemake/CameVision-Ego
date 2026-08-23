# Recovery 6 — CameVision Ego — 2026-08-23 (stereo depth)

Working **on-board stereo depth** restore point. USB stays **ADB**.
This is a software overlay on top of Recovery 5. It does **not** flash
boot, rootfs, or oem. 3A and IMU stay running.

Do not flash Luckfox Aura. Do not reboot this board into UVC.

## Product
- Board: CameVision Ego V1.I1, Rockchip RV1126B
- Sensors: SmartSens SC233HGS ×2
- USB gadget: ADB, serial `4857b9cbd0b99e0b`
- Page: http://127.0.0.1:8081/
- Calibrate: http://127.0.0.1:8081/cal

## What this restore contains
On-device stereo matching (OpenCV SGBM, coarse-to-fine), live 1920×1200
heatmap, checkerboard calibration page, IMU HUD left running.

Proven on 2026-08-23 after the upright-match + epipolar-align + hierarchical
refine work:

- Grid: 384×240, search 64 px, near limit ~0.30 m
- Coarse SGBM on 192×120, then local refine at full grid
- Alignment residual ~0.25–0.36 px (pooled ORB, quadratic surface)
- Depth ~6 fps, heatmap ~6 fps, colour previews ~7 fps
- Page HUD: matcher, grid, matched %, align residual

## Overlay

| What | File |
|---|---|
| Stereo + web + cal | `overlay/ego_stereo.py` |
| Calibration page | `overlay/ego_calib.html` |
| IMU HUD (leave running) | `overlay/ego_imu_hud.py` |
| Native matcher | `overlay/libego_stereo.so` |
| Matcher source | `overlay/stereo_native.c` |
| Deploy from host | `overlay/cv_ego_stereo_start.py` |
| Native rebuild | `overlay/cv_ego_build_stereo.py` |

Python wheels stay on the board at `/userdata/pylib` (numpy, OpenCV,
TurboJPEG). This pack does not reinstall them.

## Restore stereo only (board already on Recovery 5 + ADB)

From the project root:

```
python tools/cv_ego_stereo_start.py
```

or `restore-stereo.ps1` in this folder. USB must stay ADB.

Optional: refit eye alignment on a textured scene:

```
http://127.0.0.1:8081/align
```

## Do not
- Flash Luckfox Aura `boot.img` / `rootfs.img` / `oem.img`
- Reboot Ego into UVC
- Kill `rkaiq_3A_server` or `ego_imu_hud.py`
- Roll the board back to Recovery 4 or earlier unless cameras themselves fail
- Expect 30 fps depth: there is no hardware JPEG encoder; three 1920×1200
  software encodes share four cores
