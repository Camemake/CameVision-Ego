#!/usr/bin/env python3
"""Run a remote command over CameVision busybox telnetd (port 2323)."""
import argparse
import socket
import sys
import time

HOST = "192.168.1.23"
PORT = 2323


def run(cmd: str, wait: float = 4.0) -> str:
    s = socket.create_connection((HOST, PORT), 8)
    s.settimeout(wait + 2)
    time.sleep(0.25)
    try:
        s.recv(8192)
    except Exception:
        pass
    payload = (cmd.rstrip() + "\necho __END_CV__\n").encode()
    s.send(payload)
    time.sleep(wait)
    chunks = []
    s.settimeout(1.5)
    while True:
        try:
            b = s.recv(65536)
            if not b:
                break
            chunks.append(b)
            if b"__END_CV__" in b:
                # small extra drain
                try:
                    chunks.append(s.recv(65536))
                except Exception:
                    pass
                break
        except Exception:
            break
    s.close()
    text = b"".join(chunks).decode("utf-8", "replace")
    return text


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd")
    p.add_argument("--wait", type=float, default=4.0)
    args = p.parse_args()
    sys.stdout.write(run(args.cmd, args.wait))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
