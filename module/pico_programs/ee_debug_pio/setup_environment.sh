#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 が見つかりません。" >&2
    exit 1
fi

if [ ! -x "${venv_dir}/bin/python" ]; then
    python3 -m venv "${venv_dir}"
fi

"${venv_dir}/bin/python" -m pip install --upgrade pip platformio

echo "環境構築が完了しました。"
echo "次に ./upload_ee_debug.sh を実行してください。"
