# ee_debug の書き込み環境

`../ee_debug.ino` を Raspberry Pi Pico 2 W に書き込みます。

対象デバイス:

- 現在のポート: `/dev/ttyACM2`
- USBシリアル番号: `A437E4B324D4447A`
- ボード: `rpipico2w`
- 通信速度: `115200`

`/dev/ttyACM2` は再接続時に変わることがあるため、スクリプトはポート名ではなく USB シリアル番号で対象を特定します。

## 初回セットアップ

```bash
cd /home/ylab/hibikino_toms_ws/module/pico_programs/ee_debug_pio
./setup_environment.sh
```

## 書き込み

Linuxで `picotool was unable to connect` と表示される場合は、初回に
次のコマンドでPico 2のBOOTSELモード（USB `2e8a:000f`）用の権限を設定します。
sudoのパスワード入力が必要です。実行ユーザーは `plugdev` グループに
所属している必要があります。

```bash
bash setup_usb_permissions.sh
```

設定後、PicoのUSBを抜き、BOOTSELを押さずに接続し直します。
書き込みスクリプトは通常モードのシリアル番号を使って対象を識別します。

ROS 2 ノードやシリアルモニタを停止してから実行します。

```bash
./upload_ee_debug.sh
```

## シリアルモニタ

```bash
./monitor_ee_debug.sh
```

終了は `Ctrl-C` です。

## デバイス確認

```bash
python3 -m serial.tools.list_ports -v
```

`SERIAL=A437E4B324D4447A` と表示されるデバイスが対象です。
