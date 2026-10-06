# CameVision EGO · flash V0.2

**CV-EGO01-OS** · CameVision Ego V1.I1 · 2 September 2026

Working **Maskrom flash** for an empty board (BSS84 in Q1). USB stays ADB. Stereo, Wi-Fi STA and RV-3028 RTC start on the camera.

- **Buy CameVision EGO:** https://www.camemake.eu/shop/cv-ego01-os-camevision-ego-dual-global-shutter-ai-stereo-camera-2414
- **Camemake robotic solutions:** https://www.camemake.eu/robotic-solutions
- **Product page:** https://camemake.github.io/CameVision-Ego/
- **Repository:** https://github.com/Camemake/CameVision-Ego

## What's in this flash

- Live stereo page at `http://127.0.0.1:8081/`
- Checkerboard calibration at `http://127.0.0.1:8081/cal`
- IMU HUD at `http://127.0.0.1:8083/`
- Hardware frame sync, 50 Hz lighting lock, on-board SGBM depth
- Wi-Fi STA on boot (`camevision-wifi.sh`, rt52) after SDIO `1FFE:6621`
- RV-3028 trickle (3 kΩ) + `S11hwclock` so a power cut is not 1970
- USB stays the Camemake developer gadget (ADB)

## Empty board

Hardware: Q1 = **BSS84LT1G** (`WIFI.md`). Then from the repository:

```
python tools/cv_ego_flash.py
```

Proven on `762177b8194fb1b0`.

## Already running

```
python tools/cv_ego_overlay_deploy.py
python tools/cv_ego_autostart.py --install
```

Or `restore-v02.ps1` in this folder.

## Do not

- Flash Aura boot / oem / rootfs
- Switch USB to a webcam gadget
- Skip the BSS84 Q1 rework

© Camemake · CameVision EGO · CV-EGO01-OS
