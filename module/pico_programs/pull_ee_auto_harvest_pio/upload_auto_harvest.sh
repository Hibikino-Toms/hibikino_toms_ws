#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pio_dir="${project_dir}/../ee_debug_pio"
pio_bin="${pio_dir}/.venv/bin/pio"
target_serial="A437E4B324D4447A"

if [[ ! -x "${pio_bin}" ]]; then
    echo "PlatformIO CLI not found: ${pio_bin}" >&2
    exit 1
fi

device_port="$(python3 - "${target_serial}" <<'PY'
import sys
from serial.tools import list_ports

target = sys.argv[1]
matches = [port.device for port in list_ports.comports()
           if port.serial_number == target]
if len(matches) != 1:
    raise SystemExit(f"Expected exactly one Pico with serial {target}; found {matches}")
print(matches[0])
PY
)"

if fuser -s "${device_port}"; then
    echo "Refusing upload: ${device_port} is already open by another process." >&2
    fuser -v "${device_port}" >&2 || true
    exit 2
fi

echo "Uploading auto-harvest firmware to ${device_port} (SERIAL=${target_serial})"
cd "${project_dir}"
PLATFORMIO_CORE_DIR="${pio_dir}/.platformio" \
    "${pio_bin}" run --target upload --upload-port "${device_port}"
