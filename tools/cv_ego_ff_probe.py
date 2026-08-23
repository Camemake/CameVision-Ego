#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = (
        "timeout -k 1 4 ffmpeg -hide_banner -f v4l2 -list_formats all -i /dev/video12 2>&1 | tail -40; "
        "echo === try gray encode ===; "
        "timeout -k 1 5 ffmpeg -hide_banner -loglevel error -f v4l2 -video_size 1920x1200 -i /dev/video12 "
        "-frames:v 2 -q:v 6 /tmp/cam1_try.jpg; echo rc:$?; ls -l /tmp/cam1_try.jpg"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
