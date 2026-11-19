# q1/q2 RMD CAN移行（q3 Dynamixel維持）

現在の`xy_robot_config.yaml`は、2026-11-16にユーザーが測定した組付け後の＋Y直線姿勢を基準にしています。根元・q2・q3軸が＋Y上で一直線のとき、RMD X8 raw=−110°、X6 raw=170°、既存q3表示=0°です。固定横オフセットは撤去済みのため`Link2: 0.0`とし、モデルの関節角を`[90°, 0°, 0°]`に対応付けます。後半の2026-10-29試験は、旧機構・旧校正値での履歴です。

## 構成

- `arm_xy_tracker`の上位側は、従来どおり`q1/q2/q3`のradを扱います。FK/IK、XY追従、関節速度・加速度制限、可動範囲の処理は関節座標で行います。
- q1: RMD-X8-P20-120、CAN ID 0、Uno上のMCP2515から制御。
- q2: RMD-X6-P20-60、CAN ID 1、Uno上のMCP2515から制御。
- q3: 従来のDynamixel ID 5のみ。`q3 = motor_angle - 180° + angle_trim_deg`で関節角へ変換します。補正既定値は0°です。旧q1/q2のDynamixel ID 1～4はこのバックエンドから操作しません。
- Arduino UnoとのUSBシリアルはUSBシリアル番号`24236323730351504241`で特定します。デバイス名`/dev/ttyACM*`は固定しません。
- Unoは起動時にRMD両軸へ`0x81`の保持停止を送り、ホストから設定・事前確認・ARM要求を受けるまで位置指令を実行しません。ARM後は150msごとのheartbeatを要求し、500ms途絶えると両軸を停止・disarmします。`0x80`による出力遮断は送りません。

ファームウェアは`module/arduino_rmd_arm_bridge/`です。資料のMCP2515 8MHz、1Mbps、標準CAN、X8 ID 0 / X6 ID 1、`0x92`多回転位置、`0xA4`絶対位置、`0x81`停止を使います。位置は0.01度単位の符号付き多回転角です。速度上限は設定値で送り、ファームウェア側でも60dpsを上限にします。

## 関節限界と校正

`config/xy_robot_config.yaml`の`joint_limits_deg`は以前の設定から維持しています。

| 関節 | ソフトウェア範囲 |
|---|---:|
| q1 | -10～180° |
| q2 | -30～175° |
| q3 | -165～135° |

これは以前のモーター角制限を旧オフセットで関節空間へ換算した値です。変更後の機構の機械的な可動範囲や衝突安全を測定した値ではありません。

RMDの絶対出力角だけでは、アーム関節の角度ゼロと正方向は分かりません。現在は組付け後の＋Y直線姿勢を基準とし、正方向は以前に確認したモーター指令の正方向を継続しています。取付け後の物理的な正方向は小刻みな操作で再確認してください。取付けをさらに変えた場合は`calibration_valid: false`に戻し、再校正してください。

動作を許可する校正値は、組み立てた機構でq軸角を別の確かな方法で測り、同時にUnoから読んだRMD出力角と対にして決めます。既知の関節角からRMD角への関係を

```text
q[度] = reference_joint_deg
        + direction * (RMD生値[cdeg] - reference_motor_cdeg) / 100
        + angle_trim_deg
RMD目標[cdeg] = reference_motor_cdeg
                + direction * (q目標[度] - reference_joint_deg - angle_trim_deg) * 100
```

とし、`direction`は実測で`+1`または`-1`を設定します。`reference_motor_cdeg`は起動ログの`0x92`生値（centidegree、度の100倍）です。現在の設定は次のとおりです。

```yaml
can_mixed_backend:
  calibration_valid: true
  q1:
    direction: 1
    reference_joint_deg: 90.0
    reference_motor_cdeg: -11000
    angle_trim_deg: 0.0
  q2:
    direction: 1
    reference_joint_deg: 0.0
    reference_motor_cdeg: 17000
    angle_trim_deg: 0.0
  q3:
    angle_trim_deg: 0.0
```

### 角度の微調整

`src/arm_controller_pkg/config/xy_robot_config.yaml`の`can_mixed_backend.q1/q2/q3.angle_trim_deg`を変更します。単位は度で、固定したモーター位置に対して表示関節角へ足す量です。たとえばq1の表示を＋0.5°補正するなら、q1の`angle_trim_deg: 0.5`にします。同じ関節目標に対する実際のモーター目標は、読み取りの逆変換として補正されます。RMDの生値・Dynamixel tick自体は書き換えません。関節制限とArduinoへ渡すRMD生値制限にも校正を反映します。±180°への自動折り返しは行いません。

1. アーム制御ツール・ノードを終了してからYAMLを編集します。運転中の設定再読込はありません。
2. ソースのYAMLを明示して読み取り専用で確認します。

   ```bash
   source ~/hibikino_toms_ws/install/setup.bash
   ros2 run arm_controller_pkg can_joint_range_tool \
     --config-file ~/hibikino_toms_ws/src/arm_controller_pkg/config/xy_robot_config.yaml
   ```

3. ＋Y直線姿勢で約`q1=90°、q2=0°、q3=0°`と表示されることを確認します。q1は＋X基準の絶対角、q2/q3は前のリンクに対する相対角です。基準姿勢で全関節を0°表示にはしません。Dynamixelの分解能によりq3は約0.088°刻みになります。
4. 小刻みな移動は上のコマンドに`--enable-motion --step-deg 0.25 --speed-dps 2`を付けます。開始位置は現在の測定角で、YAML変更だけで基準姿勢へ移動する機能はありません。

通常のlaunchでinstall側設定を使う前は`colcon build --symlink-install --packages-select arm_controller_pkg`を実行し、`source install/setup.bash`を読み直してください。補正値はCAN混成バックエンドと範囲確認ツールで共通に使い、従来の5台Dynamixel専用経路には適用しません。`startup.home_joints_deg/demo_joints_deg`は校正基準とは別の移動目標です。設定済み初期化経路は組付け後の機構で確認が必要です。

固定横オフセット0mmのモデルでは、基準姿勢の手先FKは`X=0m、Y=0.620m、yaw=π/2rad`です。根元→q3軸は0.545mです。これらは設定された他のリンク寸法（270/275/75mm）による計算値であり、今回ほかの寸法を実測し直したものではありません。旧オフセットを撤去したため、同じ関節角でも以前とはFK位置が変わります。

2026-11-16のソフトウェア検証では、提示された生値から`[90°,0°,0°]`への変換と逆変換、正負の補正・方向、RMD生値制限、q3の読み取りと逆指令、オフセット0mmでのFK・ヤコビアン・IKを確認しました。初期姿勢から半径50mmの円の事前IK確認も両方向で通過しています。新校正値での実機移動は実行していません。

旧校正値での試験では各軸へ+2°（2dps）を指令し、0x92角が増加すること、元の目標へ戻ることを確認しました。q1は−121.15°から約−119.22°へ、復帰後−121.05°（基準差+0.10°）。q2は−105.46°から約−103.50°へ、復帰後−105.45°（基準差+0.01°）。この確認はリンク未装着でのモーター方向試験です。リンク組付後の実関節正方向や機構限界は未確認です。

## ビルドと起動

### q3の起動時保持確認（2026-11-17修正）

`DXL q3 startup hold readback mismatch` は、トルクON前に設定した現在位置の保持目標を確認できず、起動を中止したことを示します。ログの `initial=1264, goals=[1265,...], present_now=1264` は1カウント差です。以前は設定で1カウントを許容していても、追加確認で現在位置と目標の完全一致を要求していました。

現在は `dxl_params.startup_hold_tolerance_ticks: 1` の範囲内（約0.088度）で、目標の読戻しと現在位置の差、および両者と起動時位置の差を確認します。トルク状態が変わらず、実測位置が可動範囲内であることも要求し、2回連続で成立した場合だけトルクONへ進みます。`0`なら完全一致です。目標を実測変動に追従させて書き直す処理はありません。

`dxl_params.startup_readback_timeout_ms` の既定値・設定値は250msです。許容差を超える変動や読戻し不一致、通信異常は起動失敗とし、トルクONしません。通常のvision launchでは `src/vision_pkg/config/vision_xy_tracking.yaml` を、円デモ等では `config/xy_robot_config.yaml` を参照します。今回の修正後の実機起動は未確認です。

## 関節角の読み取りと一軸ずつの範囲確認

`can_joint_range_tool`はq1/q2のRMD出力角と校正換算した関節角、q3 Dynamixel ID 5の関節角を表示します。通常起動は読み取り専用です。読み取り専用でもArduinoのUSBシリアルを開くためUnoが再起動しますが、RMDはファームウェアの起動時停止状態のままで、ARM・移動指令やDynamixelのトルクONを要求しません。先にアームを操作する他ノードやシリアルモニターを終了してください。

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run arm_controller_pkg can_joint_range_tool
```

表示を更新するにはEnter、終了は`q`です。q1/q2の関節角はYAMLの校正値から計算した値です。現在の校正は上記＋Y直線姿勢を基準としています。生値と表示関節角・各軸の補正値を確認してください。`calibration_valid: false`でも読み取り専用なら生のモーター値と校正推定値を確認できますが、推定には未校正の表示が付きます。

一軸ずつ動かして可動範囲を調べる場合は、アームを支持し、作業範囲を空け、他のアーム制御ノードを停止してから、明示的に動作モードを指定します。

```bash
ros2 run arm_controller_pkg can_joint_range_tool --enable-motion --step-deg 0.5 --speed-dps 2
```

確認プロンプトに`MOVE`と入力すると、RMD q1/q2をARMし、q3のDynamixelトルクを有効にします。`j q1 +`、`j q2 -`、`j q3 +`のように一回ずつ小さく動かし、角度は各操作後に読み直します。`step 0.25`で刻みを小さくできます。`r`で角度更新、`limits`で設定ソフトウェア範囲を表示、`q`またはCtrl-Cで終了します。各指令では選択軸以外にその時点の測定角を目標として送ります。q1/q2の速度は`--speed-dps`で制限されます。q3の速度は既存のDynamixelプロファイル設定に従い、この引数では変更しません。

このツールは`joint_limits_deg`を越える目標を拒否します。これらは現在のソフトウェア制限で、組付け後の機械限界を示す測定値ではありません。機械端へ押し当てず、リンク・配線・周辺部品との干渉が起きる前に小刻みな指令を止め、表示角を記録してください。ソフトウェア範囲外を試す機能は設けていません。実角に合わせて校正した後、測定した運転範囲を`joint_limits_deg`へ反映します。

終了時、CAN軸には既存ファームウェアの`STOP`（保持停止）を要求し、Dynamixelのトルクは自動OFFにしません。通信断で停止指令が届かない場合に備え、独立した電源遮断手段と機械的支持を用意してください。

### U2D2が見つからない場合

ツールはArduinoを開く前に両アダプターのシリアル番号・USB接続先を表示します。どちらかが不在なら、Unoを再起動する前に終了します。起動後に失敗した場合も、その時点のUSB機器一覧を表示します。USBの抜け直し後に`ttyUSB0`などの番号が変わっても、シリアル番号が一致すれば検出します。切断原因を調べる際は別端末で以下を実行します。

```bash
journalctl -k -f
```

2026-11-16の調査では、設定したU2D2シリアル`FTAK87XF`は実機と一致しました。12:31前後のカーネルログに複数ハブ・USB機器の`err = -71`と切断、12:33:13と12:36:40にはU2D2自体の切断が記録されています。調査時のU2D2接続は`1-4.1.4.2`で、外部ハブを3段経由していました。この事実だけではハブ、ケーブル、給電、接触、電気的ノイズのどれかを特定できません。直接接続が難しいJetson環境では、まず経由するハブを減らして比較します。再発する場合はUSBケーブル交換やハブ給電の確認を一つずつ行い、切断ログと比較してください。

同日の調査試験ではArduino接続だけではU2D2は消えず、U2D2単体のDynamixel現在位置読取りは5/5成功しました。元の読み取り専用ツール起動3回でもUSB切断は再現せず、全てRMD X8 ID0の`0x9A`状態読取りが101～102msで`CAN_TIMEOUT`になりました（受信CANフレーム0、MCP2515レジスタには非ゼロの応答あり）。その後、ユーザーがCAN主電源を投入すると全軸読取りが復旧しました。この試験時のCAN無応答は主電源未投入に対応しています。

ユーザーがU2D2を近いUSBポートへ差し替え、接続先が`1-4.2`になった後は、U2D2位置読取り100/100回に成功しました。さらにCAN主電源投入後のツール起動は5/5回成功し、全軸の状態を計15回読み取れました。この試験中にU2D2切断は発生していません。元の経路でも最初の再現試験では切断しなかったため、経路変更だけで恒久解消したとは断定しません。診断中にARM、目標位置、トルクONの指令は送っていません。記録は`validation/u2d2_disconnect_20261116/`です。

この時点の旧校正による関節表示はq1約10.66°、q2約278.31°、q3約−7.96°でした。q2が設定ソフトウェア範囲−30～175°を外れていたため、当時の校正設定では移動モードを起動できませんでした。この後、ユーザーから提供された＋Y直線姿勢の測定に基づき、冒頭の新校正へ更新しています。

Arduino用PlatformIO環境（既存venv）でビルド・書込み:

```bash
cd /home/ylab/hibikino_toms_ws
/home/ylab/.platformio/penv/bin/pio run -d module/arduino_rmd_arm_bridge
/home/ylab/.platformio/penv/bin/pio run -d module/arduino_rmd_arm_bridge -t upload \
  --upload-port /dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_24236323730351504241-if00
```

書込み後の読み取り確認は115200bpsで`PING`、`READ,1`を送り、`READY,RMD_ARM_V1,STOPPED`、`PONG,RMD_ARM_V1`、`S,...`応答を確認します。`STOP`以外の指令を手動送信しないでください。起動状態で自動回転する旧テストスケッチはこのファームウェアに置き換わっています。

ROSパッケージを再ビルドします。

```bash
cd /home/ylab/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
```

模擬環境は従来どおりです。

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py backend:=sim synthetic_camera:=true
```

実機で追従ノードだけを現在位置から起動するコマンドは次のとおりです。これは今回検証した起動方法です。q1/q2をホーム姿勢へ動かしません。

```bash
ros2 run arm_controller_pkg arm_xy_tracker --ros-args \
  --params-file install/arm_controller_pkg/share/arm_controller_pkg/config/xy_tracking_params.yaml \
  -p config_file:=/home/ylab/hibikino_toms_ws/install/arm_controller_pkg/share/arm_controller_pkg/config/xy_robot_config.yaml \
  -p backend:=can_mixed -p startup_mode:=current
```

カメラ追従を起動するのはリンク・カメラ・関節座標の対応を確認してからにしてください。その際は`ros2 launch vision_pkg vision_xy_tracking.launch.py backend:=can_mixed startup_mode:=current synthetic_camera:=false`を使います。`startup_mode:=configured`は`home_joints_deg`と`demo_joints_deg`へアームを動かします。自動収穫側から使う場合も`vision_auto_harvest.launch.py backend:=can_mixed`を選べます。どちらもq1/q2 CANとq3 Dynamixelを同時に使用し、旧`arm_controller.py`の経路は対象外です。

`backend:=can_mixed`の動作許可条件:

1. Unoの識別・ファームウェア応答が正常。
2. RMD両軸のエラーが0、電圧が20～55V、起動速度が±10dps以内。
3. q1/q2の校正値が有効で、読み値を関節座標へ変換した結果が設定関節範囲内。
4. 導出したRMD raw角度範囲内に現在位置・目標値が入る。
5. q3のDynamixel ID 5が既存の位置制御モード、範囲、保持確認を通過。

実行中、10Hzのtrackerタイマーだけが位置・姿勢を読み、IKと3関節指令を計算します。q3指令をDynamixelへ送り、q1/q2を一つのUnoシリアル指令で同じCAN制御周期に送ります。Arduino heartbeatは別スレッドですが、シリアル要求・応答には同じロックを使用します。タイマーのシリアル読取時間は実機で計測してください。

## 停止と検証範囲

通常停止はlaunch端末で`Ctrl-C`です。Unoへ`STOP`を送り、RMDは`0x81`保持停止にします。Dynamixelはq3のトルクを自動OFFにしません。ホストが突然停止した場合はUnoの500msウォッチドッグがRMD両軸を停止します。通信途絶で実際に停止指令が届く保証はないため、機械的支持と独立した電源遮断手段を用意してください。

UnoファームウェアのPlatformIOビルドと書込み、シリアル応答、RMDの読取値・2°低速指令・復帰を確認しました。ROSの`backend:=can_mixed startup_mode:=current`は実機で起動し、q1≈0.09°、q2≈0.01°、q3≈−8.05°を読み、`/arm_xy/ready=true`になりました。trackerの処理時間は約18～32ms、平均周期は約100.00ms（10Hz）、計測最大周期は約101.43msでした。この計測中は画像ノード・追従目標なしです。Ctrl-C後にUnoを再読取し、armed=0、両RMD速度0dps、エラー0を確認しました。q3のトルクは既存仕様どおり自動OFFにしていません。リンク組付後の関節方向、機械限界、負荷下性能、画像追従の実動作は未確認です。

## 2026-10-29 円軌道の実機試験とCAN診断

ユーザー確認のもと、リンク未装着の固定試験環境で次の条件を実行しました。yaw固定と現在の関節制限を保てる円として、半径50mmを使っています。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch arm_controller_pkg xy_circle_demo.launch.py \
  backend:=can_mixed startup_mode:=configured center_mode:=current_start \
  radius:=0.05 period:=60.0 revolutions:=1
```

第1・第2起動ウェイポイント（`[5,170,-75]°`、`[5,160,-65]°`）を経て円軌道の事前IK確認を通過し、円デモは一周完了を出しました。記録は`validation/can_circle_20261029/real_circle_retry_fw/`にあります。

- 目標601件、追従診断605件。実測XY誤差は最大3.27mm、RMS 2.52mm。
- 指令yaw誤差最大は数値誤差相当、実測yaw誤差最大0.0130rad（約0.74°）。
- 関節角の実測範囲はq1が4.45～41.22°、q2が147.10～168.88°、q3が−100.53～−64.22°。モーターが実際に動き、円軌道を追ったことを確認しました。
- 制御周期平均100.000ms、最大101.815ms、周期処理最大64.1ms。処理時間が100msを超えた回数は0回でした。
- デモ完了の約1.2秒後、次のRMD X8 ID0状態読取りが100ms以内に応答せず、trackerが`fault_latched`になりました。失敗時は受信CAN応答0件で、MCP2515の状態・設定レジスタ読取りも全て0でした。直前のモーター状態は両軸エラー0、電圧47.8Vでした。円の追従結果は記録できましたが、運転中の通信安定性は未合格です。

MCP2515初期化については、前回の起動で全レジスタが0となり`stage=1`で失敗しました。配線差し直し後の5回起動・150回読取りは成功しましたが、ROS起動では再び同じ初期化失敗が出ました。そこでUnoファームウェアを変更し、モーターをarmする前にMCP2515初期化を最大10回（150ms間隔）試行して、成功したときだけ`READY`を出すようにしました。PlatformIO書込みと検証に成功し、書込み後の10回起動・300回読取りは全て成功しました。さらに実機走行後の再起動では、最初の2回は全レジスタ0、3回目で初期化に成功したログを確認しました。

MCP2515初期化失敗と、円軌道後の全レジスタ0は、MCP2515のSPI応答が断続した証拠です。起動再試行は一時的な初期化失敗を回復できますが、走行中のSPI応答断は解消していません。特定の1本の配線、MCP2515基板の電源低下、接触振動のどれかまでは特定できていません。

別の`hold_default_spi.jsonl`ではID0の`0x9A`応答が22msでタイムアウトした際、MCP2515のCAN状態・エラーレジスタは読めていて、エラーカウンタも0でした。この記録はMCP2515自体がSPIに応答している一方、モーターからCAN応答が届かなかったケースを示します。終端抵抗、CAN_H/CAN_L接触、共通基準GND、モーター側応答遅延などが候補ですが、保存ログだけでは特定できません。したがってCANタイムアウトをSPI配線だけの問題とは断定できません。

次の実機走行前に、MCP2515の5V/GND、特にUno D12(MISO)–MCP2515 SO、D10(CS)、共通GNDを抜けにくく固定し、モーター動作中にも基板VCCが約5Vを保つか測定してください。またCAN_H/CAN_Lの接続、コントローラー端とバス末端の120Ω終端、共通基準GNDを確認してください。通信異常時はtrackerがfaultをラッチし、再起動まで指令を再開しません。

円軌道後の読取り専用確認では、起動再試行10回すべてでMCP2515レジスタが0のままとなり、`READY`が出ませんでした（`validation/can_circle_20261029/after_circle_stopped.jsonl`）。このため、円軌道完了後にモーター停止指令が実際にCAN送信できたか、停止保持中かを最後の読取りで再確認できていません。失敗直前の最後の有効状態では両軸速度0dps・エラー0でした。次の実機走行前に、SPI配線とMCP2515電源の接続を固定・測定してから再起動確認を行ってください。

### 配線差し直し後の再確認

2026-10-29にユーザーが配線を差し直した後、読取り専用診断を10回再起動して行いました。10回すべてで`stage=1`のMCP2515 resetに失敗し、`READY`は一度も出ず、CAN読取りは0回でした（`validation/can_circle_20261029/reseat_recheck.jsonl`）。この状態ではモータ指令を送っていません。

追加の`SPI_PINS`診断では、Uno側SPIレジスタは`SPCR=0x51`、`DDRB=0x2C`でマスター出力に設定されていました。MISO（PB4）の入力プルアップを有効にするとPB4はHIGHのまま、MCP2515レジスタは全て`0xFF`でした（`validation/can_circle_20261029/spi_pin_recheck.jsonl`）。これはMCP2515からのMISO応答が届いていない状態を示します。MISO線の断線・接触、MCP2515基板の電源またはRESET状態、基板故障のいずれかを示唆しますが、この診断だけでは部品単位の原因までは特定できません。CAN_H/CAN_LやROSの軌道設定より手前のSPI初期化で止まっているため、ここが復旧するまでは円軌道を再試行しません。

次に確認する箇所は、MCP2515基板上の`SO`からUno `D12/MISO`までの導通、基板の`VCC-GND`電圧、`RESET`がHIGHになっていること、Uno `D10/CS`・`D11/MOSI`・`D13/SCK`および共通GNDです。これらを測定して再起動診断で`READY`が確認できてから、停止状態でCAN連続読取りを行い、その後に低速の円軌道を再開してください。

その後、追加の物理配線変更なしで再確認すると、Uno起動5/5回・CAN読取り150/150回が成功しました。半径50mm、周期60秒、1周の円軌道を再実行し、`Circle demo complete`まで到達しました。ログは`validation/can_circle_20261029/reseated_circle_2/`です。

- 目標601件、追従サンプル605件。XY誤差は最大3.30mm、RMS 2.53mm、実測yaw誤差は最大0.0130rad（約0.74°）。
- 制御周期平均100.000ms（約10Hz）、最大101.319ms。計算時間最大63.9msで、100msを超えた計算は0回。目標の古さの最大値は0.458秒であり、目標更新が一時的に遅れる余地は残ります。
- 完了後の読取り診断もUno起動3/3回・CAN読取り90/90回が成功しました。RMD両軸はdisarmed、速度0dps、エラー0、電圧47.7～47.9Vでした（`validation/can_circle_20261029/post_circle_recheck_2.jsonl`）。

この再試験では起動失敗とCANタイムアウトを再現しませんでしたが、直前の同一配線状態では起動10/10回失敗していたため、通信が恒久的に安定したとはまだ判断できません。MISO応答断の原因が配線接触・電源・RESET・基板のどれか、以前のCAN応答タイムアウトの原因が何かは切り分け未完了です。今回の運転は1周の確認であり、連続長時間運転の安定性を保証しません。

事前IK確認は関節制限内で円を描けることの確認であり、リンクを組み付けた状態の衝突安全性や実機の機械限界を保証しません。今回のモーター範囲はリンク未装着の試験値です。
