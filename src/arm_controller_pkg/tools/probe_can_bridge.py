"""Record stopped Arduino boot/SPI/READ diagnostics; never send ARM or MOVE.

Opening Uno resets it and the bridge firmware sends STOP. Stop ROS controllers
and serial monitors before running this tool. Requires existing pyserial.
"""
import argparse
import json
import time
from pathlib import Path

import serial
from serial.tools import list_ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial-number', default='24236323730351504241')
    parser.add_argument('--boots', type=int, default=1)
    parser.add_argument('--reads', type=int, default=30)
    parser.add_argument('--rate', type=float, default=10.)
    parser.add_argument('--spi-check', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.boots < 1 or args.reads < 0 or not 0 < args.rate <= 100:
        parser.error('boots >= 1, reads >= 0, and 0 < rate <= 100 required')
    ports = [p.device for p in list_ports.comports() if p.serial_number == args.serial_number]
    if len(ports) != 1:
        parser.error(f'Expected one Arduino, found {ports}')
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with path.open('x') as output:
        def record(**fields):
            entry = dict(time=time.time(), **fields)
            output.write(json.dumps(entry) + '\n')
            output.flush()
            if fields.get('phase') != 'read' or not fields.get('ok'):
                print(json.dumps(entry), flush=True)

        def receive(port, prefixes, timeout):
            end = time.monotonic() + timeout
            lines = []
            while time.monotonic() < end:
                line = port.readline().decode('ascii', errors='replace').strip()
                if line:
                    lines.append(line)
                    if line.startswith(prefixes + ('ERR,', 'FAULT,')):
                        break
            return lines

        for boot in range(args.boots):
            with serial.Serial(ports[0], 115200, timeout=.1, write_timeout=1., exclusive=True) as port:
                lines = receive(port, ('READY,',), 6.)
                ok = bool(lines) and lines[-1] == 'READY,RMD_ARM_V1,STOPPED'
                record(phase='boot', boot=boot, ok=ok, lines=lines)
                if not ok:
                    failures += 1
                    continue
                if args.spi_check:
                    port.write(b'SPI_CHECK\n')
                    lines = receive(port, ('OK,SPI_CHECK',), 10.)
                    record(phase='spi_check', boot=boot, lines=lines)
                deadline = time.monotonic()
                for seq in range(1, args.reads + 1):
                    started = time.monotonic()
                    port.write(f'READ,{seq}\n'.encode('ascii'))
                    lines = receive(port, (f'S,{seq},',), 1.)
                    ok = bool(lines) and lines[-1].startswith(f'S,{seq},')
                    record(phase='read', boot=boot, seq=seq, ok=ok,
                           duration_sec=time.monotonic()-started, lines=lines)
                    if not ok:
                        failures += 1
                        break
                    deadline += 1. / args.rate
                    time.sleep(max(0., deadline-time.monotonic()))
            time.sleep(.15)
    print(f'Recorded {path}; failures={failures}', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
