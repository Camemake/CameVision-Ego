#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
r = subprocess.run(
    [
        ADB,
        "-s",
        S,
        "shell",
        "python3 -c \"import json;d=json.load(open('/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json'));e=d['main_scene'][0]['sub_scene'][0]['scene_isp35'];print('iq enh',e['enh']['en'],'ynr',e['ynr']['en'])\"; "
        "grep -E 'YNR|CNR|SHARP|ENH|GIC|CAC|DRC' /proc/rkisp-vir0",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout)
