#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
python3 /tmp/ego_i2c_rd.py
echo === iq drc ===
python3 -c "import json; d=json.load(open('/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json')); isp=d['main_scene'][0]['sub_scene'][0]['scene_isp35']; print('oem drc', isp['drc']['en'], 'mge', isp['mge']['en']); d2=json.load(open('/etc/iqfiles/sc233hgs_efference-sc233hgs_default.json')); isp2=d2['main_scene'][0]['sub_scene'][0]['scene_isp35']; print('etc drc', isp2['drc']['en'])"
echo === 3A ===
ps | grep rkaiq_3A | grep -v grep
echo === drc hw ===
grep -E 'DRC|HDRMGE' /proc/rkisp-vir0
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=25)
print(r.stdout)
print(r.stderr)
