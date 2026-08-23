#!/usr/bin/env python3
import json
from pathlib import Path

p = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
d = json.loads(p.read_text(encoding="utf-8"))
lin = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]["ae_calib"]["linAeCtrl"]
print(json.dumps(lin["route"], indent=2)[:3500])
