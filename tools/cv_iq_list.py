#!/usr/bin/env python3
import json
from pathlib import Path

p = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
d = json.loads(p.read_text(encoding="utf-8"))
isp = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]
for k in sorted(isp):
    v = isp[k]
    if isinstance(v, dict) and "en" in v:
        print(f"{k:12} en={v.get('en')} op={v.get('opMode')} bypass={v.get('bypass')}")
