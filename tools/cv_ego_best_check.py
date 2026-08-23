#!/usr/bin/env python3
import subprocess
import time

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"


def sh(cmd: str, timeout: int = 30) -> str:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    print(out, end="" if out.endswith("\n") else "\n")
    return out


print("=== oem flags ===")
sh(
    "python3 -c \""
    "import json;"
    "d=json.load(open('/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json'));"
    "isp=d['main_scene'][0]['sub_scene'][0]['scene_isp35'];"
    "print('ynr',isp['ynr']['en'],'cnr',isp['cnr']['en'],'sharp',isp['sharp']['en'],"
    "'enh',isp['enh']['en'],'gic',isp['gic']['en'],'cac',isp['cac']['en'],'drc',isp['drc']['en'])"
    "\""
)
print("=== start 3A ===")
sh(
    "killall rkaiq_tool_server 2>/dev/null; "
    "if ! ps | grep -q '[r]kaiq_3A_server'; then "
    "  export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
    "  export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH; "
    "  setsid nohup rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 & "
    "  echo started $!; "
    "fi"
)
time.sleep(3)
sh("ps | grep rkaiq_3A | grep -v grep; echo === hw ===; grep -E 'YNR|CNR|SHARP|ENH|GIC|CAC|DRC' /proc/rkisp-vir0")
