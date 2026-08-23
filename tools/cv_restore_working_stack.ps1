# Restore the working CameVision stack: Linux + Wi-Fi + RKAIQ + RKISP + UVC.
# First boot is ADB so we can leave Maskrom. Then the working files go back on.
$ErrorActionPreference = 'Stop'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$adb = 'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe'
$kg = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb'
$rec = 'C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream'
$ov = Join-Path $rec 'overlay'
$live = 'C:\Users\stefa\Desktop\CameVision Single\build\live'

function Ld { & $ut ld 2>&1 | Out-String }
function PushUnix([string]$src, [string]$dst) {
  $tmp = Join-Path $env:TEMP ([IO.Path]::GetFileName($src) + '.unix')
  $bytes = [IO.File]::ReadAllBytes($src)
  $text = [Text.Encoding]::UTF8.GetString($bytes) -replace "`r`n", "`n" -replace "`r", "`n"
  $utf8 = New-Object System.Text.UTF8Encoding $false
  [IO.File]::WriteAllText($tmp, $text, $utf8)
  & $adb push $tmp $dst
  if ($LASTEXITCODE -ne 0) { throw "push failed $dst" }
}

$ld = Ld
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb. Hold BOOT, tap RESET once.' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'SerialNo=0')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db once ==='
    & $ut db (Join-Path $kg 'rv1126b_spl_loader_k4a8g.bin')
    if ($LASTEXITCODE -ne 0) { throw 'db failed' }
    Start-Sleep -Seconds 2
} else {
    Write-Host '=== skip db ==='
}

foreach ($w in @(
    @{ lba = '0x0';      file = (Join-Path $kg 'env.img') },
    @{ lba = '0x40';     file = (Join-Path $kg 'idblock.img') },
    @{ lba = '0x440';    file = (Join-Path $kg 'uboot.img') },
    @{ lba = '0x2440';   file = (Join-Path $kg 'camevision_boot.img') },
    @{ lba = '0x607C40'; file = (Join-Path $kg 'rootfs_bootstable.img') }
)) {
    Write-Host ("=== wl {0} {1} ===" -f $w.lba, [IO.Path]::GetFileName($w.file))
    & $ut wl $w.lba $w.file
    if ($LASTEXITCODE -ne 0) { throw "write failed $($w.file)" }
}

Write-Host '=== rd ==='
Start-Sleep -Seconds 2
& $ut rd

$ok = $false
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    $devs = & $adb devices 2>&1 | Out-String
    Write-Host ("--- {0:HH:mm:ss} ---" -f (Get-Date))
    Write-Host $devs.Trim()
    Write-Host (Ld).Trim()
    if ($devs -match '0558fa189447bc45' -or $devs -match '(?m)^[0-9a-f]+\s+device') {
        $ok = $true
        break
    }
}
if (-not $ok) { throw 'Linux did not reach ADB. Release BOOT, tap RESET only.' }

Write-Host '=== overlay + working camera files ==='
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rec 'apply-overlay.ps1')
if ($LASTEXITCODE -ne 0) { throw 'overlay failed' }

& $adb shell 'mount -o remount,rw /; mount -o remount,rw /oem; mount -o remount,rw /userdata'
PushUnix (Join-Path $ov 'camevision-aiq.sh') /userdata/camevision-aiq.sh
PushUnix (Join-Path $ov 'camevision-uvc-cam.sh') /userdata/camevision-uvc-cam.sh
PushUnix (Join-Path $ov 'camevision-uvc-mjpg.py') /userdata/camevision-uvc-mjpg.py
PushUnix (Join-Path $ov 'S99camevision') /etc/init.d/S99camevision
PushUnix (Join-Path $live 'S50usbdevice.uvc-rk') /etc/init.d/S50usbdevice
& $adb shell 'chmod 755 /userdata/camevision-aiq.sh /userdata/camevision-uvc-cam.sh /userdata/camevision-uvc-mjpg.py /etc/init.d/S99camevision /etc/init.d/S50usbdevice; touch /userdata/uvc-webcam.on; rm -f /userdata/uvc-webcam.off; sync'

$wiboot = Join-Path $rec 'camevision_boot_wifi_imu.img'
if (Test-Path $wiboot) {
    Write-Host '=== wifi/IMU boot via ADB ==='
    & $adb push $wiboot /userdata/camevision_boot_wifi_imu.img
    & $adb shell 'dd if=/userdata/camevision_boot_wifi_imu.img of=/dev/mmcblk0p4 bs=1M conv=fsync; sync'
}

Write-Host '=== start Wi-Fi + RKAIQ + RKISP now ==='
& $adb shell 'busybox telnetd -l /bin/sh -p 2323; /userdata/camevision-wifi.sh; /userdata/camevision-aiq.sh; /userdata/camevision-uvc-cam.sh; echo STACK; ip -4 addr show wlan0; ps | grep -E "rkaiq_3A|v4l2-ctl|uvc-mjpg|adbd" | grep -v grep'

Write-Host '=== reboot into working UVC+Wi-Fi stack ==='
& $adb reboot
Write-Host 'WORKING_STACK_INSTALLED — board rebooting. USB becomes CameVision Single. Debug on Wi-Fi 192.168.1.23:2323'
