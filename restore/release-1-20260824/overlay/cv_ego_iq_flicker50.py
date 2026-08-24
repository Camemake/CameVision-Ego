#!/usr/bin/env python3
"""Lock AE anti-flicker to 50 Hz (Europe mains).

Auto mode drops the lock in bright scenes, so LED lights beat against
the 15 fps / 13.95 Hz trigger. Normal 50 Hz keeps exposure on 10 ms
steps. Frame-rate hint is 15 to match the sensor VTS, not 30.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
SRC = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\restore\recovery-5-20260823-imaging-adb"
    r"\overlay\iqfiles\sc233hgs_efference-sc233hgs_default.json"
)
OUT = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\tools\iqfiles\sc233hgs_efference-sc233hgs_flicker50.json"
)
LIVE = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\build\live\sc233hgs_efference-sc233hgs_flicker50.json"
)
NAME = "sc233hgs_efference-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def patch(src: Path, dst: Path) -> None:
    d = json.loads(src.read_text(encoding="utf-8"))
    time_dot = [0.02, 0.03, 0.04, 0.05, 0.06, 0.066]
    for scene in d.get("main_scene") or []:
        ae = scene["sub_scene"][0]["scene_isp35"]["ae_calib"]
        ctrl = ae["commCtrl"]
        ctrl["antiFlicker"] = {
            "sw_aeT_antiFlicker_en": 1,
            "sw_aeT_antiFlicker_freq": "ae_antiFlicker_50hz_freq",
            "sw_aeT_antiFlicker_mode": "ae_antiFlicker_normal_mode",
        }
        ctrl["frmRate"] = {
            "sw_aeT_frmRate_mode": "ae_frmRate_fix_mode",
            "sw_aeT_frmRate_val": 15,
        }
        lin = ae["linAeCtrl"]
        lin["initExp"]["sw_aeT_initTime_val"] = 0.02
        lin["route"]["sw_aeT_time_dot"] = list(time_dot)
        lin["route"]["sw_aeT_gain_dot"] = [1, 1, 1, 1, 2, 4]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print("wrote", dst, dst.stat().st_size)
    if dst != LIVE:
        LIVE.parent.mkdir(parents=True, exist_ok=True)
        LIVE.write_bytes(dst.read_bytes())


def sh(s: str, cmd: str, timeout: int = 35) -> str:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    text = (r.stdout or "") + (r.stderr or "")
    print(text, end="" if text.endswith("\n") else "\n")
    return text


def main() -> int:
    patch(SRC, OUT)
    s = serial()
    subprocess.run([ADB, "-s", s, "push", str(OUT), "/userdata/iqfiles/" + NAME], check=True)
    sh(
        s,
        "cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s 2>/dev/null || "
        "(mount -o remount,rw /oem && cp -f /userdata/iqfiles/%s /oem/usr/share/iqfiles/%s); "
        "export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH; "
        "killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null; "
        "start-stop-daemon -S -b -m -p /userdata/rkaiq.pid -x /oem/usr/bin/rkaiq_3A_server -- --silent"
        % (NAME, NAME, NAME, NAME),
    )
    time.sleep(4)
    sh(
        s,
        "echo === 3A ===; ps | grep rkaiq_3A | grep -v grep; "
        "echo === iq ===; python3 -c \""
        "import json; d=json.load(open('/userdata/iqfiles/%s')); "
        "c=d['main_scene'][0]['sub_scene'][0]['scene_isp35']['ae_calib']['commCtrl']; "
        "print(c['antiFlicker']); print(c['frmRate'])\"; "
        "echo === exp ===; "
        "v4l2-ctl -d /dev/v4l-subdev10 -C exposure -C analogue_gain; "
        "v4l2-ctl -d /dev/v4l-subdev5 -C exposure -C analogue_gain; "
        "echo === log ===; grep -E 'ERR|error|fail|antiFlick' /userdata/rkaiq.log | tail -8"
        % NAME,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
