#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === OUT FMTS ===
v4l2-ctl -d /dev/video28 --list-formats-out
v4l2-ctl -d /dev/video28 --list-formats
echo === MPI ENC ===
ls /oem/usr/bin/mpi_enc_test /usr/bin/mpi_enc_test 2>/dev/null
/oem/usr/bin/mpi_enc_test -h 2>&1 | head -40
echo === KO ===
ls /oem/usr/ko | head -40
echo === LOG FULL LAST ===
tail -5 /userdata/rk_mpi_uvc.log
echo === WIN gadget ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo PROD=$(cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product)
echo DNAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
""", wait=8))
