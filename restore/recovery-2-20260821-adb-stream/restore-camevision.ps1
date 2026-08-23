# CameVision Single recovery 2. Never writes Luckfox Aura kernel.
# Does not wipe userdata (kmpp + stream live there).
# Loader already up (SerialNo=0|rockchip): do not db again.

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$kg = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$loader = Join-Path $kg 'rv1126b_spl_loader_k4a8g.bin'

Write-Host '=== ld ==='
$ld = & $ut ld 2>&1 | Out-String
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb device.' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'SerialNo=0\s')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db loader (once, RAM only) ==='
    & $ut db $loader
    if ($LASTEXITCODE -ne 0) { throw 'Download-boot failed' }
    Start-Sleep -Seconds 2
    & $ut ld
} else {
    Write-Host '=== skip db (already usbplug) ==='
}

$writes = @(
    @{ lba = '0x0';      file = (Join-Path $kg 'env.img') },
    @{ lba = '0x40';     file = (Join-Path $kg 'idblock.img') },
    @{ lba = '0x440';    file = (Join-Path $kg 'uboot.img') },
    @{ lba = '0x2440';   file = (Join-Path $kg 'camevision_boot.img') },
    @{ lba = '0x207C40'; file = (Join-Path $kg 'oem_noko.img') },
    @{ lba = '0x607C40'; file = (Join-Path $kg 'rootfs_bootstable.img') }
)
foreach ($w in $writes) {
    if (-not (Test-Path $w.file)) { throw "Missing $($w.file)" }
    Write-Host ("=== wl {0} {1} ===" -f $w.lba, [IO.Path]::GetFileName($w.file))
    & $ut wl $w.lba $w.file
    if ($LASTEXITCODE -ne 0) { throw "Write failed: $($w.file)" }
}

Write-Host '=== skipped userdata (recovery 2 keeps kmpp/stream) ==='
Write-Host '=== RELEASE BOOT, then reset ==='
Write-Host 'Fingers off BOOT. If USB stays empty: unplug USB-C, plug in, tap RESET only.'
Start-Sleep -Seconds 4
& $ut rd
Write-Host 'RECOVERY2_FLASH_DONE — when ADB is up, run apply-overlay.ps1'
