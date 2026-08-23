#!/usr/bin/env python3
"""Drive GPIO3_B2 low (P-MOS Q1 on if the GPIO is the gate) and rescan mmc2."""
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = r"""
python3 - <<'PY'
import mmap,os,struct,time
GPIO3=0x21E00000
LO=0x04000000
fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)
m=mmap.mmap(fd,0x80,mmap.MAP_SHARED,mmap.PROT_WRITE|mmap.PROT_READ,offset=GPIO3)
m[0:4]=struct.pack('<I',LO)
time.sleep(0.25)
ext=struct.unpack_from('<I',m,0x70)[0]
dr=struct.unpack_from('<I',m,0)[0]
print('held_LO ext=%08x dr=%08x bit10=%d'%(ext,dr,(ext>>10)&1))
m.close(); os.close(fd)
PY
echo 1 > /sys/class/mmc_host/mmc2/force_rescan
sleep 3
echo === sdio ===
ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio
cat /sys/bus/sdio/devices/mmc2:0001:1/uevent 2>/dev/null || true
echo === gpio ===
sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio
echo === cameras ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
echo === dmesg ===
dmesg | tail -8
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=30)
    sys.stdout.write((r.stdout or "") + (r.stderr or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
