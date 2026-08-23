#!/bin/sh
# Build Seekwave SWT6621S H26.27.6.1 against the CameVision 6.1.141-rt52
# PREEMPT_RT kernel. Run this on Linux with an aarch64 toolchain.
#
# Required:
#   KSRC  = that kernel tree after `make ARCH=arm64 modules_prepare`
#           CONFIG_PREEMPT_RT=y, CONFIG_LOCALVERSION="-rt52"
#           vermagic must be: 6.1.141-rt52 SMP preempt_rt mod_unload aarch64
#   CROSS = aarch64-linux-gnu-
#
# Do not pass CONFIG_SKW_USB=m — USB gadget on this board must stay ADB.
# NPI / /dev/ATC only needs skw_sdio_lite. STA also needs cfg80211 + swt6621s_wifi
# from the same kernel tree.

set -e
SKW=${SKW:-/mnt/c/Users/stefa/Desktop/Project Efference/M1/SWT6621S_H26.27.6.1_F26.26.3.1/SWT6621S_H26.27.6.1_F26.26.3.1/seekwave}
KSRC=${KSRC:?set KSRC to the 6.1.141-rt52 kernel tree}
CROSS=${CROSS:-aarch64-linux-gnu-}
OUT=${OUT:-/mnt/c/Users/stefa/Desktop/CameVision Single/build/live/swt6621-rt52}

test -f "$KSRC/Makefile" || { echo "no kernel Makefile in $KSRC"; exit 1; }
grep -q 'PREEMPT_RT=y' "$KSRC/.config" || echo "WARN: $KSRC/.config should have CONFIG_PREEMPT_RT=y"

make -C "$KSRC" ARCH=arm64 CROSS_COMPILE="$CROSS" M="$SKW/swt6621s" modules \
	CONFIG_SEEKWAVE_BSP_DRIVERS=m \
	CONFIG_SKW_SDIOHAL=m \
	CONFIG_SKW_BSP_UCOM=m \
	CONFIG_SKW_BSP_BOOT=m \
	CONFIG_WLAN_VENDOR_SWT6621S=m \
	CONFIG_SKW_BT=m

mkdir -p "$OUT"
cp -f "$SKW"/swt6621s/drivers/seekwaveplatform_lite/skw_sdio_lite.ko "$OUT/"
cp -f "$SKW"/swt6621s/drivers/swt6621s_wifi/swt6621s_wifi.ko "$OUT/" 2>/dev/null || true
cp -f "$SKW"/swt6621s/drivers/swtbt4l/skwbt.ko "$OUT/" 2>/dev/null || true
# STA also needs these from KSRC (not from Seekwave):
for m in cfg80211 mac80211 libarc4 ctr ccm aes_generic; do
	find "$KSRC" -name "$m.ko" -print -exec cp -f {} "$OUT/" \; 2>/dev/null || true
done
echo "built into $OUT"
find "$OUT" -name '*.ko' -exec sh -c 'echo; modinfo "$1" | grep -E "filename|vermagic|depends"' _ {} \;
