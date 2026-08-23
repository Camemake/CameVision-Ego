# Flash Wi-Fi + SPI IMU DTB over ADB. Run after apply-overlay, before the UVC reboot.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$rec2 = 'C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream'
$adbCandidates = @(
  'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe',
  'C:\Users\stefa\Downloads\RKDevTool_Release_v2.84\RKDevTool_Release_v2.84\bin\adb.exe'
)
$adb = $adbCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $adb) { throw 'adb.exe not found' }

$img = Join-Path $here 'camevision_boot_wifi_imu.img'
$bak = Join-Path $here 'boot_before_wifi_imu.img'
if (-not (Test-Path $img)) { $img = Join-Path $rec2 'camevision_boot_wifi_imu.img' }
if (-not (Test-Path $img)) { $img = 'C:\Users\stefa\Desktop\CameVision Single\build\camevision_boot_wifi_imu.img' }
if (-not (Test-Path $img)) { throw 'missing camevision_boot_wifi_imu.img' }

& $adb wait-for-device
Write-Host 'backing up live boot partition'
& $adb pull /dev/block/by-name/boot $bak
if ($LASTEXITCODE -ne 0) { throw 'boot backup failed' }
& $adb push $img /userdata/camevision_boot_wifi_imu.img
if ($LASTEXITCODE -ne 0) { throw 'push boot.img failed' }
& $adb shell 'dd if=/userdata/camevision_boot_wifi_imu.img of=/dev/mmcblk0p4 bs=1M conv=fsync; sync'
if ($LASTEXITCODE -ne 0) { throw 'dd boot failed' }
Write-Host 'BOOT_FLASHED — rebooting. USB becomes UVC CameVision Single; debug on Wi-Fi :2323'
& $adb reboot
