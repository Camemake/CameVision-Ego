# Push V0.2 overlay. Does not flash boot. USB stays ADB.
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root
python "$root\tools\cv_ego_overlay_deploy.py"
python "$root\tools\cv_ego_autostart.py" --install
