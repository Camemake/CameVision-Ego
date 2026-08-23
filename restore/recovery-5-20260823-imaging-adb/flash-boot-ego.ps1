# Flash Recovery 5 Ego imaging boot.img over ADB. USB stays ADB.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$adb = 'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe'
$img = Join-Path $here 'camevision_boot_ego.img'
if (-not (Test-Path $img)) { throw "missing $img" }

$serial = $null
foreach ($line in (& $adb devices)) {
    if ($line -match '^(\S+)\s+device') { $serial = $Matches[1]; break }
}
if (-not $serial) { throw 'no ADB device' }

& $adb -s $serial wait-for-device
Write-Host "pushing Recovery 5 boot.img to $serial"
& $adb -s $serial push $img /userdata/camevision_boot_ego.img
if ($LASTEXITCODE -ne 0) { throw 'push failed' }
& $adb -s $serial shell 'dd if=/userdata/camevision_boot_ego.img of=/dev/mmcblk0p4 bs=1M conv=fsync; sync'
if ($LASTEXITCODE -ne 0) { throw 'dd boot failed' }
Write-Host 'BOOT_FLASHED — rebooting. USB stays ADB CameVision Ego'
& $adb -s $serial reboot
