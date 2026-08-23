#!/usr/bin/env python3
"""Probe Ego microSD host, DT, GPIOs, and block devices over ADB."""
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
echo === mmc nodes ===
ls -l /proc/device-tree/mmc@* 2>/dev/null
for n in /proc/device-tree/mmc@*; do
  echo ---- $n
  echo -n status=; cat $n/status; echo
  echo -n name=; cat $n/name; echo
  [ -f $n/bus-width ] && echo bus-width=$(hexdump -v -e '/4 "%d "' $n/bus-width)
  [ -f $n/cd-gpios ] && echo cd-gpios=$(hexdump -v -e '/4 "%08x "' $n/cd-gpios)
  [ -f $n/vmmc-supply ] && echo vmmc=$(hexdump -v -e '/4 "%08x "' $n/vmmc-supply)
  [ -f $n/non-removable ] && echo non-removable=yes
  [ -f $n/cap-sd-highspeed ] && echo cap-sd-highspeed=yes
done
echo === vcc1v8-sd ===
if [ -d /proc/device-tree/vcc1v8-sd ]; then
  echo -n name=; cat /proc/device-tree/vcc1v8-sd/regulator-name; echo
  echo gpio=$(hexdump -v -e '/4 "%08x "' /proc/device-tree/vcc1v8-sd/gpio)
  ls /sys/class/regulator | while read r; do
    n=$(cat /sys/class/regulator/$r/name 2>/dev/null)
    [ "$n" = vcc1v8_sd ] && echo sys $r $n state=$(cat /sys/class/regulator/$r/state) uV=$(cat /sys/class/regulator/$r/microvolts 2>/dev/null)
  done
else
  echo MISSING
fi
echo === block ===
ls -l /dev/mmcblk* 2>/dev/null
ls /sys/block | grep mmc
echo === mmc host ===
for h in /sys/class/mmc_host/mmc*; do
  echo $h
  cat $h/mmc*/uevent 2>/dev/null
  cat $h/*/cid 2>/dev/null
done
echo === dmesg mmc ===
dmesg | grep -iE 'mmc|sdhci|dwmmc|sdmmc' | tail -40
echo === gpio 3-11 CD / 3-12 PWREN ===
# gpiochip for gpio3
for c in /sys/class/gpio/gpiochip*; do
  echo chip $c base=$(cat $c/base) ngpio=$(cat $c/ngpio) label=$(cat $c/label)
done
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
