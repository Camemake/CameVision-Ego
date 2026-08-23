#!/usr/bin/env python3
import subprocess
import urllib.request

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
r = subprocess.run(
    [
        ADB,
        "-s",
        S,
        "shell",
        "python3 -c \"import json;d=json.load(open('/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json'));print('oem drc',d['main_scene'][0]['sub_scene'][0]['scene_isp35']['drc']['en'])\"; "
        "grep DRC /proc/rkisp-vir0; ps | grep rkaiq_3A | grep -v grep",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout)
data = urllib.request.urlopen("http://127.0.0.1:8081/", timeout=8).read(200000)
print("jpeg", data.find(b"\xff\xd9") - data.find(b"\xff\xd8"))
