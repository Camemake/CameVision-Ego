#!/usr/bin/env python3
"""Live-enable Ego VS6621 without flashing, reboot, or touching cameras/USB.

CHIP_EN / WIFI_POW_EN is GPIO3_B2 (gpio 106). The live FIT treats it as
ACTIVE_HIGH reset, so pwrseq deassert drives it LOW and the module is off
during the boot SDIO probe. After the failed probe the line is left HIGH
(asserted). This script:
  1. raises HOST_WAKE_WL (GPIO3_B6 / gpio 110)
  2. force_rescans mmc2 only
  3. if still no SDIO, holds CHIP_EN high via /dev/mem during a second rescan
Does not unbind ISP/CIF, does not touch the USB gadget, does not flash.
"""
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"

# GPIO3 @ 0x21e00000, pin 10 = GPIO3_B2. Rockchip GPIO v2 write-mask:
# low 16 = data, high 16 = write enable. Pin 10 high => 0x04000400
GPIO3 = 0x21E00000
CHIP_EN_SET = 0x04000400


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 40) -> str:
    r = subprocess.run(
        [ADB, "-s", s, "shell", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (r.stdout or "") + (r.stderr or "")
    sys.stdout.write(out)
    if not out.endswith("\n"):
        sys.stdout.write("\n")
    return out


def main() -> int:
    s = serial()
    print(f"adb={s}")

    sh(
        s,
        r"""
echo === cameras before ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
echo === helpers ===
which python3 devmem 2>/dev/null
ls /sys/class/rkwifi 2>/dev/null
ls /oem/usr/ko | grep -iE 'skw|swt|cfg80211|mac80211|arc4|aes|ccm|ctr|gf128'
echo === firmware on board ===
ls /userdata/swt6621_fw /lib/firmware /oem/usr/share 2>/dev/null | head -40
find /oem /userdata /lib/firmware -name '*SWT6621*' -o -name '*SEEKWAVE*' 2>/dev/null | head
echo === rkwifi ===
for f in /sys/class/rkwifi/*; do
  [ -f "$f" ] || continue
  echo -n "$(basename $f)="; cat "$f"; echo
done
""",
    )

    sh(
        s,
        r"""
mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
# HOST_WAKE_WL GPIO3_B6 = gpio 110. Unclaimed. High = host wakes WLAN.
if [ ! -d /sys/class/gpio/gpio110 ]; then
  echo 110 > /sys/class/gpio/export 2>/dev/null || true
fi
if [ -d /sys/class/gpio/gpio110 ]; then
  echo out > /sys/class/gpio/gpio110/direction
  echo 1 > /sys/class/gpio/gpio110/value
  echo host_wake=$(cat /sys/class/gpio/gpio110/value)
else
  echo host_wake=export_failed
fi
# CHIP_EN is claimed by pwrseq as gpio-106. Do not export it.
echo === gpio3 after host_wake ===
sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio
echo === rkwifi power on ===
echo 1 > /sys/class/rkwifi/wifi_power 2>/dev/null || true
echo 1 > /sys/class/rkwifi/wifi_bt_vbat 2>/dev/null || true
echo 1 > /sys/class/rkwifi/wifi_set_carddetect 2>/dev/null || true
echo === force_rescan mmc2 ===
echo 1 > /sys/class/mmc_host/mmc2/force_rescan
sleep 2
echo === sdio after rescan ===
ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio
cat /sys/bus/sdio/devices/mmc2:0001:1/uevent 2>/dev/null || true
echo === gpio3 after rescan ===
sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio
echo === cameras after rescan ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
""",
    )

    # Second pass only if no SDIO: hold CHIP_EN high across another rescan.
    check = subprocess.run(
        [ADB, "-s", s, "shell", "ls /sys/bus/sdio/devices 2>/dev/null"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if "mmc2:" in (check.stdout or ""):
        print("SDIO present after first rescan")
        return 0

    print("=== hold CHIP_EN high + rescan ===")
    # One on-device python loop. GPIO3 is page-aligned; write-mask pin 10 high.
    hold_py = (
        "import mmap,os,struct,time\n"
        f"fd=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)\n"
        f"m=mmap.mmap(fd,0x10,mmap.MAP_SHARED,mmap.PROT_WRITE|mmap.PROT_READ,offset={GPIO3})\n"
        f"w=struct.pack('<I',{CHIP_EN_SET})\n"
        "t=time.time()+4\n"
        "while time.time()<t:\n"
        " m[0:4]=w\n"
        " time.sleep(0.001)\n"
        "m.close(); os.close(fd)\n"
    )
    sh(
        s,
        "if [ ! -e /dev/mem ]; then echo no_/dev/mem; exit 0; fi\n"
        "printf '%s' '" + hold_py.replace("'", "'\\''") + "' > /tmp/hold_chipen.py\n"
        "python3 /tmp/hold_chipen.py &\n"
        "hold=$!\n"
        "sleep 0.05\n"
        "echo 1 > /sys/class/mmc_host/mmc2/force_rescan\n"
        "sleep 3\n"
        "kill $hold 2>/dev/null || true\n"
        "wait $hold 2>/dev/null || true\n"
        "echo === sdio after hold ===\n"
        "ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio\n"
        "cat /sys/bus/sdio/devices/mmc2:0001:1/uevent 2>/dev/null || true\n"
        "dmesg | grep -iE '21f60000|mmc2|sdio' | tail -15\n"
        "echo === gpio3 after hold ===\n"
        "sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio\n"
        "echo === cameras after hold ===\n"
        "ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l\n",
        timeout=50,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
