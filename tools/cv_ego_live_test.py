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
    tests = [
        [ADB, "-s", s, "exec-out", "sh", "-c", "echo HELLO"],
        [ADB, "-s", s, "exec-out", "sh", "-c", "which v4l2-ctl ffmpeg nc; ls /usr/bin/v4l2-ctl"],
        [ADB, "-s", s, "shell", "timeout -k 1 6 sh -c 'v4l2-ctl -d /dev/video12 --stream-mmap=4 --stream-count=1 --stream-to=- --stream-poll 2>/tmp/v4l.err | wc -c'; echo ---; cat /tmp/v4l.err"],
    ]
    for t in tests:
        print(">>", t[-1][:80])
        r = subprocess.run(t, capture_output=True, timeout=20)
        print("stdout", r.stdout[:200])
        print("stderr", r.stderr[:200])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
