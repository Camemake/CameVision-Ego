#!/usr/bin/env python3
import json
from pathlib import Path
p = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb\overlay\sc233hgs_efference-sc233hgs_default.json")
d = json.load(p.open(encoding="utf-8"))
print("resolution", d["sensor_calib"]["resolution"])
print("CISMinFps", d["sensor_calib"].get("CISMinFps"))
print("CISFlip", d["sensor_calib"].get("CISFlip"))
print("iso_list", d["sensor_calib"].get("iso_list"))
print("module", d["module_calib"])
print("algoSwitch", d["sys_static_cfg"])
print("scenes", [(s.get("name"), s.get("sub_scene_len")) for s in d["main_scene"]])
sub = d["main_scene"][0]["sub_scene"][0]
print("sub0 keys", list(sub.keys()) if isinstance(sub, dict) else type(sub))
if isinstance(sub, dict):
    print("sub0 name", sub.get("name"))
    mods = sub.get("module_data") or sub.get("CalibDbV2") or sub
    if "module_data" in sub:
        md = sub["module_data"]
        print("module_data type", type(md).__name__, list(md)[:40] if isinstance(md, dict) else getattr(md, "__len__", lambda:0)())
    else:
        print("top-level scene modules:")
        for k,v in sub.items():
            if isinstance(v, dict):
                print(" ", k, list(v)[:8])
            elif not isinstance(v, list):
                print(" ", k, v)
