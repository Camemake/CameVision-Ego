#!/usr/bin/env python3
"""Enable ISP DRC in the SC233HGS IQ (linear/knee path, not 2-frame merge)."""
import json
from pathlib import Path

src = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
dst = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\live\sc233hgs_efference-sc233hgs_drc.json")
d = json.loads(src.read_text(encoding="utf-8"))
isp = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]
isp["drc"]["en"] = 1
isp["drc"]["bypass"] = 0
# Keep Rockchip 2-frame merge off. This sensor is Knee Point HDR.
if "mge" in isp:
    isp["mge"]["en"] = 0
d["sensor_calib"]["CISHdrSet"]["hdr_en"] = 0
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print("wrote", dst, "bytes", dst.stat().st_size)
print("drc.en", isp["drc"]["en"], "mge.en", isp["mge"]["en"])
