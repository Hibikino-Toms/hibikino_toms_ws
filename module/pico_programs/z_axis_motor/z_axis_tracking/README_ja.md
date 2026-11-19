# Z軸の離散画像補正用Picoファームウェア

既存 `../z_axis_pico2.ino` を変更せずに追加した専用ファームウェアです。起動時はAWO=LOWの通電保持で、移動・原点復帰は始まりません。停止／異常／USB切断でも自動で通電解除しません。

| 機能 | ピン／設定 |
|---|---|
| 下降CW | GP16 / GP17 |
| 上昇CCW | GP18 / GP19 |
| 保持AWO | GP20、LOW=通電保持 |
| 原点 | GP26、実測LOW=押下または信号断、HIGH=解除 |
| 換算・範囲 | 既存の200step/mm、0～450mm。実距離未校正 |
| 原点探索 | ROSの `home_speed_m_s` を使用（統合YAMLは10mm/s）。最大450mm・120秒、押下後5mm離脱で完了。速度省略の旧指令は5mm/s |
| 起動時に原点信号LOW | 最大2mm離脱を試み、解除しなければ停止 |
| 補正速度上限・加速度 | 20mm/s・20mm/s²。ROS既定は10mm/s |
| 監視 | ZINFO等が600ms途絶／USB切断で停止。USB TX満杯時は状態送信を破棄して監視継続 |

原点信号で下降を停止し、そこから離れる上昇は許可します。上端には独立したリミットがありません。範囲はパルス位置のソフト制限です。断線とスイッチ押下は区別できず、独立エンコーダや実位置監視はありません。脱調を検出したとの扱いはできません。

## ビルド・書き込み

既存PlatformIO環境とArduino Stepperライブラリを使います。

```bash
cd ~/hibikino_toms_ws
~/.platformio/penv/bin/pio run -d module/pico_programs/z_axis_motor/z_axis_tracking
```

**Z軸を支持し、Zを使うROSノードとモニターを終了してから書き込みます。** 再起動で保持が途切れる可能性があります。USBシリアル番号 `E6613008E3567336` が対象であることを必ず照合してください。ttyACM番号は変わります。

```bash
python3 - <<'PY'
from serial.tools import list_ports
for p in list_ports.comports():
    print(p.device, p.serial_number, p.product)
PY
# 下のポートは対象Z Picoの実際のポートに置換する。
~/.platformio/penv/bin/pio run \
  -d module/pico_programs/z_axis_motor/z_axis_tracking \
  -t upload --upload-port /dev/ttyACM1
```

自動BOOTSEL移行で再認識しなければ、対象PicoだけをBOOTSELを押しながらUSB接続します。対象と確認した `RPI-RP2` へ `.pio/build/z_axis_tracking/firmware.uf2` をコピーする標準UF2方式も使えます。別のPicoへは書き込まないでください。書き込み後のUSB製品名は `Z_TRACKING_V1` です。

## 通信仕様

115200bps、ASCII、改行区切り。ROS trackerだけがポートを所有します。

| 指令 | 意味 |
|---|---|
| `ZINFO` | 非移動の状態照会兼heartbeat。ホストは10Hz送信 |
| `ZHOME,<id>,<速度mm/s>` | 速度指定の原点復帰。0.5～20mm/s。XY停止はROS側が先に確認 |
| `ZHOME,<id>` | 従来互換の5mm/s原点復帰 |
| `ZMOVE,<id>,<絶対位置mm整数>,<速度mm/s>` | 原点確定後のみ受理、動作中の追加目標は拒否、キューなし |
| `ZSTOP` | 移動停止・通電保持。原点復帰を中断した場合は原点未確定 |

状態は `ZTRACK_V1,STATE,<step位置>,<原点確定0/1>,<動作中0/1>,<通電0/1>,<原点LOW0/1>,<id>,<異常理由>`。エラーは `ZERR,<理由>`。動作完了の判断には指令idとbusy=falseを使い、要求受理と区別します。

旧サービス用の `0,0` / `1,0` / `2,0` / `3,位置mm` と2整数の完了応答も残しています。旧モードでは周期STATEやheartbeat監視を出さず、USB切断・移動時間上限・原点入力監視で停止します。旧 `0,0` だけは操作者からの明示的な通電解除です。旧サービスと追従ノードを同時起動しないでください。旧実装でコメント5mm・実際5000stepだった原点離脱は、新実装では1000step（既存換算で5mm）です。

## 書き込み記録（2026-11-17）

### 原点復帰速度の設定追加

`src/vision_pkg/config/vision_xy_tracking.yaml` の `z_tracking.home_speed_m_s` に原点復帰速度をm/sで指定します。現在は0.010（10mm/s）で、原点探索とスイッチ離脱に共通です。加速度20mm/s²・リミット極性・最大探索距離・原点復帰時間上限・5mm離脱は変更していません。通常のZ移動は別の `speed_m_s` を使用します。

速度指定付き `ZHOME` を受け付ける今回のファームウェアへの更新が必要です。旧ファームウェアは新指令を拒否します。書き込み前はZを支持し、関連ROSノード・シリアルモニターを終了します。新しい原点復帰速度での実機動作は未確認です。

2026-11-17、ユーザーのZ支持・関連ノード終了確認後にビルド・書き込みを実施しました。自動1200bps移行は失敗したため、ユーザーがBOOTSELで再接続し、USB位置 `1-4.1.4.1` とブートシリアル `E0C9125B0D9B` を照合してUF2を転送しました。再認識したシリアル `E6613008E3567336` / `/dev/ttyACM1` に `ZINFO` だけを送り、`homed=0,busy=0,powered=1,fault=NONE` を確認しました。原点復帰・移動指令は送っていません。次回configured起動時には原点復帰を行います。

### 以前の書き込み記録

Z軸支持とモニター終了のユーザー確認後、対象シリアル `E6613008E3567336` のPicoへ書き込みました。自動1200bpsリセットでは再認識されず、ユーザーがBOOTSELで接続し直した後、既知のUSB位置 `1-4.1.4.1`（Bootシリアル `E0C9125B0D9B`）を照合しUF2をコピーしました。再認識後の製品名は `Z_TRACKING_V1`、ポートは `/dev/ttyACM1`、シリアルは元と同じです。

状態照会は `busy=0, homed=0, powered=1, limit_active=1, command_id=0, fault=NONE`。`ZINFO` と終了時 `ZSTOP` だけを送り、移動や原点復帰は行っていません。原点入力LOWは押下か信号異常なので、実機確認が必要です。パルス位置0は原点未確定時の初期値であり実位置ではありません。詳細とハッシュは [記録](../../../../src/arm_controller_pkg/validation/z_tracking_20261117/flash_and_status.json) を参照してください。

## 実機を動かさない検証

2026-11-17追記: 実機が `ZMOVE,201,5,10.000`（現在位置5mm、移動不要）を `RANGE_OR_SPEED` で拒否する現象を確認しました。速度の浮動小数 `sscanf` を使わず、文字列を `strtod` で解釈して末尾も検証するよう修正しています。数値範囲・速度上限は変更していません。支持確認後、同じZ PicoへUSB位置 `1-4.1.4.1` とBOOTSELシリアル `E0C9125B0D9B` を照合して書き込み、原点復帰と画像Z補正の実動作を確認しました。小数速度・不正末尾・NaNの模擬検証も追加しています。

新しい書き込みハッシュとROSBAGはワークスペース直下 `tracking_trials_20261117/` にあります。上記の初回書き込み時の状態照会記録とは別の実動作記録です。

```bash
g++ -std=c++17 -Wall -Wextra -Werror \
  -I module/pico_programs/z_axis_motor/z_axis_tracking/test/fakes \
  module/pico_programs/z_axis_motor/z_axis_tracking/test/test_firmware.cpp \
  -o /tmp/z_tracking_firmware_test
/tmp/z_tracking_firmware_test
```

実スケッチを模擬GPIO/時間/USBで実行します。正常原点復帰、未原点移動拒否、初期LOWの離脱上限、原点途中の停止、下降禁止／上昇許可、停止、heartbeat途絶、USB切断、TX詰まり、動作時間上限、最新指令の非蓄積、旧モード応答を確認します。実配線・波形・移動距離・荷重での保持性能は保証しません。

ROS起動・原点サービス・設定・診断は [vision_pkgの手順](../../../../src/vision_pkg/README_realtime_ja.md) を参照してください。
