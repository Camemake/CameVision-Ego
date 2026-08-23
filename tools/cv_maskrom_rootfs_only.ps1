# Maskrom: one loader, rewrite rootfs only (ADB S50). No oem/boot/userdata.
$ErrorActionPreference = 'Stop'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$kg = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb'
$loader = Join-Path $kg 'rv1126b_spl_loader_k4a8g.bin'
$rootfs = Join-Path $kg 'rootfs_bootstable.img'

Write-Host '=== ld ==='
$ld = & $ut ld 2>&1 | Out-String
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb device.' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'Mode=Loader')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db loader (once) ==='
    & $ut db $loader
    if ($LASTEXITCODE -ne 0) { throw 'db failed' }
    Start-Sleep -Seconds 2
    & $ut ld
} else {
    Write-Host '=== skip db (loader already up) ==='
}

Write-Host '=== wl rootfs only ==='
& $ut wl 0x607C40 $rootfs
if ($LASTEXITCODE -ne 0) { throw 'rootfs write failed' }

Write-Host '=== rd (RELEASE BOOT) ==='
Start-Sleep -Seconds 2
& $ut rd
Write-Host 'ROOTFS_ONLY_DONE'
