# CameVision Ego AM / MIRA220 · Maskrom flash

Empty AM board. USB stays **ADB**.

```
python tools/cv_ego_flash_am.py
```

| LBA | Partition | File |
|---|---|---|
| loader (`db` once) | SPL | `rv1126b_spl_loader_k4a8g.bin` |
| 0x0 | env | `env.img` |
| 0x40 | idblock | `idblock.img` |
| 0x440 | uboot | `uboot.img` |
| 0x2440 | boot | `camevision_boot_ego_am.img` |
| 0x7C40 | userdata | `userdata.img` |
| 0x207C40 | oem | `oem_noko.img` |
| 0x607C40 | rootfs | `rootfs_bootstable.img` |

Hold BOOT, tap RESET → Maskrom. Release BOOT after writes. Overlay deploy
installs MIRA220 modules, CIF stereo, and pylib.

Board already running AM: `restore-am.ps1` or `python tools/cv_ego_overlay_deploy_am.py`.
