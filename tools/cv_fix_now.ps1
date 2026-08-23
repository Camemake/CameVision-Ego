# One-shot: Maskrom -> ADB Linux -> overlay -> Wi-Fi. No UVC. No oem/userdata wipe.
$ErrorActionPreference = 'Stop'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$adb = 'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe'
$kg = 'C:\Users\stefa\Desktop\CameVision Single\restore\known-good-20260819-camera-adb'
$rec = 'C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream'
$loader = Join-Path $kg 'rv1126b_spl_loader_k4a8g.bin'
$boot = Join-Path $rec 'camevision_boot_wifi_imu.img'

function Ld {
    & $ut ld 2>&1 | Out-String
}

Write-Host '=== 1. Maskrom / loader ==='
$ld = Ld
Write-Host $ld
if ($ld -notmatch 'Maskrom|Loader|rockchip') { throw 'No Rockusb. Hold BOOT, tap RESET, then re-run.' }

$loaderUp = ($ld -match 'SerialNo=rockchip') -or ($ld -match 'SerialNo=0')
if ($ld -match 'Maskrom' -and -not $loaderUp) {
    Write-Host '=== db loader (once) ==='
    & $ut db $loader
    if ($LASTEXITCODE -ne 0) { throw 'db failed' }
    Start-Sleep -Seconds 2
    Write-Host (Ld)
} else {
    Write-Host '=== skip db ==='
}

Write-Host '=== 2. write Wi-Fi/IMU boot (rootfs already bootstable ADB) ==='
& $ut wl 0x2440 $boot
if ($LASTEXITCODE -ne 0) { throw 'boot write failed' }

Write-Host '=== 3. rd — fingers OFF BOOT ==='
Start-Sleep -Seconds 2
& $ut rd

Write-Host '=== 4. wait ADB (USB stays ADB, no UVC) ==='
$deadline = (Get-Date).AddSeconds(120)
$ok = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 4
    $ld = Ld
    $devs = & $adb devices 2>&1 | Out-String
    $pnp = @(Get-PnpDevice | Where-Object { $_.Present -and $_.InstanceId -match 'VID_2207' } | ForEach-Object { "$($_.Status) $($_.FriendlyName)" })
    Write-Host ("--- {0:HH:mm:ss} ---" -f (Get-Date))
    Write-Host $ld.Trim()
    Write-Host $devs.Trim()
    Write-Host ($pnp -join ' | ')
    if ($devs -match '0558fa189447bc45\s+device' -or ($devs -match '\sdevice\s' -and $devs -notmatch 'List of devices attached\s*$')) {
        $ok = $true
        break
    }
    if ($ld -match 'Maskrom') {
        Write-Host 'STILL MASKROM — release BOOT completely, tap RESET only (do not hold BOOT).'
    }
}
if (-not $ok) { throw 'ADB did not come up. Release BOOT, tap RESET, keep USB plugged.' }

Write-Host '=== 5. overlay + kill leftover UVC flag ==='
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $rec 'apply-overlay.ps1')
if ($LASTEXITCODE -ne 0) { throw 'overlay failed' }

& $adb shell 'mount -o remount,rw /userdata; rm -f /userdata/uvc-webcam.on /userdata/S50usbdevice.uvc-rk; sync'
& $adb shell 'ifconfig lo up; busybox telnetd -l /bin/sh -p 2323; /userdata/camevision-wifi.sh' 
Write-Host '=== 6. status ==='
& $adb shell 'echo -n product=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product; echo; echo -n udc=; cat /sys/kernel/config/usb_gadget/rockchip/UDC; echo; echo -n state=; cat /sys/class/udc/21500000.usb/state; echo; ip -4 addr show wlan0; ls /dev/video13; cat /proc/uptime'
Write-Host 'FIX_DONE'
