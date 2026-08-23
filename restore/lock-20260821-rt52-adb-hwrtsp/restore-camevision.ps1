# CameVision Single only. Never writes Luckfox Aura kernel/rootfs/oem.
# Loader already up (SerialNo=0|rockchip): do not db again.

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$loader = Join-Path $here 'rv1126b_spl_loader_k4a8g.bin'
$userdata = 'C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\userdata.img'

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
    @{ lba = '0x0';      file = (Join-Path $here 'env.img') },
    @{ lba = '0x40';     file = (Join-Path $here 'idblock.img') },
    @{ lba = '0x440';    file = (Join-Path $here 'uboot.img') },
    @{ lba = '0x2440';   file = (Join-Path $here 'camevision_boot.img') },
    @{ lba = '0x7C40';   file = $userdata },
    @{ lba = '0x207C40'; file = (Join-Path $here 'oem_noko.img') },
    @{ lba = '0x607C40'; file = (Join-Path $here 'rootfs_bootstable.img') }
)
foreach ($w in $writes) {
    if (-not (Test-Path $w.file)) { throw "Missing $($w.file)" }
    Write-Host ("=== wl {0} {1} ===" -f $w.lba, [IO.Path]::GetFileName($w.file))
    & $ut wl $w.lba $w.file
    if ($LASTEXITCODE -ne 0) { throw "Write failed: $($w.file)" }
}

Write-Host '=== RELEASE BOOT, then reset ==='
Write-Host 'Fingers off BOOT. If you are holding it, Linux will not start.'
Start-Sleep -Seconds 4
& $ut rd
Write-Host 'CAMEVISION_FLASH_DONE'
