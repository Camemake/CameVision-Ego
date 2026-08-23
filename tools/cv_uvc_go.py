#!/usr/bin/env python3
"""Live H.264 UVC recover: names, H264 header, PHY bounce, rk_mpi. Reboot if still detached."""
import base64
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import HOST, PORT, run

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Single")
S50 = ROOT / "build" / "live" / "S50usbdevice.uvc-rk"
S99 = ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay" / "S99camevision"
PUMP = ROOT / "build" / "live" / "camevision-uvc-h264.py"


def push(path: Path, dest: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return run(
        f"mount -o remount,rw / 2>/dev/null; echo {b64} | base64 -d > {dest}; chmod 755 {dest}; wc -c {dest}",
        wait=10,
    )


def ping_ok() -> bool:
    r = subprocess.run(
        ["ping", "-n", "1", "-w", "1000", HOST],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def telnet_ok() -> bool:
    try:
        s = socket.create_connection((HOST, PORT), 3)
        s.close()
        return True
    except OSError:
        return False


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Status, $_.Class, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


LIVE = r"""
killall rk_mpi_uvc v4l2-ctl ffmpeg hw_rtsp.py mpi_enc_test 2>/dev/null
kill -9 $(cat /userdata/isp-grab.pid /userdata/hw-rtsp.pid 2>/dev/null) 2>/dev/null
touch /userdata/uvc-webcam.on

G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1

echo none > $G/UDC
sleep 1
rm -f $C/f1 $C/f2 $C/f3 $C/f4 $C/ffs.adb

echo 0x2207 > $G/idVendor
echo 0x0016 > $G/idProduct
echo 239 > $G/bDeviceClass
echo 2 > $G/bDeviceSubClass
echo 1 > $G/bDeviceProtocol
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo 500 > $C/MaxPower

echo "CameVision Single RGB" > $U/device_name
echo "UVC RGB" > $U/function_name
echo 3072 > $U/streaming_maxpacket
echo 2 > $U/uvc_num_request
echo 0 > $U/streaming_bulk

mkdir -p $U/streaming/framebased/f1/1920_1200p
echo 1920 > $U/streaming/framebased/f1/1920_1200p/wWidth
echo 1200 > $U/streaming/framebased/f1/1920_1200p/wHeight
echo 333333 > $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMinBitRate
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMaxBitRate
printf '333333\n' > $U/streaming/framebased/f1/1920_1200p/dwFrameInterval
printf 'H264\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71' > $U/streaming/framebased/f1/guidFormat

rm -f $U/streaming/class/fs/h $U/streaming/class/hs/h $U/streaming/class/ss/h
rm -f $U/streaming/header/h/f1 $U/streaming/header/h/f $U/streaming/header/h/m
ln -s $U/streaming/framebased/f1 $U/streaming/header/h/f1
ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m
ln -s $U/streaming/header/h $U/streaming/class/fs/h
ln -s $U/streaming/header/h $U/streaming/class/hs/h
ln -s $U/streaming/header/h $U/streaming/class/ss/h

echo host > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
echo peripheral > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
echo PHY=$(cat /sys/devices/platform/21400000.usb2-phy/otg_mode)

ln -s $U $C/f1
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)

cp -f /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini
sed -i 's/enable_aiq = 1/enable_aiq = 0/' /tmp/rkuvc.ini
grep -q enable_venc_0 /tmp/rkuvc.ini || sed -i 's/enable_2uvc = 0/enable_2uvc = 0\nenable_venc_0 = 1/' /tmp/rkuvc.ini
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export rt_log_level=3
touch /tmp/uvc_no_timeout
start-stop-daemon -S -b -q -m -p /tmp/rk_mpi_uvc.pid -x /oem/usr/bin/rk_mpi_uvc -- -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2
start-stop-daemon -S -b -q -m -p /tmp/uvc-h264.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-h264.py
sleep 6
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo DNAME=$(cat $U/device_name)
echo PROD=$(cat $G/strings/0x409/product)
echo HEADER=$(ls $U/streaming/header/h)
echo V28=$(cat /sys/class/video4linux/video28/name)
ps | grep -E 'rk_mpi_uvc|camevision-uvc-h264' | grep -v grep
dmesg | grep -E 'device reset|uvc_function_set_alt' | tail -6
"""


def status() -> str:
    return run(
        r"""
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo UDC=$(cat /sys/kernel/config/usb_gadget/rockchip/UDC)
echo DNAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
echo HEADER=$(ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h)
echo V28=$(cat /sys/class/video4linux/video28/name 2>/dev/null)
ps | grep -E 'rk_mpi_uvc|camevision-uvc-h264' | grep -v grep
""",
        wait=6,
    )


def wait_board(seconds: int = 75) -> bool:
    t0 = time.time()
    while time.time() - t0 < seconds:
        if ping_ok() and telnet_ok():
            return True
        time.sleep(2)
    return False


def main() -> int:
    overlay = ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay"
    shutil.copy2(S50, overlay / "S50usbdevice.uvc-rk")
    shutil.copy2(PUMP, overlay / "camevision-uvc-h264.py")

    print("=== PUSH ===")
    print(push(S50, "/etc/init.d/S50usbdevice"))
    print(push(S99, "/etc/init.d/S99camevision"))
    print(push(PUMP, "/userdata/camevision-uvc-h264.py"))

    print("=== LIVE PHY BOUNCE ===")
    print(run(LIVE, wait=24))
    print("=== WIN after live ===")
    print(win_uvc() or "(no present VID_2207)")

    st = status()
    print(st)
    attached = "STATE=configured" in st or "STATE=addressed" in st
    if attached:
        print("ATTACHED")
        return 0

    print("=== still detached, software reboot ===")
    try:
        run("sync; reboot", wait=2)
    except Exception as e:
        print("reboot send", e)

    time.sleep(8)
    if not wait_board(90):
        print("board did not return on telnet")
        print(win_uvc() or "(no present VID_2207)")
        return 1

    time.sleep(10)
    print("=== after reboot ===")
    print(status())
    print("=== WIN after reboot ===")
    print(win_uvc() or "(no present VID_2207)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
