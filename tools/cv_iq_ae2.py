#!/usr/bin/env python3
import json
from pathlib import Path

p = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
d = json.loads(p.read_text(encoding="utf-8"))
lin = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]["ae_calib"]["linAeCtrl"]
print(json.dumps({k: lin[k] for k in lin if k != "route"}, indent=2)[:4000])
print("--- keys", list(lin.keys()))
print("--- backLit", json.dumps(lin["backLightCtrl"], indent=2)[:2500])
if "overExpCtrl" in lin:
    print("--- overExp", json.dumps(lin["overExpCtrl"], indent=2)[:2000])
