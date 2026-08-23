#!/usr/bin/env python3
"""Probe Ego Wi-Fi DT, SDIO, drivers, and STA state."""
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def main() -> int:
    s = serial()
    print("serial", s)
    cmd = r"""
echo === model ===
cat /proc/device-tree/model; echo
echo === mmc2 / sdmmc1 ===
echo -n status=; cat /proc/device-tree/mmc@21f60000/status; echo
ls /sys/class/mmc_host/mmc2/ 2>/dev/null
cat /sys/class/mmc_host/mmc2/mmc2\:0001/uevent 2>/dev/null
echo === sdio ===
ls /sys/bus/sdio/devices 2>/dev/null
for d in /sys/bus/sdio/devices/*; do
  [ -e "$d" ] || continue
  echo $d
  cat $d/uevent 2>/dev/null
done
echo === wifi gpio / regulator ===
cat /sys/class/regulator/regulator.*/name 2>/dev/null | while read; do true; done
for r in /sys/class/regulator/regulator.*; do
  n=$(cat $r/name 2>/dev/null)
  case "$n" in *wifi*|*vcc3v3_wifi*) echo $r $n state=$(cat $r/state) ;; esac
done
echo === wireless-wlan ===
ls /proc/device-tree/wireless-wlan 2>/dev/null
echo -n chip=; cat /proc/device-tree/wireless-wlan/wifi_chip_type 2>/dev/null; echo
echo === files ===
ls -l /userdata/camevision-wifi.sh /userdata/wpa_camevision.conf /userdata/insmod_wifi.sh 2>/dev/null
ls /userdata/swt6621-rt52 2>/dev/null | head
ls /userdata/swt6621_fw 2>/dev/null | head
ls /oem/usr/ko 2>/dev/null | grep -iE 'skw|swt|cfg80211|mac80211' | head
echo === lsmod wifi ===
lsmod | grep -iE 'skw|swt|cfg80211|mac80211|arc4|aes'
echo === net ===
ls /sys/class/net
ip -4 addr show wlan0 2>/dev/null
wpa_cli -i wlan0 status 2>/dev/null | head -20
echo === dmesg wifi ===
dmesg | grep -iE 'mmc2|21f60000|sdio|vs6621|swt6621|skw|wlan|wifi' | tail -40
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print(r.stdout)
    if r.stderr:
        print("STDERR", r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
