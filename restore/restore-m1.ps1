# Flash the complete M1 A-slot firmware at M1's OWN partition offsets.
#
# This is not a hybrid. M1 idblock/SPL, M1 U-Boot, M1 kernel FIT, M1 EROFS
# rootfs, M1 vendor/misc/vbmeta and M1 env. Nothing is retargeted and nothing is
# hash-patched, so it is the same firmware that works on the old board.
#
# Offsets come from M1 env.bin blkdevparts:
#   32K(env),512K@32K(idblock),256K@3584K(vendor),4M(misc),4M(uboot_a),
#   4M(uboot_b),12M(boot_a),12M(boot_b),1536M(system_a),1536M(system_b),
#   512K(vbmeta_a),512K(vbmeta_b),2M(pstore),-(userdata)
#
# env is written LAST so the partition table only appears once the partitions
# behind it are in place.
#
# Only the A slot is written. misc.img gives slot_a priority 15 vs slot_b 14.

$ErrorActionPreference = 'Stop'

$ut     = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$adb    = 'C:\Users\stefa\Downloads\RKDevTool_Release_v2.84\RKDevTool_Release_v2.84\bin\adb.exe'
$donor  = 'C:\Users\stefa\Desktop\CameVision Single\build\m1-donor'
$loader = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb\rv1126b_spl_loader_k4a8g.bin'

$writes = @(
    @{ lba = '0x40';     file = 'idblock.img';  bytes = 524288 },
    @{ lba = '0x1C00';   file = 'vendor.img';   bytes = 262144 },
    @{ lba = '0x1E00';   file = 'misc.img';     bytes = 4194304 },
    @{ lba = '0x3E00';   file = 'uboot_a.img';  bytes = 4194304 },
    @{ lba = '0x7E00';   file = 'boot_a.img';   bytes = 12582912 },
    @{ lba = '0x13E00';  file = 'system_a.img'; bytes = 1610612736 },
    @{ lba = '0x613E00'; file = 'vbmeta_a.img'; bytes = 524288 },
    @{ lba = '0x0';      file = 'env.bin';      bytes = 32768 }
)

Write-Host '=== verify donor images ==='
foreach ($w in $writes) {
    $p = Join-Path $donor $w.file
    if (-not (Test-Path $p)) { throw "Missing $($w.file)" }
    $n = (Get-Item $p).Length
    if ($n -ne $w.bytes) { throw "$($w.file) is $n bytes, expected $($w.bytes)" }
    Write-Host ("  {0,-14} {1,12} bytes -> {2}" -f $w.file, $n, $w.lba)
}

Write-Host '=== ld ==='
$ld = & $ut ld 2>&1 | Out-String
Write-Host $ld
if ($ld -notmatch 'Maskrom') { throw 'Board is not in Maskrom' }

# Never send db twice. Once the usbplug loader is running the serial reads
# "rockchip" and a second db wedges the device.
if ($ld -notmatch 'SerialNo=rockchip') {
    Write-Host '=== db loader ==='
    & $ut db $loader
    Start-Sleep -Seconds 2
} else {
    Write-Host '=== skip db (usbplug already running) ==='
}

foreach ($w in $writes) {
    $p = Join-Path $donor $w.file
    Write-Host "=== wl $($w.lba) $($w.file) ==="
    & $ut wl $w.lba $p
    if ($LASTEXITCODE -ne 0) { throw "wl $($w.file) failed with $LASTEXITCODE" }
}

Write-Host '=== rd ==='
& $ut rd

Write-Host 'M1_FLASH_DONE. Watching for ADB and for a UVC camera.'
for ($i = 1; $i -le 50; $i++) {
    Start-Sleep -Seconds 6
    $ad  = (& $adb devices 2>&1 | Out-String)
    $cam = @(Get-PnpDevice -PresentOnly |
             Where-Object { $_.InstanceId -match 'VID_2207' } |
             ForEach-Object { "$($_.Class):$($_.FriendlyName)" })
    $adbUp = $ad -match "`tdevice"
    Write-Host ("--- {0,4}s adb={1} usb2207=[{2}]" -f ($i * 6), $adbUp, ($cam -join ', '))
    if ($adbUp) { break }
}

Write-Host '=== final ==='
& $adb devices -l
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_2207' } |
    Format-Table Status, Class, FriendlyName, InstanceId -AutoSize
& $ut ld
