#!/usr/bin/env python3
"""Stock look, but AE protects windows. No DRC, no Knee HDR, no extra NR."""
import json
from pathlib import Path

src = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
dst = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\live\sc233hgs_efference-sc233hgs_backlight.json")
d = json.loads(src.read_text(encoding="utf-8"))
d["sensor_calib"]["CISHdrSet"]["hdr_en"] = 0
lin = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]["ae_calib"]["linAeCtrl"]
lin["initExp"]["sw_aeT_initTime_val"] = 0.008
lin["initExp"]["sw_aeT_initGain_val"] = 1.0
lin["backLightCtrl"]["sw_aeT_backLit_en"] = 1
lin["overExpCtrl"]["sw_aeT_overExp_en"] = 1
lin["route"]["sw_aeT_time_dot"] = [0, 0.002, 0.004, 0.005, 0.006, 0.006]
lin["route"]["sw_aeT_gain_dot"] = [1, 1, 1, 1, 2, 2]
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print("wrote", dst)
print("backlit", lin["backLightCtrl"]["sw_aeT_backLit_en"], "overexp", lin["overExpCtrl"]["sw_aeT_overExp_en"])
print("route time", lin["route"]["sw_aeT_time_dot"], "gain", lin["route"]["sw_aeT_gain_dot"])
