#!/usr/bin/env python3
"""LED follow-up: S99, init.d, apply current sysfs, no binary greps."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cv_telnet import run

CMD = r"""
echo '=== INIT.D ==='
ls -1 /etc/init.d
echo '=== S99 FILE ==='
ls -l /etc/init.d/S99camevision /userdata/camevision-led.sh 2>/dev/null
echo '----- S99camevision -----'
cat /etc/init.d/S99camevision 2>/dev/null
echo '----- end S99 -----'
echo '=== LED FILES IN INIT ==='
grep -n 'status:red\|status:green\|heartbeat\|class/leds' /etc/init.d/* 2>/dev/null
echo '=== UBOOT ENV LED ==='
fw_printenv 2>/dev/null | grep -i led
echo '=== GPIO LED PINS ==='
for n in 4 5 6; do
  echo -n "gpio0_A$n "; cat /sys/kernel/debug/gpio 2>/dev/null | grep -E "gpio-$n |GPIO0_A$n" | head -3
done
echo '=== DEBUG GPIO LEDS ==='
cat /sys/kernel/debug/gpio 2>/dev/null | grep -iE 'led|gpio-4|gpio-5|gpio-6|PA4|PA5|PA6' | head -20
echo '=== CURRENT TRIGGERS ==='
for n in red green blue; do
  echo -n "status:$n trigger="; cat /sys/class/leds/status:$n/trigger | tr ' ' '\n' | grep '\['; echo
  echo -n "status:$n brightness="; cat /sys/class/leds/status:$n/brightness; echo
done
echo '=== WIFI USB ==='
ip -4 addr show wlan0 2>/dev/null | grep inet
lsusb 2>/dev/null | head
cat /sys/class/udc/*/function 2>/dev/null
ls /sys/class/udc 2>/dev/null
echo OK
"""

if __name__ == "__main__":
    text = run(CMD, wait=8)
    out = Path(__file__).with_name("cv_led_s99.out.txt")
    out.write_text(text, encoding="utf-8", errors="replace")
    print(f"wrote {out} ({len(text)} chars)")
