#!/usr/bin/env python3
"""Read-only Wi-Fi/BLE probe. Does not touch cameras or USB."""
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = r"""
echo === cameras still up ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
echo === sdio / mmc2 ===
ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio
ls /sys/class/mmc_host/mmc2/
echo -n mmc2_status=; cat /proc/device-tree/mmc@21f60000/status; echo
echo reset_dt=$(hexdump -v -e '/4 "%08x "' /proc/device-tree/sdio-pwrseq/reset-gpios); echo
echo === gpio3 wifi lines ===
mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
sed -n '/gpiochip3:/,/gpiochip4:/p' /sys/kernel/debug/gpio
echo === uart2 ===
echo -n uart2=; cat /proc/device-tree/serial@21170000/status 2>/dev/null; echo
ls /dev/ttyS2 /dev/ttyAS2 2>/dev/null
echo === files ===
ls /userdata/camevision-wifi.sh /userdata/wpa_camevision.conf 2>/dev/null
ls /userdata/swt6621-rt52 2>/dev/null | head
ls /userdata/swt6621_fw 2>/dev/null | head
ls /oem/usr/ko | grep -iE 'skw|swt|cfg80211|mac80211' | head
echo === rfkill ===
ls /sys/class/rfkill 2>/dev/null
echo === pinctrl wifi ===
grep -E 'gpio3-10|gpio3-14|gpio3-15|sdmmc1' /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins 2>/dev/null
echo === dmesg mmc2 ===
dmesg | grep -iE '21f60000|mmc2|sdio|WLAN_RFKILL' | tail -20
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print(r.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
