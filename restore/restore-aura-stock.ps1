# Flash vendor Luckfox Aura only. Goal: ADB every reset. No camera kernel, no S21 eMMC poke.
# Maskrom: VID 2207 PID 110F, empty serial. Never db twice if SerialNo is rockchip or 0.

$ErrorActionPreference = 'Stop'
$stock = 'C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606'
$loader = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb\rv1126b_spl_loader_k4a8g.bin'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'

Write-Host '=== ld ==='
$ld = & $ut ld 2>&1 | Out-String
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb device.' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'SerialNo=0\s')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db loader (once) ==='
    & $ut db $loader
    if ($LASTEXITCODE -ne 0) { throw 'Download-boot failed' }
    Start-Sleep -Seconds 2
    & $ut ld
} else {
    Write-Host '=== skip db (already usbplug) ==='
}

$writes = @(
    @{ lba = '0x0';      file = 'env.img' },
    @{ lba = '0x40';     file = 'idblock.img' },
    @{ lba = '0x440';    file = 'uboot.img' },
    @{ lba = '0x2440';   file = 'boot.img' },
    @{ lba = '0x7C40';   file = 'userdata.img' },
    @{ lba = '0x207C40'; file = 'oem.img' },
    @{ lba = '0x607C40'; file = 'rootfs.img' }
)
foreach ($w in $writes) {
    $path = Join-Path $stock $w.file
    if (-not (Test-Path $path)) { throw "Missing $path" }
    Write-Host ("=== wl {0} {1} ===" -f $w.lba, $w.file)
    & $ut wl $w.lba $path
    if ($LASTEXITCODE -ne 0) { throw "Write failed: $($w.file)" }
}

Write-Host '=== rd ==='
Write-Host 'Release BOOT, then reset should boot stock Aura Linux + ADB.'
& $ut rd
Write-Host 'AURA_STOCK_FLASH_DONE'
