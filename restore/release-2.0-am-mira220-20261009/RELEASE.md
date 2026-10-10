# CameVision EGO AM · MIRA220 · flash 2.0 — 9 October 2026

This folder is the **AM / MIRA220** Maskrom kit. It is **not** the SC233HGS
V0.2 kit (`restore/release-0.2-20260902`). Do not flash one onto the other.

Hardware: CameVisionEgo_AM V0.3, dual AMS MIRA220 (1600×1400 RAW10, color,
SGRBG), microSD rail **+3.3V_SDC_PWR**. USB stays **ADB**.

```
python tools/cv_ego_flash_am.py
```

Already running:

```
python tools/cv_ego_overlay_deploy_am.py
```

| Partition | Image |
|---|---|
| env / idblock / uboot | same RV1126B SPL set as V0.2 (copied here) |
| boot | `camevision_boot_ego_am.img` (MIRA220 DTB, 3.3 V SD) |
| userdata | AM overlay (CIF stereo, mira modules, MIRA220 IQ) |
| oem / rootfs | CameVision `oem_noko.img` / `rootfs_bootstable.img` |

Overlay:

- Stereo page `:8081` — CIF RAW10, 1400×1600 view, jet depth
- IMU HUD `:8083`
- `S10mira220` — mira220 + ciflate + miralink + mfix4 + mstart
- `S99ego-stereo` — AM stereo start (no rkaiq 3A)
- IQ `mira220_camevision-mira220_default.json`

## Do not

- Flash this kit onto a SC233HGS board
- Use `tools/cv_ego_flash.py` (that is V0.2 SC233HGS)
- Switch USB to a webcam gadget
