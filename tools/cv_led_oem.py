#!/usr/bin/env python3
"""Check OEM/init LED blinkers; do not grep binaries."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cv_telnet import run

CMD = r"""
echo '=== OEM KO SCRIPTS ==='
ls -l /oem/usr/ko/*.sh 2>/dev/null
echo '----- insmod_ko.sh head -----'
sed -n '1,80p' /oem/usr/ko/insmod_ko.sh 2>/dev/null
echo '----- insmod_wifi.sh head -----'
sed -n '1,80p' /oem/usr/ko/insmod_wifi.sh 2>/dev/null
echo '=== S21 ==='
sed -n '1,80p' /etc/init.d/S21appinit 2>/dev/null
echo '=== S99_auto_reboot ==='
sed -n '1,40p' /etc/init.d/S99_auto_reboot 2>/dev/null
echo '=== LED PIDS ==='
ps w | grep -i led | grep -v grep
echo '=== STATUS LED.SH ==='
ls -l /oem/usr/ko/status_led.sh /userdata/*led* 2>/dev/null
echo DONE
"""

if __name__ == "__main__":
    text = run(CMD, wait=8)
    out = Path(__file__).with_name("cv_led_oem.out.txt")
    out.write_text(text, encoding="utf-8", errors="replace")
    print(f"wrote {out} ({len(text)} chars)")
