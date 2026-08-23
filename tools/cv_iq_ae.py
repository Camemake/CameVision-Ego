#!/usr/bin/env python3
import json
from pathlib import Path

p = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-3-20260822-uvc-wifi-rkaiq"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
d = json.loads(p.read_text(encoding="utf-8"))
ae = d["main_scene"][0]["sub_scene"][0]["scene_isp35"]["ae_calib"]


def walk(o, pref=""):
    if isinstance(o, dict):
        for k, v in o.items():
            kl = k.lower()
            if any(
                x in kl
                for x in (
                    "luma",
                    "target",
                    "bias",
                    "back",
                    "hist",
                    "ev",
                    "weight",
                    "strategy",
                    "hl",
                    "highlight",
                    "dark",
                    "env",
                )
            ):
                if isinstance(v, (dict, list)):
                    print(pref + k, type(v).__name__, end=" ")
                    if isinstance(v, dict):
                        print(list(v.keys())[:16])
                    else:
                        print("len", len(v), v[:8] if v and not isinstance(v[0], (dict, list)) else "")
                else:
                    print(pref + k, "=", v)
            if isinstance(v, (dict, list)) and any(
                x in kl for x in ("lin", "hdr", "ctrl", "route", "weight", "env", "hist")
            ):
                walk(v, pref + k + ".")
    elif isinstance(o, list) and o and isinstance(o[0], dict):
        walk(o[0], pref + "[0].")


print("ae top", list(ae.keys()))
walk(ae)
