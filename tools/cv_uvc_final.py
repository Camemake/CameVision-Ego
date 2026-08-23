#!/usr/bin/env python3
"""dwc3 reconnect + CameVision Single + H264 1920x1200@30 + ISP pump."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
killall ffmpeg 2>/dev/null
killall v4l2-ctl 2>/dev/null
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1
rm -f $C/f1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "CameVision Single" > $U/function_name
echo 0x2207 > $G/idVendor
echo 0x0016 > $G/idProduct

# header already has f1+m from last fix
echo NAME=$(cat $U/device_name)
echo PROD=$(cat $G/strings/0x409/product)
echo HEADER=$(ls $U/streaming/header/h)
echo H264=$(cat $U/streaming/framebased/f1/1920_1200p/wWidth)x$(cat $U/streaming/framebased/f1/1920_1200p/wHeight) fi=$(cat $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval)

ln -s $U $C/f1
echo 21500000.usb > $G/UDC
sleep 2
echo UDC=$(cat $G/UDC) STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)

export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export PATH=/oem/usr/bin:/usr/bin:$PATH
cp -f /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini
sed -i 's/enable_aiq = 1/enable_aiq = 0/' /tmp/rkuvc.ini
grep -q enable_venc_0 /tmp/rkuvc.ini || sed -i 's/enable_2uvc = 0/enable_2uvc = 0\nenable_venc_0 = 1/' /tmp/rkuvc.ini
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid

# kmpp H264 pump: ISP NV12 1920x1200 -> gadget H264
# ffmpeg will block until the host STREAMON
: > /userdata/uvc-h264-pump.log
ffmpeg -hide_banner -loglevel info \
  -f v4l2 -input_format nv12 -video_size 1920x1200 -framerate 30 -i /dev/video13 \
  -c:v mjpeg -q:v 5 -pix_fmt yuvj420p -r 30 \
  -f v4l2 /dev/video28 >/userdata/uvc-h264-pump.log 2>&1 &
echo ffmpeg_mjpeg=$!
# also try H264 into the gadget if the encoder exists
ffmpeg -encoders 2>/dev/null | grep -iE 'h264|rkmpp|mjpeg' | head -10 >>/userdata/uvc-h264-pump.log

sleep 4
echo STATE2=$(cat /sys/class/udc/21500000.usb/state)
ps | grep -E 'rk_mpi_uvc|ffmpeg' | grep -v grep
dmesg | grep -E 'device reset|set_alt' | tail -8
tail -15 /userdata/uvc-h264-pump.log
tail -8 /userdata/rk_mpi_uvc.log | grep -E 'Please configure|add uvc|uvc open|rgb_cnt'
"""
print(run(CMD, wait=24))
