# Push Recovery 6 stereo overlay. Does not flash boot. 3A / IMU stay up.
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root
python "$root\tools\cv_ego_stereo_start.py"
