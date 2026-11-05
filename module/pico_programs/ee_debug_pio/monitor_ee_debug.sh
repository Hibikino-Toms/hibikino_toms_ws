#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv"
target_serial="A437E4B324D4447A"

# Keep PlatformIO's state inside this project.
export PLATFORMIO_CORE_DIR="${project_dir}/.platformio"

if [ ! -x "${venv_dir}/bin/pio" ]; then
    echo "PlatformIO がありません。先に ./setup_environment.sh を実行してください。" >&2
    exit 1
fi

device_port="$(${venv_dir}/bin/python - "${target_serial}" <<'PY'
import sys
from serial.tools import list_ports

target = sys.argv[1]
for port in list_ports.comports():
    if port.serial_number == target:
        print(port.device)
        break
else:
    print(f"シリアル番号 {target} のデバイスが見つかりません。", file=sys.stderr)
    raise SystemExit(1)
PY
)"

cd "${project_dir}"
exec "${venv_dir}/bin/pio" device monitor --port "${device_port}" --baud 115200
