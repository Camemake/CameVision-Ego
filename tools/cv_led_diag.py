#!/usr/bin/env python3
"""Dump LED sysfs, DT, dmesg, and init LED usage on CameVision via telnet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cv_telnet import run

CMD = r"""
echo '=== PING/UPTIME ==='
uptime; cat /proc/version 2>/dev/null | head -1
echo '=== SYSFS LEDS ==='
ls -la /sys/class/leds 2>/dev/null
for d in /sys/class/leds/*; do
  [ -d "$d" ] || continue
  echo "-- $d --"
  echo -n 'trigger='; cat "$d/trigger" 2>/dev/null
  echo -n 'brightness='; cat "$d/brightness" 2>/dev/null
  echo -n 'max='; cat "$d/max_brightness" 2>/dev/null
  for f in delay_on delay_off invert panic; do
    if [ -f "$d/$f" ]; then echo -n "$f="; cat "$d/$f"; fi
  done
  echo -n 'uevent='; cat "$d/uevent" 2>/dev/null | tr '\n' ' '; echo
done
echo '=== LED DEVICE OF NODE ==='
for d in /sys/class/leds/*; do
  [ -d "$d" ] || continue
  echo "-- $d --"
  ls -la "$d/device" 2>/dev/null | head -5
  cat "$d/device/of_node/name" 2>/dev/null
  cat "$d/device/of_node/compatible" 2>/dev/null | tr '\0' ' '; echo
  if [ -d "$d/device/of_node" ]; then
    for n in "$d/device/of_node"/*; do
      bn=$(basename "$n")
      echo "  child $bn"
      if [ -f "$n/label" ]; then echo -n '    label='; cat "$n/label"; echo; fi
      if [ -f "$n/linux,default-trigger" ]; then echo -n '    default-trigger='; cat "$n/linux,default-trigger"; echo; fi
      if [ -f "$n/default-state" ]; then echo -n '    default-state='; cat "$n/default-state"; echo; fi
      if [ -f "$n/gpios" ]; then echo -n '    gpios='; xxd -p "$n/gpios" 2>/dev/null || od -An -tx1 "$n/gpios"; fi
      if [ -f "$n/color" ]; then echo -n '    color='; xxd -p "$n/color" 2>/dev/null || od -An -tx1 "$n/color"; fi
    done
  fi
done
echo '=== PROC DEVICE TREE LEDS ==='
ls /proc/device-tree/leds 2>/dev/null || ls /proc/device-tree/gpio-leds 2>/dev/null
find /proc/device-tree -name '*led*' 2>/dev/null | head -40
echo '=== DT LED NODES ==='
for n in /proc/device-tree/leds/* /proc/device-tree/gpio-leds/*; do
  [ -e "$n" ] || continue
  echo "-- $n --"
  ls "$n" 2>/dev/null
  for p in label linux,default-trigger default-state function color gpios status; do
    if [ -f "$n/$p" ]; then
      echo -n "  $p="; cat "$n/$p" 2>/dev/null | tr '\0' ' '; echo
    fi
  done
done
echo '=== DMESG LED/GPIO/PANIC/HEARTBEAT ==='
dmesg | grep -iE 'led|heartbeat|panic|gpio-leds|status:red|status:green|charger|mmc0' | tail -60
echo '=== INIT LED SCRIPTS ==='
grep -RIn 'leds\|heartbeat\|brightness\|status:red\|status:green' /etc/init.d /userdata /oem/usr/ko /oem/usr/bin 2>/dev/null | head -80
echo '=== S99 ==='
ls -l /etc/init.d/S99* 2>/dev/null
head -80 /etc/init.d/S99camevision 2>/dev/null
echo '=== USERDATA HELPERS ==='
ls -l /userdata/camevision*.sh /userdata/*led* 2>/dev/null
echo '=== PROC CMDLINE ==='
cat /proc/cmdline
echo '=== DONE ==='
"""

if __name__ == "__main__":
    text = run(CMD, wait=12)
    out = Path(__file__).with_name("cv_led_diag.out.txt")
    out.write_text(text, encoding="utf-8", errors="replace")
    print(f"wrote {out} ({len(text)} chars)")
