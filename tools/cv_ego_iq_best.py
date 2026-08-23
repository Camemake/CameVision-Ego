#!/usr/bin/env python3
"""Linear IQ: denoise/sharpen/enhance on. Knee HDR, DRC, and 2-frame merge stay off."""
import json
from pathlib import Path

src = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
dst = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\live\sc233hgs_efference-sc233hgs_best.json")

d = json.loads(src.read_text(encoding="utf-8"))
d["sensor_calib"]["CISHdrSet"]["hdr_en"] = 0

isp = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]
on = ("ynr", "cnr", "sharp", "gic", "cac")
off = ("drc", "mge", "bayertnr", "histEQ", "enh", "aibnr", "airms", "aiynr")
for name in on:
    isp[name]["en"] = 1
    isp[name]["bypass"] = 0
    if isp[name].get("opMode") == "RK_AIQ_OP_MODE_MANUAL":
        isp[name]["opMode"] = "RK_AIQ_OP_MODE_AUTO"
for name in off:
    isp[name]["en"] = 0

dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print("wrote", dst, dst.stat().st_size)
for name in list(on) + list(off):
    print(name, "en", isp[name]["en"])
