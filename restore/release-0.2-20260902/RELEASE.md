# CameVision EGO · flash V0.2 — 2 September 2026

Working **empty-board Maskrom flash**. USB stays **ADB**. Product:
[CameVision EGO · CV-EGO01-OS](https://www.camemake.eu/shop/cv-ego01-os-camevision-ego-dual-global-shutter-ai-stereo-camera-2414).

Hardware: CameVision Ego V1.I1 with **BSS84LT1G** in Q1 (`WIFI.md`).
Proven on `762177b8194fb1b0`.

```
python tools/cv_ego_flash.py
```

## What V0.2 writes

| Partition | Image |
|---|---|
| env / idblock / uboot | `restore/known-good-20260819-camera-adb` |
| boot | `camevision_boot_ego.img` in this folder (Wi-Fi DTB + RV-3028 trickle) |
| userdata | Aura skeleton, then overlay (below) |
| oem / rootfs | `oem_noko.img` / `rootfs_bootstable.img` (CameVision) |

Boot FIT (vs Recovery 5):

- VS6621 pwrseq GPIO3_B2 `ACTIVE_HIGH`, 200 ms, INT B7, HOST_WAKE B6, BT off B2
- RV-3028 trickle 3 kΩ + backup switchover (C99 11 mF on `V_BKUP`) so a power cut is not 1970
- USB `dr_mode` peripheral (ADB)

Overlay installed after ADB comes up:

- Stereo page `:8081`, IMU HUD `:8083`, 50 Hz IQ, native matcher
- Wi-Fi STA on boot (`camevision-wifi.sh` + rt52 kos) → `Camemake R&D center`
- `S11hwclock` — load/store RV-3028
- `S99ego-stereo` — stereo + Wi-Fi
- numpy / OpenCV in `/userdata/pylib` when `build/wheels` is present

| What | File |
|---|---|
| Boot FIT | `camevision_boot_ego.img` |
| Stereo + web + cal | `overlay/ego_stereo.py` |
| Native matcher | `overlay/libego_stereo.so` |
| Boot start | `overlay/camevision-stereo.sh`, `overlay/S99ego-stereo` |
| Wi-Fi STA | `overlay/camevision-wifi.sh`, `overlay/wpa_camevision.conf`, `overlay/swt6621-rt52`, `overlay/swt6621_fw` |
| RTC | `overlay/S11hwclock` |
| 50 Hz IQ | `overlay/iqfiles/sc233hgs_camevision-sc233hgs_default.json` |

## Do not

- Flash Aura boot / oem / rootfs
- Switch USB to a webcam gadget
- Skip the BSS84 Q1 rework
