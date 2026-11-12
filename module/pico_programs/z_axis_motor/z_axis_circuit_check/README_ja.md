# Z軸のモーター・回路確認

対象はPico（RP2040）。2026-11-12にZ軸用として接続し直した基板は、書き込み前にUSB device 041（USB物理位置 `1-4.1.4.1`）、書き込み後のシリアル番号は `E6613008E3567336`（実測）です。別のPico W（`E6613008E3277436`）やEE用Pico 2W（`A437E4B324D4447A`）とはシリアル番号で区別してください。
`z_axis_circuit_check.ino` は既存 `../z_axis_pico2.ino` のピンとStepper出力方式に合わせた、独立した確認用プログラムです。
Arduino IDEではこのサブフォルダの `.ino` を開いてください。親フォルダのスケッチと連結しない構成です。

| 接続 | Pico GPIO | 動作 |
|---|---|---|
| CW A/B | GP16 / GP17 | 既存コードで下降に対応 |
| CCW A/B | GP18 / GP19 | 既存コードで上昇に対応 |
| AWO | GP20 | LOWで通電保持、HIGHで通電解除 |
| 原点信号 | GP26 | 今回の実測では通常HIGH、押下・信号線取り外し時LOW（LOWをトリップ扱い） |

GP26は基板の物理ピン31です。GPIO番号と物理ピン番号を区別してください。
今回の測定は「未押下=1、押下=0、スイッチ線取り外し=0」でした。このため、GP26=LOWを押下または信号異常として下降停止に使います。ソフトウェアでは押下と断線を区別できません。
この極性は今回の実配線で測った値に合わせています。別の配線・インターフェース基板では、移動キーを使わずに必ず両状態を確認してください。GP26へ24Vを接続しないでください。

## モニターの起動

書き込み後は通常のアーム用launchを終了したまま、次を実行します。

```bash
cd ~/hibikino_toms_ws
python3 module/pico_programs/z_axis_motor/z_axis_circuit_check/monitor.py
```

USBシリアル番号からポートを選ぶため、ttyACMの番号変更に対応します。
通信は115200bps。単一キーを入力します。Enterは不要です。モニター終了は `Ctrl+]`。

| キー | 動作 |
|---|---|
| `p` | 入力・出力・停止理由を表示（自動表示も毎250ms） |
| `?` | 操作案内 |
| `u` | CCW側へ200ステップだけ動かす（上昇想定、NCが開いていても使用可） |
| `d` | CW側へ200ステップだけ動かす（下降想定、GP26=LOWなら拒否） |
| `t` | CW側へ動かし、GP26=LOWになった最初のサンプルで停止。最大2000ステップ／4秒 |
| `x` / Space / Esc | ステップ出力を止め、通電保持 |
| `e` | 通電保持を有効にする。移動は開始しない |
| 大文字 `F` | 明示的に通電解除。Z軸を支えた状態でのみ使用 |

起動時は `POWER=ON MOVE=STOP REASON=boot_hold_no_motion` になります。
自動移動・自動原点復帰・停止時の自動通電解除はありません。
USBモニター切断で移動を中断します。ホスト停止時に切断を検出できなくても、ステップ数と4秒の上限で終了します。
上昇中は原点スイッチから離れるため、GP26=LOWによる上昇禁止を行いません。
上端用スイッチや絶対位置管理はありません。上昇試験の空間は目視で確認してください。

## 確認の順序

1. 移動キーを押さず、手でスイッチを押す・離す。今回の実測に合わせ、`GP26=1 LIMIT=CLOSED/NC` → `GP26=0 LIMIT=OPEN/TRIPPED` → `GP26=1` になることを確認。
2. スイッチ線を外した時も `GP26=0 LIMIT=OPEN/TRIPPED` になることを確認。外しても1のままなら断線検出になっていないため、下降試験はしない。
3. 移動余裕を確保して `u` を1回入力し、上昇方向かを確認。想定と反対なら `x` で止め、方向を修正してから続ける。
4. GP26=1の未押下状態で `d` を1回入力し、下降方向と200ステップで止まることを確認。
5. `t`を使う場合は、動作を直ちに止められる人がスイッチを操作し、GP26が0になった時に`REASON=limit_active_stop`で停止することを確認。
6. GP26=0のとき`d`を入力すると`down_blocked_limit_active`になり、`u`で原点から離れる方向へ動けることを確認。

設定は `.ino` 先頭の `TEST_RPM=120`、`JOG_STEPS=200`、`SEEK_MAX_STEPS=2000`、`MOTION_TIMEOUT_MS=4000`。
元スケッチの換算200ステップ/mmなら約1mm／10mmですが、物理距離は未校正のためステップ数を基準にしてください。
原点位置の確定や長距離の原点復帰は行いません。

## ビルドと書き込み

```bash
cd ~/hibikino_toms_ws
~/.platformio/penv/bin/platformio run -d module/pico_programs/z_axis_motor/z_axis_circuit_check
```

書き込みは、Z軸を支え、対象ポートをモニター表示のポートと一致させて行います。書き込み時の再起動では保持が途切れる可能性があります。

```bash
# /dev/ttyACM1 は実際の Z Pico のポートへ置換する。
~/.platformio/penv/bin/platformio run -d module/pico_programs/z_axis_motor/z_axis_circuit_check -t upload --upload-port /dev/ttyACM1
```

USB書き込み権限がない環境では、このコマンドはBOOTSEL移行後に失敗することがあります。
その場合は、対象Picoが `RPI-RP2` ドライブとしてマウントされたことを確認し、
`.pio/build/z_axis_circuit_check/firmware.uf2` をそのドライブへコピーしてください。今回もこの標準UF2方式で書き込みました。
ファームウェアを変更するとUSBシリアル番号やttyACM番号が変わることがあります。
`monitor.py --serial-number 番号` で対象を明示できます。

確認用ファームウェアは通常のROSの `0,0 / 1,0 / 2,0 / 3,x` プロトコルを実装しません。
**確認用の書き込み中は `ipad_demo_rev2_eetest.launch.py` 等を起動しないでください。**
通常動作へ戻す際は本番用ファームウェアの書き込みが必要です。
本番用 `z_axis_pico2.ino` の原点復帰条件は、GP26がHIGHの間だけ下降し、LOWで止まるため、今回の実測極性（未押下=HIGH、押下/断線=LOW）と一致します。今回の変更ではこの極性を定数とコメントで明示しました。なお、本番スケッチの原点探索には時間・ステップ数の上限がなく、原点検出後の退避はコメントの5mmに対して5000ステップ（既存換算では約25mm）です。これらは今回の最小変更の対象外です。

2026-11-12に、上記の極性を明示した本番 `z_axis_pico2.ino` をZ軸Pico（`E6613008E3567336`）へ書き戻しました。ビルド済みUF2をBOOTSELドライブへコピーし、USBシリアルとして再認識されたことを確認しています。書き込み後の確認ではシリアルへコマンドを送っておらず、実機の原点復帰動作は行っていません。記録は `validation/z_axis_pico2_write_20261112.json` を参照してください。

## ソフトウェア検証

`test/check.cpp` は実際のスケッチを模擬Arduino/Stepper環境で実行します。
起動時の無移動、NC開放時の下降停止・再下降拒否・上昇許可、移動量・時間上限、停止優先、入力の非蓄積、USB切断、通電操作を確認します。

```bash
g++ -std=c++17 -Wall -Wextra -Werror \
  -I module/pico_programs/z_axis_motor/z_axis_circuit_check/test/fakes \
  module/pico_programs/z_axis_motor/z_axis_circuit_check/test/check.cpp \
  -o /tmp/z_axis_circuit_check_test
/tmp/z_axis_circuit_check_test
```

模擬検証は実配線の方向、ドライバーの入力波形仕様、移動距離、スイッチの実入力を保証しません。実機での確認結果は `validation/` に保存します。

2026-11-12、ユーザー実測（未押下GP26=1、押下GP26=0、スイッチ線取り外しGP26=0）に合わせてLOWを停止条件とするUF2をビルドし、Z軸用Pico（シリアル `E6613008E3567336`、USB物理位置 `1-4.1.4.1`）へ書き込みました。UF2は `RPI-RP2` BOOTSELドライブにコピーする方式を使用しました。

書き込み後にシリアル `/dev/ttyACM1` から状態照会だけを行い、`GP26=1 LIMIT=CLOSED/NC POWER=ON MOVE=STOP STEPS=0/0 PINS16_19=0000 AWO20=0 REASON=boot_hold_no_motion` を確認しました。モーター移動コマンドは送っていません。読み取り記録は `validation/active_low_telemetry_after_flash_20261112.txt`、書き込み・ビルド情報は `validation/active_low_measurement_20261112.json` にあります。

GP26=LOWはスイッチ押下または信号線異常として扱われ、下降を停止・拒否します。LOWの原因（押下と断線）はこの回路では区別できません。今回の実機確認は停止状態と未押下レベルまでです。上下方向や、スイッチ押下時に下降が止まることの機械動作確認は、支持・停止要員を用意したうえで別途実施してください。
