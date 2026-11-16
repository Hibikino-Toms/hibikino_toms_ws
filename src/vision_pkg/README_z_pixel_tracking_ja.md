# D405の縦画素によるZ補正

`vision_xy_tracking.launch.py` は **`config/vision_xy_tracking.yaml`** を使います。以下のZ設定は統合ファイル内の `z_tracking`、目標画素は `target` で調整してください。旧ロボット・vision設定ファイルは別launch用として残しており、このlaunchへは自動反映されません。

2026-11-17更新。画像の縦位置だけでZ補正を判断します。以前の「深度から換算した上下ずれ10mm」は、この追従経路では使いません。

## 判定と動作

画像高をH、選択したトマト中心をv、目標画素をv*として、`error_px = v - v*` を使用します。

- `|error_px| >= H × 0.10` で補正開始。
- XY関節を実測角で保持し、保持後の0.5秒の位置履歴から停止条件を3周期続けて確認してからZ移動。
- 深度から移動量を計算せず、最大5mmの移動と新しい画像の確認を繰り返す。
- 移動中でも `|error_px| <= H × 0.05` に入ったら停止要求を出す。
- Zの停止通知と新しい画像を確認し、内側の範囲で0.3秒保持したらXY追従を再開。
- 補正開始後は外側の境界を内側に入っても続行し、内側の境界まで合わせる。補正完了後は、再び外側を超えるまでZを動かさない。

640×480の場合、目標高さから**48px以上で開始、24px以内で停止**です。目標画素・外側境界（橙）・内側境界（緑）をカメラ画面に表示します。停止要求から物理停止までの遅れがあるため、実機で速度と制動距離の確認は必要です。

Z補正中はXYの画像目標を破棄します。各5mm区間の間もXYを保持し、途中でXY追従を挟みません。目標画素が中央でも奥行き全量をZ指令に変換しません。

## YAML設定

### 目標高さ

`src/vision_pkg/config/realtime_detector.yaml`:

```yaml
target:
  target_pixel: null
  target_pixel_offset_x_px: 50.0  # 既存の左右設定
  target_pixel_offset_y_px: 0.0   # 今回追加。+で下、-で上
```

`target_pixel: null` なら、目標高さは `(画像高-1)/2 + target_pixel_offset_y_px` です。480pxでは239.5pxが中央です。例えば `-30.0` は中央より30px上、`20.0` は中央より20px下です。中心の定義はカメラ内部パラメータの主点とは別です。`target_pixel: [u,v]` を指定した場合は、そのvにオフセットを加えます。最終目標が画像外なら起動時に拒否します。

### 開始・停止幅と移動制限

`src/arm_controller_pkg/config/xy_robot_config.yaml`:

```yaml
z_tracking:
  trigger_ratio: 0.10
  stop_ratio: 0.05
  step_m: 0.005
  max_cycle_travel_m: 0.100
  speed_m_s: 0.010
  move_timeout_sec: 30.0
```

| 設定 | 意味 |
|---|---|
| `trigger_ratio` | 画像全体の高さに対する補正開始幅。0.10=1/10 |
| `stop_ratio` | 補正を完了する幅。0.05=1/20。開始幅より小さくする |
| `step_m` | 一度に送るZ移動の上限。既定5mm。距離の推定値ではない |
| `max_cycle_travel_m` | 1回の補正サイクルの累積指令移動量上限。既定100mm |
| `speed_m_s` | Z速度。既定10mm/s、ファームウェア上限20mm/s |
| `move_timeout_sec` | 複数区間・画像待ちを含む補正全体の時間上限。既定30秒 |
| `min_position_m` / `max_position_m` | 原点からのパルス位置のソフト制限。既定5～450mm |
| `observation_timeout_sec` | 縦画素観測の許容経過時間。既定0.30秒 |
| `xy_stop_speed_rad_s` / `xy_stop_samples` | Z開始前のXY実測停止確認。窓全体の角度差÷経過時間が0.02rad/s以下、かつ位置幅・保持誤差の条件を3周期続けて満たす |
| `xy_stop_window_sec` | 保持後に計測する停止確認の時間窓。既定0.50秒 |
| `xy_stop_position_tolerance_rad` | 窓内の最大角−最小角、保持目標からの実測誤差、の両方の上限。既定0.0035rad（約0.20度） |
| `xy_stop_max_sample_gap_sec` | 関節サンプルの許容最大間隔。既定0.25秒。途切れたら窓と連続成立数をリセット |
| `xy_stop_timeout_sec` | XY停止確認の上限。既定5秒 |
| `settle_sec` | 内側の範囲に入ってZが停止した後の保持時間。既定0.30秒 |
| `communication_timeout_sec` | Z状態通信のタイムアウト。既定0.60秒 |
| `serial_number` / `baudrate` | Z用Picoの選択。E6613008E3567336 / 115200 |
| `home_timeout_sec` | 原点復帰時間上限。既定120秒 |
| `sim_initial_position_m` / `sim_homed` | 模擬Zの開始位置225mm／原点確定true |

設定を変更したらlaunchを再起動してください。Z位置・移動量・速度の単位はmと秒、画像観測は明示的にpxです。旧 `trigger_error_m` / `max_correction_m` は現在のZ画素制御では使いません。

Z方向は既存の `camera_to_end_effector` と撮影時yawから決めます。標準取付けでは、画面で対象が上ならZ上昇、下ならZ下降です。取り付け並進を相対移動へ加算しません。上下画素に対するZの効果が小さい取付けは拒否します。既存の取付行列・軸符号は今回変更していません。

## 起動・停止

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
```

模擬カメラ・模擬アーム:

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=sim synthetic_camera:=true harvest_cycle_enabled:=false \
  z_tracking_enabled:=true show_window:=true
```

実機（XY初期姿勢への移動と追従を伴います）:

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured synthetic_camera:=false \
  harvest_cycle_enabled:=false z_tracking_enabled:=true show_window:=true
```

**前回書き込んだ `Z_TRACKING_V1` ファームウェアをそのまま使用できます。今回の変更でPicoの再書き込みは不要です。** 無指定の `z_tracking_enabled:=false` ではZポートを開きません。旧アームサービス／Zモニターとは同時に起動しないでください。

**`startup_mode:=configured` かつ `z_tracking_enabled:=true` では起動ごとに自動原点復帰します。** 原点確定済みでも一度実行し、通信・XY停止確認 → Z原点復帰・離脱・整定 → XY初期姿勢移動・追従、の順に進みます。異常時は次工程へ進まず保持し、自動再試行しません。

`startup_mode:=current` は自動原点復帰しません。Pico再起動後の `NEEDS_HOME` ではXYを保持して待つため、スイッチ極性と移動余裕を確認し、別端末で以下を要求します。要求受理と原点復帰完了は別です。

```bash
source ~/hibikino_toms_ws/install/setup.bash
ros2 service call /arm_xy/z/home std_srvs/srv/Trigger '{}'
```

原点復帰はGP26=LOW（押下または信号断）で下降停止し、5mm離脱します。最初からLOWなら最大2mmだけ離脱を試み、解除されなければ異常停止します。`HOMING → SETTLING → IDLE`、続いて `/arm_xy/ready=true` を確認してください。断線と押下は同じLOWで区別できません。

停止はCtrl-C、または次のサービスです。通電保持は維持します。明示停止や異常後は原因を解消してtrackerを再起動します。

```bash
ros2 service call /arm_xy/z/stop std_srvs/srv/Trigger '{}'
```

## 深度が取れない場合と異常時

**Z補正は2D検出だけで実行します。** 対象内深度の欠損・外れ値・深度フレーム欠損を理由としてZ補正を中断しません。XYも、既定の `target.image_approach.enabled: true` では遠距離の左右合わせ・接近に深度を必要としません。Z補正完了後はXYの画像接近を再開します。近距離の深度を一度得た後は、欠損時に保持し、画像だけの前進には戻しません。詳細は [画像接近の手順書](README_image_approach_ja.md) を参照してください。画像接近を無効にした場合は、従来どおりXYに有効深度が必要です。

対象消失、識別の曖昧さ、古い画像、姿勢時刻ずれ、カメラ異常は全軸保持を要求します。Z補正中ならZも停止して異常をラッチします。対象IDが変わった場合もZを止め、別の対象へ乗り換えません。Z通信異常、位置範囲外、累積移動上限・時間上限でも保持し、自動再試行やトルクOFFは行いません。表示画素だけで物理的な到達距離や衝突安全性は保証できません。

収穫保持／復帰中はZ補正を行わず、初期姿勢への復帰でZを自動的に初期高さへ戻しません。

## 診断・ROSBAG

### XYが動かない／`xy_failed_to_stop` の場合

以前の `Vision hold requested: reason=invalid_mask_depth scope=xy_only` は、深度必須のXY制御で有効深度を得られず保持したことを示します。現在の画像接近が有効なら、遠距離の深度欠損だけではXY接近を止めません。近距離への切替確認中や切替後の欠損では `confirming_near_depth`／`near_depth_lost_hold` で保持します。Zの画素制御は継続できます。

`STOPPING_XY → xy_failed_to_stop` は、5秒以内にXY停止確認が成立しなかったことを示します。`target_m=None` ならZ移動指令もまだ出ていません。ログだけでは実際の振動・移動と読取り値の細かな変化を区別できません。

q3の既存換算は360度/4095countで、100ms間の2countの変動は約0.0307rad/sです。以前の100ms差分だけによる判定ではこれが0.02rad/sを超えました。現在は、保持開始後0.5秒の窓での速度に加えて、窓内の位置変動幅と保持目標からの誤差がそれぞれ0.0035rad以内であることを確認します。0.25秒を超えるサンプル欠落では確認をやり直し、5秒の上限は維持します。位置の実測変化が大きいままZを開始する判定にはしません。

`Z waiting for XY stop` を1秒ごと、タイムアウト時には `XY stop check` を表示します。`/arm_xy/z/state` と `/arm_xy/diagnostics` の `z` にも以下が残ります。

- `xy_stop.blocking_joints`: 判定を妨げている関節番号（1=q1、2=q2、3=q3）。
- `xy_stop.window_velocity_rad_s`: 窓の端点間で求めた関節速度。
- `xy_stop.position_span_rad`: 窓内の最大角−最小角。
- `xy_stop.hold_error_rad`: 保持開始時の目標角からの誤差。
- `joint_velocity_rad_s`: 直近2サンプルによる速度。量子化の影響を見る診断値で、単独では停止判定に使用しません。
- `stopped_samples` / `required_stopped_samples`: 連続成立数と必要数。

実機の揺れや保持誤差が原因なら、診断値で関節を特定してから機構・モーター保持を確認してください。この変更で実機が静止したことを確認したわけではありません。

| トピック | 内容 |
|---|---|
| `/arm_xy/z/pixel_observation` (`String` JSON) | `capture_stamp`, `frame_id`, `error_px`, `image_height`, `direction_per_error`, `track_id`。深度値なし、最新1件 |
| `/arm_xy/z/state` (`String` JSON) | `control_mode=pixel`, `phase`, `reason`, `error_px`, `trigger_px`, `stop_px`, `xy_inhibited`, `position_m`, `target_m`, `cycle_travel_m` |
| `/vision/servo_diagnostics` | `vertical_error_px`, `z_trigger_px`, `z_stop_px`, `pixel_error`, `z_depth_required=false`、深度値はXY診断用 |
| `/arm_xy/xy_hold` (`Empty`) | XYだけの保持。深度無効時にZの画素制御を止めないための要求 |
| `/arm_xy/hold` (`Empty`) | 全軸保持要求。検出消失・カメラ異常・明示停止等 |
| `/arm_xy/actual` | XY/yawは関節実測FK、zは原点からのパルス位置推定 |

```bash
ros2 bag record -o ~/rosbags/z_pixel_$(date +%Y%m%d_%H%M%S) \
  /rosout /vision/servo_diagnostics /arm_xy/diagnostics \
  /arm_xy/z/state /arm_xy/z/pixel_observation /arm_xy/hold /arm_xy/xy_hold \
  /arm_xy/actual /arm_xy/goal /arm_xy/joints /arm_xy/ready
```

Zには独立した位置エンコーダがなく、200step/mmの送出パルス数からの位置推定です。脱調・実距離・荷重時の保持は実機での確認が必要です。原点未確定時の位置0は実位置を示しません。

今回実施した確認はPython構文確認と関連パッケージのビルドです。実機移動・Pico書き換えは行っていません。以前の [10mm方式の模擬検証記録](../arm_controller_pkg/validation/z_tracking_20261117/summary.json) と [Pico書き込み記録](../arm_controller_pkg/validation/z_tracking_20261117/flash_and_status.json) は履歴であり、今回の画素方式の実測性能を示すものではありません。
