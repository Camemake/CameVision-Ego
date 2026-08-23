$adb = 'C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe'
$ut = 'C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe'
$deadline = (Get-Date).AddSeconds(90)
while ((Get-Date) -lt $deadline) {
    $ld = & $ut ld 2>&1 | Out-String
    $devs = & $adb devices 2>&1 | Out-String
    $pnp = Get-PnpDevice | Where-Object { $_.Present -and $_.InstanceId -match 'VID_2207' } |
        ForEach-Object { "$($_.Status) $($_.FriendlyName) $($_.InstanceId)" }
    $t = [int]((Get-Date) - $deadline.AddSeconds(-90)).TotalSeconds
    Write-Host "t=$t"
    Write-Host $ld.Trim()
    Write-Host $devs.Trim()
    Write-Host ($pnp -join ' | ')
    if ($devs -match '0558fa189447bc45\s+device' -or $devs -match 'device$') {
        Write-Host 'ADB_UP'
        break
    }
    if ($ld -match 'Maskrom' -and $ld -notmatch 'SerialNo=0') {
        Write-Host 'BACK_TO_MASKROM'
        break
    }
    Start-Sleep -Seconds 4
}
