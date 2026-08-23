#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
python3 /tmp/ego_hdr_off.py
killall rkaiq_tool_server 2>/dev/null
if ! ps | grep -q '[r]kaiq_3A_server'; then
  sh /userdata/camevision-aiq.sh
  killall rkaiq_tool_server 2>/dev/null
fi
echo === 3282 ===
python3 -c "import fcntl,os; F=0x0706
def rd(b,r):
 fd=os.open('/dev/i2c-%d'%b,os.O_RDWR); fcntl.ioctl(fd,F,0x30); os.write(fd,bytes([r>>8,r&255])); v=os.read(fd,1)[0]; os.close(fd); return v
print('cam0',hex(rd(3,0x3282))); print('cam1',hex(rd(6,0x3282)))"
echo === ps ===
ps | grep -E 'rkaiq_3A|ego_mjpeg' | grep -v grep
echo === drc ===
grep DRC /proc/rkisp-vir0
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=30)
print(r.stdout)
print(r.stderr)
