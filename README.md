# CameVision Ego

On-board stereo for **CameVision Ego V1.I1** (Rockchip RV1126B, dual SC233HGS).

**Release 1** (2026-08-24) is the baseline: `restore/release-1-20260824`.

The live page starts on the board at boot. USB stays **ADB**. On this PC the watcher
`python tools/cv_ego_autostart.py --install` deploys, starts the service if needed,
and restores `http://127.0.0.1:8081/` every time you plug in (also at Windows logon).

Manual once: `python tools/cv_ego_page.py`  
First-time / full push: `python tools/cv_ego_stereo_start.py`

Do not flash Luckfox Aura. Do not reboot into UVC.

- Live: http://127.0.0.1:8081/
- Calibrate: http://127.0.0.1:8081/cal

Board notes and restore history: [EGO.md](EGO.md).
