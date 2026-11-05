#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv"
target_serial="A437E4B324D4447A"

# Keep PlatformIO's downloaded platforms/tools inside this project.
export PLATFORMIO_CORE_DIR="${project_dir}/.platformio"

if [ ! -x "${venv_dir}/bin/pio" ]; then
    echo "PlatformIO がありません。先に ./setup_environment.sh を実行してください。" >&2
    exit 1
fi

device_port="$(${venv_dir}/bin/python - "${target_serial}" <<'PY'
import sys
from serial.tools import list_ports

target = sys.argv[1]
matches = [port.device for port in list_ports.comports()
           if port.serial_number == target]

if len(matches) != 1:
    if not matches:
        print(f"シリアル番号 {target} のデバイスが見つかりません。", file=sys.stderr)
    else:
        print(f"対象デバイスが複数あります: {matches}", file=sys.stderr)
    raise SystemExit(1)

print(matches[0])
PY
)"

echo "書き込み先: ${device_port} (SERIAL=${target_serial})"
cd "${project_dir}"
"${venv_dir}/bin/pio" run --target upload --upload-port "${device_port}"
