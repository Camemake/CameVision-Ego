# Push AM / MIRA220 overlay. Does not flash SC233HGS. USB stays ADB.
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root
python "$root\tools\cv_ego_overlay_deploy_am.py"
