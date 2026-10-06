# CameVision Ego · flash V0.2 (Maskrom)

Empty board, BSS84 already in Q1 (`WIFI.md`). USB stays **ADB**.

```
python tools/cv_ego_flash.py
```

Loader `db` once. CameVision images only — do not write Aura boot / oem / rootfs.

| LBA | Partition | File |
|---|---|---|
| 0x0 | env | `restore/known-good-20260819-camera-adb/env.img` |
| 0x40 | idblock | `restore/known-good-20260819-camera-adb/idblock.img` |
| 0x440 | uboot | `restore/known-good-20260819-camera-adb/uboot.img` |
| 0x2440 | boot | `camevision_boot_ego.img` (this folder) |
| 0x7C40 | userdata | Aura skeleton, then overlay after ADB |
| 0x207C40 | oem | `oem_noko.img` |
| 0x607C40 | rootfs | `rootfs_bootstable.img` |

Hold BOOT, tap RESET → Maskrom. After writes, **release BOOT**, then `rd`. Overlay deploy installs stereo, Wi-Fi STA, RTC `S11hwclock`, and pylib.

Board already on V0.2 / Recovery 5 (no Maskrom): `restore-v02.ps1` or `python tools/cv_ego_overlay_deploy.py`.
