Write-Host '=== PING ==='
ping -n 2 -w 800 192.168.1.23
Write-Host '=== USB PnP ==='
Get-PnpDevice | Where-Object {
  $_.Present -and (
    $_.InstanceId -match 'VID_2207' -or
    $_.FriendlyName -match 'CameVision|UVC|Rockchip|ADB|Android|Maskrom|Loader'
  )
} | ForEach-Object { '{0} | {1} | {2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }
Write-Host '=== USBVID ==='
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'USB\\VID_' } |
  Select-Object -First 40 Status, FriendlyName, InstanceId |
  Format-Table -AutoSize
