#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rule_source="${project_dir}/98-ee-pico2-boot.rules"
rule_target="/etc/udev/rules.d/98-ee-pico2-boot.rules"

if ! id -nG | tr ' ' '\n' | grep -qx plugdev; then
    echo '現在のユーザーはplugdevグループに所属していません。管理者に設定を依頼してください。' >&2
    exit 1
fi
if [ -e "${rule_target}" ] && ! cmp -s "${rule_source}" "${rule_target}"; then
    echo "既存の異なる設定を保護するため停止しました: ${rule_target}" >&2
    exit 1
fi

sudo install -o root -g root -m 0644 "${rule_source}" "${rule_target}"
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --subsystem-match=usb --attr-match=idVendor=2e8a --attr-match=idProduct=000f
sudo udevadm settle

echo 'Pico 2のBOOTSELモード用USB権限を設定しました。'
echo 'PicoのUSBを抜き、BOOTSELを押さずに接続し直してから ./upload_ee_debug.sh を実行してください。'
