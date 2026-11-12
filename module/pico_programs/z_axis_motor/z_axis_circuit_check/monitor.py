#!/usr/bin/env python3
"""Find only the Z Pico by USB serial number; never send a motion on connect."""
import argparse
import subprocess
import sys
import time

import serial
from serial.tools import list_ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial-number', default='E6613008E3567336')
    parser.add_argument('--observe-seconds', type=float, default=0.0,
                        help='Read-only telemetry capture, then exit')
    args = parser.parse_args()
    matches = [p for p in list_ports.comports() if p.serial_number == args.serial_number]
    if len(matches) != 1:
        raise SystemExit(f'Expected one Z Pico ({args.serial_number}); found {matches}')
    device = matches[0].device
    print(f'Z Pico: {device}, serial={args.serial_number}', flush=True)
    if args.observe_seconds > 0:
        with serial.Serial(device, 115200, timeout=.2, exclusive=True) as port:
            deadline = time.monotonic() + args.observe_seconds
            while time.monotonic() < deadline:
                data = port.readline()
                if data:
                    print(data.decode('utf-8', errors='replace').rstrip(), flush=True)
    else:
        raise SystemExit(subprocess.call([
            sys.executable, '-m', 'serial.tools.miniterm',
            device, '115200', '--raw', '--eol', 'LF']))


if __name__ == '__main__':
    main()
