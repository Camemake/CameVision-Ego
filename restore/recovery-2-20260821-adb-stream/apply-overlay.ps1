# Re-apply recovery 2 overlay. Does not restart USB / S50.
# Self-contained: Wi-Fi/BT RT52 modules, F26.26.3.1 firmware, IMU scripts, kmpp.
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
  if ($src -notmatch '\.(ko|bin|img)$') {
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

# Init + profile
PushUnix (Join-Path $ov 'S20linkmount') /etc/init.d/S20linkmount
PushUnix (Join-Path $ov 'S21appinit') /etc/init.d/S21appinit
PushUnix (Join-Path $ov 'S40network') /etc/init.d/S40network
PushUnix (Join-Path $ov 'S50usbdevice') /etc/init.d/S50usbdevice
PushUnix (Join-Path $ov 'S99camevision') /etc/init.d/S99camevision
PushUnix (Join-Path $ov 'camevision.sh') /etc/profile.d/camevision.sh

# Userspace scripts
PushUnix (Join-Path $ov 'camevision-stream.sh') /userdata/camevision-stream.sh
PushUnix (Join-Path $ov 'camevision-wifi.sh') /userdata/camevision-wifi.sh
PushUnix (Join-Path $ov 'camevision-imu.sh') /userdata/camevision-imu.sh
PushUnix (Join-Path $ov 'swt6621.sh') /userdata/swt6621.sh
PushUnix (Join-Path $ov 'imu-live.sh') /userdata/imu-live.sh
PushUnix (Join-Path $ov 'wifi-ble-test.sh') /userdata/wifi-ble-test.sh
PushUnix (Join-Path $ov 'wpa_camevision.conf') /userdata/wpa_camevision.conf
PushUnix (Join-Path $ov 'insmod_wifi.sh') /oem/usr/ko/insmod_wifi.sh
PushUnix (Join-Path $ov 'isp_grab.py') /userdata/isp_grab.py
PushUnix (Join-Path $ov 'hw_rtsp.py') /userdata/hw_rtsp.py

# Encoder
& $adb push (Join-Path $ov 'kmpp-rt52.ko') /userdata/kmpp-rt52.ko
if ($LASTEXITCODE -ne 0) { throw 'push kmpp-rt52.ko failed' }

# Seekwave firmware F26.26.3.1
$fwSrc = Join-Path $ov 'swt6621_fw'
& $adb shell 'mkdir -p /userdata/swt6621_fw /userdata/swt6621-rt52'
Get-ChildItem -LiteralPath $fwSrc -File | ForEach-Object {
  & $adb push $_.FullName "/userdata/swt6621_fw/$($_.Name)"
  if ($LASTEXITCODE -ne 0) { throw "push fw $($_.Name) failed" }
}

# Real 6.1.141-rt52 PREEMPT_RT modules (not vermagic-patched Aura kos)
$rtKo = Join-Path $ov 'swt6621-rt52'
Get-ChildItem -LiteralPath $rtKo -Filter '*.ko' | ForEach-Object {
  & $adb push $_.FullName "/userdata/swt6621-rt52/$($_.Name)"
  if ($LASTEXITCODE -ne 0) { throw "push ko $($_.Name) failed" }
}

& $adb shell 'chmod 755 /etc/init.d/S20linkmount /etc/init.d/S21appinit /etc/init.d/S40network /etc/init.d/S50usbdevice /etc/init.d/S99camevision /etc/profile.d/camevision.sh /userdata/camevision-stream.sh /userdata/camevision-wifi.sh /userdata/camevision-imu.sh /userdata/swt6621.sh /userdata/imu-live.sh /userdata/wifi-ble-test.sh /oem/usr/ko/insmod_wifi.sh /userdata/isp_grab.py /userdata/hw_rtsp.py; sync'
Write-Host 'RECOVERY2_OVERLAY_DONE — USB was not restarted.'
Write-Host 'Boot starts: IMU (~8s), Wi-Fi+BLE (~10s), RTSP stream (~12s).'
Write-Host 'Manual: /userdata/camevision-wifi.sh | /userdata/camevision-imu.sh | /userdata/imu-live.sh'
