Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } |
  ForEach-Object { '{0} | {1} | {2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }
