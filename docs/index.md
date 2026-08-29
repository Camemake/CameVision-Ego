---
title: CameVision EGO
---

<p align="center">
  <img src="https://raw.githubusercontent.com/Camemake/CameVision-Ego/main/tools/camemake-logo.png" alt="Camemake" width="260">
</p>

# CameVision EGO

**CV-EGO01-OS** — dual global-shutter AI stereo camera from [Camemake](https://www.camemake.eu).

Open stereo vision platform for SLAM, robotics, VIO and spatial AI. Stereo, depth and calibration run **on the camera**.

- **[Buy CameVision EGO](https://www.camemake.eu/shop/cv-ego01-os-camevision-ego-dual-global-shutter-ai-stereo-camera-2414)** — webshop listing, pricing and customisation
- **[Camemake robotic solutions](https://www.camemake.eu/robotic-solutions)** — single / double / triple / 5-fold / 9-camera ODM PCBs, headset, cap, helmet, backpack and gripper
- **[Full repository README](https://github.com/Camemake/CameVision-Ego#readme)** — install, live page, Release 1, GPIO map

| | |
|---|---|
| Cameras | 2 × 2.3 MP global shutter, hardware-synchronised |
| IMU | One IMU per camera |
| Compute | On-board vision SoC + NPU |
| Memory / storage | 1 GB RAM · 16 GB eMMC + microSD |
| I/O | USB-C · Wi-Fi 6 · BLE · battery pads |
| Demo | Live stereo `http://127.0.0.1:8081/` after USB plug |

```
python tools/cv_ego_stereo_start.py
python tools/cv_ego_autostart.py --install
```

© Camemake · [sales@camemake.com](mailto:sales@camemake.com)
