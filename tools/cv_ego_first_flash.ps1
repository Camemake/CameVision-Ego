# First boot of CameVision Ego with the Single-proven images.
# Includes oem so a blank eMMC has /oem. Does not wipe a custom userdata if we skip it.
$ErrorActionPreference = 'Stop'
$kg = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb'
if (-not (Test-Path $kg)) {
  $kg = 'C:\Users\stefa\Desktop\CameVision Ego\restore\known-good-20260819-camera-adb'
}
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$loader = Join-Path $kg 'rv1126b_spl_loader_k4a8g.bin'

function Ld { & $ut ld 2>&1 | Out-String }

$ld = Ld
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'SerialNo=0')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db once ==='
    & $ut db $loader
    if ($LASTEXITCODE -ne 0) { throw 'db failed' }
    Start-Sleep -Seconds 2
    Write-Host (Ld)
} else {
    Write-Host '=== skip db ==='
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
    if ($LASTEXITCODE -ne 0) { throw "write failed $($w.file)" }
}

Write-Host '=== skipped userdata ==='
Write-Host '=== rd — RELEASE BOOT ==='
Start-Sleep -Seconds 3
& $ut rd
Write-Host 'EGO_FLASH_DONE'
