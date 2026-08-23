# Recovery 3 overlay. Does not restart USB / S50.
# After this, reboot once so UVC S50 is the gadget. Debug on Wi-Fi :2323.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ov = Join-Path $here 'overlay'

$adbCandidates = @(
  'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe',
  'C:\Users\stefa\Downloads\RKDevTool_Release_v2.84\RKDevTool_Release_v2.84\bin\adb.exe'
)
$adb = $adbCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $adb) { throw 'adb.exe not found' }

function PushUnix([string]$src, [string]$dst) {
  $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($src) + '.unix')
  $bytes = [IO.File]::ReadAllBytes($src)
  if ($src -notmatch '\.(ko|bin|img|json)$') {
    $text = [Text.Encoding]::UTF8.GetString($bytes) -replace "`r`n", "`n" -replace "`r", "`n"
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($tmp, $text, $utf8)
    $src = $tmp
  }
  & $adb push $src $dst
  if ($LASTEXITCODE -ne 0) { throw "push failed: $dst" }
}

& $adb wait-for-device
& $adb shell 'mount -o remount,rw /; mount -o remount,rw /oem; mount -o remount,rw /userdata'

PushUnix (Join-Path $ov 'S20linkmount') /etc/init.d/S20linkmount
PushUnix (Join-Path $ov 'S21appinit') /etc/init.d/S21appinit
PushUnix (Join-Path $ov 'S40network') /etc/init.d/S40network
PushUnix (Join-Path $ov 'S50usbdevice') /etc/init.d/S50usbdevice
PushUnix (Join-Path $ov 'S50usbdevice.adb') /userdata/S50usbdevice.adb
PushUnix (Join-Path $ov 'S99camevision') /etc/init.d/S99camevision
PushUnix (Join-Path $ov 'camevision.sh') /etc/profile.d/camevision.sh

PushUnix (Join-Path $ov 'camevision-wifi.sh') /userdata/camevision-wifi.sh
PushUnix (Join-Path $ov 'camevision-imu.sh') /userdata/camevision-imu.sh
PushUnix (Join-Path $ov 'camevision-led.sh') /userdata/camevision-led.sh
PushUnix (Join-Path $ov 'camevision-aiq.sh') /userdata/camevision-aiq.sh
PushUnix (Join-Path $ov 'camevision-uvc-cam.sh') /userdata/camevision-uvc-cam.sh
PushUnix (Join-Path $ov 'camevision-uvc-mjpg.py') /userdata/camevision-uvc-mjpg.py
PushUnix (Join-Path $ov 'camevision-uvc-live.sh') /userdata/camevision-uvc-live.sh
PushUnix (Join-Path $ov 'camevision-stream.sh') /userdata/camevision-stream.sh
PushUnix (Join-Path $ov 'swt6621.sh') /userdata/swt6621.sh
PushUnix (Join-Path $ov 'imu-live.sh') /userdata/imu-live.sh
PushUnix (Join-Path $ov 'wifi-ble-test.sh') /userdata/wifi-ble-test.sh
PushUnix (Join-Path $ov 'wpa_camevision.conf') /userdata/wpa_camevision.conf
PushUnix (Join-Path $ov 'insmod_wifi.sh') /oem/usr/ko/insmod_wifi.sh
PushUnix (Join-Path $ov 'hw_rtsp.py') /userdata/hw_rtsp.py

& $adb shell 'mkdir -p /userdata/iqfiles /userdata/swt6621_fw /userdata/swt6621-rt52'
$iq = Join-Path $ov 'iqfiles\sc233hgs_efference-sc233hgs_default.json'
if (Test-Path $iq) {
  PushUnix $iq /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json
}

& $adb push (Join-Path $ov 'kmpp-rt52.ko') /userdata/kmpp-rt52.ko
if ($LASTEXITCODE -ne 0) { throw 'push kmpp-rt52.ko failed' }

Get-ChildItem -LiteralPath (Join-Path $ov 'swt6621_fw') -File | ForEach-Object {
  & $adb push $_.FullName "/userdata/swt6621_fw/$($_.Name)"
  if ($LASTEXITCODE -ne 0) { throw "push fw $($_.Name) failed" }
}
Get-ChildItem -LiteralPath (Join-Path $ov 'swt6621-rt52') -Filter '*.ko' | ForEach-Object {
  & $adb push $_.FullName "/userdata/swt6621-rt52/$($_.Name)"
  if ($LASTEXITCODE -ne 0) { throw "push ko $($_.Name) failed" }
}

& $adb shell 'chmod 755 /etc/init.d/S20linkmount /etc/init.d/S21appinit /etc/init.d/S40network /etc/init.d/S50usbdevice /etc/init.d/S99camevision /etc/profile.d/camevision.sh /userdata/camevision-wifi.sh /userdata/camevision-imu.sh /userdata/camevision-led.sh /userdata/camevision-aiq.sh /userdata/camevision-uvc-cam.sh /userdata/camevision-uvc-mjpg.py /userdata/camevision-uvc-live.sh /userdata/camevision-stream.sh /userdata/swt6621.sh /userdata/imu-live.sh /userdata/wifi-ble-test.sh /oem/usr/ko/insmod_wifi.sh /userdata/hw_rtsp.py /userdata/S50usbdevice.adb; touch /userdata/uvc-webcam.on; rm -f /etc/init.d/S50usbdevice.uvc-rk /etc/init.d/S50usbdevice.bak-uvc /etc/init.d/S50usbdevice.adb-stock; sync'
Write-Host 'RECOVERY3_OVERLAY_DONE — USB was not restarted.'
Write-Host 'Reboot once: UVC CameVision Single on USB, telnet 192.168.1.23:2323'
Write-Host 'If Windows still shows ADB: unplug USB-C 2s, plug back in.'
