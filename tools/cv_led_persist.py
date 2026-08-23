#!/usr/bin/env python3
"""Apply LED policy now and persist via userdata helper + S99camevision."""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

OVERLAY = Path(
    r"C:\Users\stefa\Desktop\CameVision Single"
    r"\restore\recovery-2-20260821-adb-stream\overlay"
)
LED = OVERLAY / "camevision-led.sh"
S99 = OVERLAY / "S99camevision"

led_b64 = base64.b64encode(LED.read_bytes()).decode("ascii")
s99_b64 = base64.b64encode(S99.read_bytes()).decode("ascii")

CMD = f"""
echo '=== APPLY NOW ==='
echo none > /sys/class/leds/status:red/trigger
echo 0 > /sys/class/leds/status:red/brightness
echo none > /sys/class/leds/status:green/trigger
echo 1 > /sys/class/leds/status:green/brightness
echo none > /sys/class/leds/status:blue/trigger
echo 0 > /sys/class/leds/status:blue/brightness
echo '=== PERSIST ==='
echo {led_b64} | base64 -d > /userdata/camevision-led.sh
chmod 755 /userdata/camevision-led.sh
mount -o remount,rw / 2>/dev/null
echo {s99_b64} | base64 -d > /etc/init.d/S99camevision
chmod 755 /etc/init.d/S99camevision
/userdata/camevision-led.sh
echo '=== VERIFY LED ==='
for n in red green blue; do
  echo -n "status:$n trigger="
  cat /sys/class/leds/status:$n/trigger | tr ' ' '\\n' | grep '\\['
  echo -n "status:$n brightness="
  cat /sys/class/leds/status:$n/brightness
done
echo '=== VERIFY FILES ==='
ls -l /userdata/camevision-led.sh /etc/init.d/S99camevision
echo '----- S99 head -----'
sed -n '1,20p' /etc/init.d/S99camevision
echo '=== LINK ==='
ip -4 addr show wlan0 | grep inet
echo -n 'udc='; cat /sys/class/udc/21500000.usb/state 2>/dev/null
echo -n 'speed='; cat /sys/class/udc/21500000.usb/current_speed 2>/dev/null
echo -n 'function='; cat /sys/class/udc/21500000.usb/function 2>/dev/null
echo DONE
"""

if __name__ == "__main__":
    text = run(CMD, wait=10)
    out = Path(__file__).with_name("cv_led_persist.out.txt")
    out.write_text(text, encoding="utf-8", errors="replace")
    print(f"wrote {out} ({len(text)} chars)")
