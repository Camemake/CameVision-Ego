#!/usr/bin/env python3
"""Pulse Ego CHIP_EN and rebind mmc2 only. Cameras/USB untouched."""
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
GPIO3 = 0x21E00000
# Rockchip GPIO v2 write-mask, pin 10 = GPIO3_B2
CHIP_EN_HI = 0x04000400
CHIP_EN_LO = 0x04000000


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def sh(s: str, cmd: str, timeout: int = 45) -> str:
    r = subprocess.run(
        [ADB, "-s", s, "shell", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (r.stdout or "") + (r.stderr or "")
    sys.stdout.write(out if out.endswith("\n") else out + "\n")
    return out


def main() -> int:
    s = serial()
    sh(
        s,
        r"""
echo === cameras ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
echo === live mmc2 dt ===
for f in /proc/device-tree/mmc@21f60000/*; do
  [ -f "$f" ] || continue
  b=$(basename "$f")
  echo -n "$b: "
  hexdump -v -e '/4 "%08x "' "$f"; echo
done
echo === wireless-wlan ===
ls /proc/device-tree/wireless-wlan
for f in /proc/device-tree/wireless-wlan/*; do
  [ -f "$f" ] || continue
  echo -n "$(basename $f): "
  hexdump -v -e '/4 "%08x "' "$f"; echo
  cat "$f" 2>/dev/null | tr '\0' ' '; echo
done
echo === mmc2 ios ===
cat /sys/kernel/debug/mmc2/ios 2>/dev/null || echo no_ios
echo === wifi_power now ===
cat /sys/class/rkwifi/wifi_power; echo
echo === gpio3 extport ===
devmem 0x21e00000 32
devmem 0x21e00008 32
devmem 0x21e00070 32
""",
    )

    hold = (
        "import mmap,os,struct,time,sys\n"
        f"fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)\n"
        f"m=mmap.mmap(fd,0x80,mmap.MAP_SHARED,mmap.PROT_WRITE|mmap.PROT_READ,offset={GPIO3})\n"
        "def wr(off,v):\n"
        " m[off:off+4]=struct.pack('<I',v)\n"
        "def rd(off):\n"
        " return struct.unpack_from('<I',m,off)[0]\n"
        f"wr(0,{CHIP_EN_LO})\n"
        "time.sleep(0.08)\n"
        f"wr(0,{CHIP_EN_HI})\n"
        "print('pulsed CHIP_EN lo->hi ext=%08x dr=%08x'%(rd(0x70),rd(0)))\n"
        "t=time.time()+8\n"
        f"w=struct.pack('<I',{CHIP_EN_HI})\n"
        "while time.time()<t:\n"
        " m[0:4]=w\n"
        " time.sleep(0.001)\n"
        "m.close(); os.close(fd)\n"
    )
    sh(
        s,
        "printf '%s' '" + hold.replace("'", "'\\''") + "' > /tmp/wifi_pulse.py\n"
        "echo 1 > /sys/class/gpio/gpio110/value 2>/dev/null || true\n"
        "echo 1 > /sys/class/rkwifi/wifi_power 2>/dev/null || true\n"
        "python3 /tmp/wifi_pulse.py &\n"
        "hold=$!\n"
        "sleep 0.2\n"
        "echo === unbind mmc2 ===\n"
        "echo 21f60000.mmc > /sys/bus/platform/drivers/dwmmc_rockchip/unbind\n"
        "sleep 0.3\n"
        "echo === bind mmc2 ===\n"
        "echo 21f60000.mmc > /sys/bus/platform/drivers/dwmmc_rockchip/bind\n"
        "sleep 4\n"
        "kill $hold 2>/dev/null || true\n"
        "wait $hold 2>/dev/null || true\n"
        "echo === sdio ===\n"
        "ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio\n"
        "cat /sys/bus/sdio/devices/mmc2:0001:1/uevent 2>/dev/null || true\n"
        "echo === dmesg ===\n"
        "dmesg | grep -iE '21f60000|mmc2|sdio' | tail -20\n"
        "echo === gpio3 ===\n"
        "sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio\n"
        "echo === cameras ===\n"
        "ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l\n"
        "echo === extport ===\n"
        "devmem 0x21e00000 32\n"
        "devmem 0x21e00070 32\n",
        timeout=50,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
