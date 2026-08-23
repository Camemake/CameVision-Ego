#!/usr/bin/env python3
import json, sys
from pathlib import Path
p = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb\overlay\sc233hgs_efference-sc233hgs_default.json")
d = json.load(p.open(encoding="utf-8"))
print("TOP", list(d.keys()))
for k in ("sensor_calib","module_calib","sys_static_cfg"):
    v = d.get(k)
    print("====", k, type(v).__name__)
    if isinstance(v, dict):
        for kk,vv in v.items():
            if isinstance(vv,(dict,list)):
                print(" ", kk, type(vv).__name__, (list(vv)[:12] if isinstance(vv,dict) else len(vv)))
            else:
                print(" ", kk, vv)
print("main_scene_len", d.get("main_scene_len"))
ms = d.get("main_scene")
if isinstance(ms, list) and ms:
    print("scene0 keys", list(ms[0])[:20] if isinstance(ms[0],dict) else type(ms[0]))
    if isinstance(ms[0], dict):
        for kk,vv in list(ms[0].items())[:15]:
            if not isinstance(vv,(dict,list)):
                print("  scene0", kk, vv)
            else:
                print("  scene0", kk, type(vv).__name__)
