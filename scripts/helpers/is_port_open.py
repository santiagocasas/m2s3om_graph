#!/usr/bin/env python3
import socket
import sys


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    host = sys.argv[1]
    port = int(sys.argv[2])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        code = sock.connect_ex((host, port))
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
