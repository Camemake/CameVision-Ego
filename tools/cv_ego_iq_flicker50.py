#!/usr/bin/env python3
"""Lock AE anti-flicker to 50 Hz (Europe mains).

Auto mode drops the lock in bright scenes, so LED lights beat against
the trigger. Normal 50 Hz keeps exposure on 10 ms steps. Frame-rate
hint is 30 (native SC233HGS). Live still triggers at 12.5 fps; record
raises the GPIO to 30. Max exposure 20 ms so 30 fps VTS still fits.
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
    r"\overlay\iqfiles\sc233hgs_camevision-sc233hgs_default.json"
)
OUT = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\tools\iqfiles\sc233hgs_camevision-sc233hgs_flicker50.json"
)
LIVE = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\build\live\sc233hgs_camevision-sc233hgs_flicker50.json"
)
NAME = "sc233hgs_camevision-sc233hgs_default.json"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def _iso_nodes(dyn: dict) -> list:
    iso = dyn.get("isoLink")
    if isinstance(iso, list):
        return [x for x in iso if isinstance(x, dict)]
    if isinstance(iso, dict):
        return [iso]
    return []


def tune_color(d: dict) -> None:
    """Cool the yellow security-cam look a bit: no CCM enhance, sat 90, +blue WB."""
    for scene in d.get("main_scene") or []:
        for sub in scene.get("sub_scene") or []:
            isp = sub.get("scene_isp35") or {}
            step = (isp.get("wb") or {}).get("awbGnCalcStep") or {}
            off = step.get("wbGainOffset")
            if isinstance(off, dict):
                off["offset_en"] = 1
                off["offset_val"] = [-0.12, 0.0, 0.0, 0.18]
            ccm = (isp.get("ccm") or {}).get("tunning") or {}
            for mode in ("stAuto", "stMan"):
                tun = ccm.get(mode) or {}
                dyn = tun.get("dyn") or {}
                if not isinstance(dyn, dict):
                    continue
                for iso in _iso_nodes(dyn):
                    enh = iso.get("enhance")
                    if isinstance(enh, dict):
                        enh["hw_ccmT_enhance_en"] = 0
                        enh["hw_ccmT_enhanceRat_maxLimit"] = 1.0
                for illu in dyn.get("illuLink") or []:
                    if not isinstance(illu, dict):
                        continue
                    curve = illu.get("gain2SatCurve") or {}
                    sats = curve.get("sw_ccmT_glbSat_val")
                    if isinstance(sats, list) and sats:
                        curve["sw_ccmT_glbSat_val"] = [90] * len(sats)


def patch(src: Path, dst: Path) -> None:
    d = json.loads(src.read_text(encoding="utf-8"))
    time_dot = [0.01, 0.012, 0.014, 0.016, 0.018, 0.02]
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
            "sw_aeT_frmRate_val": 30,
        }
        lin = ae["linAeCtrl"]
        lin["initExp"]["sw_aeT_initTime_val"] = 0.02
        lin["route"]["sw_aeT_time_dot"] = list(time_dot)
        lin["route"]["sw_aeT_gain_dot"] = [1, 1, 2, 4, 8, 16]
    tune_color(d)
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
        "c=d['main_scene'][0]['sub_scene'][0]['scene_isp35']; "
        "print(c['ae_calib']['commCtrl']['antiFlicker']); "
        "print(c['ae_calib']['commCtrl']['frmRate']); "
        "print('offset', c['wb']['awbGnCalcStep']['wbGainOffset']); "
        "print('enh', c['ccm']['tunning']['stAuto']['dyn']['isoLink'][0]['enhance']); "
        "print('sat', c['ccm']['tunning']['stAuto']['dyn']['illuLink'][0]['gain2SatCurve']['sw_ccmT_glbSat_val'][:2])\"; "
        "echo === exp ===; "
        "v4l2-ctl -d /dev/v4l-subdev10 -C exposure -C analogue_gain; "
        "v4l2-ctl -d /dev/v4l-subdev5 -C exposure -C analogue_gain; "
        "echo === log ===; grep -E 'ERR|error|fail|antiFlick' /userdata/rkaiq.log | tail -8"
        % NAME,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
