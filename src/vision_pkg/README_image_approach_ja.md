# 遠距離からの画像接近と近距離の深度制御

`vision_xy_tracking.launch.py` の設定は **`config/vision_xy_tracking.yaml`** に統合しました。この手順書の `target.*` とロボットの各キーは統合ファイル内の同名キー、ROSパラメーターは `tracking.*` を調整してください。旧ファイルは別launch・単独ノード用で、自動同期しません。[設定項目一覧](README_realtime_ja.md#このlaunchの設定ファイル統合済み)

## 動作

既存の `vision_service_realtime` と `arm_xy_tracker` を使います。ノード追加やPico再書き込みは不要です。`vision_service.py` と従来のサービス収穫経路は変更していません。

```text
IMAGE_APPROACH
  トマトの横画素を合わせながら、設定速度で前進
  深度が無効でも実行。横ずれが大きいほど前進を減速
    ↓ 初めて有効な近距離深度を検出
DEPTH_CONFIRMING
  XYを保持し、近距離深度を3フレーム連続で確認（開始350mm／確認上限380mm）
    ↓ ばらつき15mm以内
DEPTH_CONTROL
  実深度と desired_distance_m の差で接近・距離維持
    ↓ 深度を失った場合
DEPTH_HOLD / DEPTH_CONFIRMING
  保持して深度を再確認。画像だけの前進へは戻さない
```

Z補正が必要なら、これまでどおりXYを止めてからZだけを動かします。Z中も近距離深度の初回検出は記録し、Zが終わった後に無測距の前進を再開しないようにします。

## 遠距離での計算

深度の代用品として仮のトマト3D位置を作りません。カメラ内部パラメータから得た光線の横角度差を左右速度へ変換し、前進速度は操作者が設定するm/sの指令です。取付け回転と撮影時の実測yawを使って、その左右・前進速度を実現可能なbase XYへ変換します。

前進中の画像の横ずれも式に含めるため、画像中央以外を目標画素にした場合にも、その目標へ合わせます。目標手先yawは既存の設定値に固定します。取付け並進を相対移動へ重複加算しません。

目標は撮影時の実測XYに、設定した時間だけ先の変位を加えて作ります。前回の仮想目標に足し続けず、古い目標を蓄積しません。物理的な関節速度・加速度・関節制限はtrackerで引き続き制限します。速度設定がそのまま実機の速度になる保証はありません。

## YAML設定

`src/vision_pkg/config/realtime_detector.yaml` の `target.image_approach`:

```yaml
image_approach:
  enabled: true
  forward_speed_m_s: 0.04
  lateral_gain_m_s_per_rad: 0.25
  forward_gate_ratio: 0.25
  max_speed_m_s: 0.06
  max_acceleration_m_s2: 0.15
  goal_horizon_sec: 0.25
  max_step_m: 0.015
  max_blind_travel_m: 0.20
  max_blind_time_sec: 15.0
  travel_deadband_m: 0.001
  depth_switch_max_m: 0.35
  depth_confirm_frames: 3
  depth_confirm_spread_m: 0.015
  depth_switch_hysteresis_m: 0.03
  depth_control_max_speed_m_s: 0.04
```

| 設定 | 意味 |
|---|---|
| `enabled` | trueで遠距離の画像接近を有効化。falseは従来の深度必須のXY追従 |
| `forward_speed_m_s` | 横誤差ゼロ時の前進指令。0.04=40mm/s |
| `lateral_gain_m_s_per_rad` | 横の光線角度差から左右速度へのゲイン。実距離の推定値ではない |
| `forward_gate_ratio` | 横誤差が画像幅のこの割合以上なら前進要求を0にする。0.25なら640px画像で160px。そこまで線形に前進速度を下げる。物理停止には制動時間が必要 |
| `max_speed_m_s` | 画像接近の合成XY速度上限。既存 `target.max_speed_m_s` も上限として適用 |
| `max_acceleration_m_s2` | 画像接近の速度変化上限。関節側の制限も別に適用 |
| `goal_horizon_sec` | 実測位置から何秒先の目標を作るか。画像接近・切替後の深度制御に適用。0.25秒、最大0.5秒。フレーム間隔だけ先の目標では関節制御の応答に対して短く、接近が遅くなる |
| `max_step_m` | 画像接近の1目標当たりの変位上限。既定15mm |
| `max_blind_travel_m` | 深度未取得の接近全体で許す実測FKの累積XY移動量。既定200mm |
| `max_blind_time_sec` | 画像接近開始からの時間上限。既定15秒。途中の保持・Z補正時間も含む |
| `travel_deadband_m` | 移動量積算で小さな関節読取りのぶれを加算し続けないための位置幅。基準点から1mm以上動いたらその変位を加算し基準点を更新 |
| `depth_switch_max_m` | この距離以下の有効深度を初めて見たら、画像だけの前進を停止して深度確認へ移る。既定0.35m。カメラ性能の保証値ではなく制御上の設定 |
| `depth_confirm_frames` | 近距離深度の連続確認数。既定3。対象消失・古い画像・無効観測・Zによる時間間隔で確認をリセット |
| `depth_confirm_spread_m` | 確認フレーム間の最大深度差。既定15mm |
| `depth_switch_hysteresis_m` | 一度350mm以下を見た後の確認上限に加える幅。既定30mmなので380mmまで確認に使用する。350mm境界付近の揺れによる確認の永久リセットを防ぐ。画像だけの前進を再開するものではない |
| `depth_control_max_speed_m_s` | 切替後の深度制御の合成XY速度上限。既定40mm/s |

近距離の最終目標は `target.desired_distance_m: 0.15`（150mm）です。0なら最初に安定取得した距離を保持します。固定距離を使うときは `desired_distance_m < image_approach.depth_switch_max_m` にしてください。

左右の目標画素は既存の `target_pixel_offset_x_px`、上下は `target_pixel_offset_y_px` です。ゲイン・速度・前進ゲートを変更しても、関節制限や取付け座標を変更するものではありません。

trackerのIK許容差は `tracking_position_tolerance_m: 0.0001`、`tracking_angle_tolerance_rad: 0.001` です。さらに `tracking_correction_resolution_m: 0.0001`、`tracking_correction_resolution_rad: 0.001` を独立設定し、`solve_tracking()` は両者の厳しい方まで計算します。IK許容差を20mmへ広げても、1mmの補正を現在角度のまま成功にしない回帰検証を実施しました。到達判定を緩める場合は `xy_robot_config.yaml` の `harvest_cycle.arrival_*` を使います。補正計算の分解能や画像制御のデッドバンドとは区別してください。

## 起動

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured synthetic_camera:=false \
  harvest_cycle_enabled:=false z_tracking_enabled:=true show_window:=true
```

上記のconfigured起動では、Zの通信・XY停止確認後にZ原点復帰を自動実行し、整定後にXY初期姿勢へ動きます。有効な2D対象があれば深度nullでもXYが動きます。`startup_mode:=current` ではZ自動原点復帰は行わず、原点未確定なら明示要求を待ちます。[Z手順](README_z_pixel_tracking_ja.md)を参照してください。

カメラ・モーターを使わずに起動するには `backend:=sim synthetic_camera:=true` に置き換えます。合成画像の既定対象深度は0.25mなので、最初から近距離の確認に入ります。遠距離の例では `simulation.initial_target_camera_m` の奥行き成分を0.35mより大きく設定します。合成画像はカメラの固定3D対象を投影しますが、今回の変更では実行測定していません。

停止はCtrl-Cです。目標消失・古い画像・カメラ異常・曖昧な対象のときは保持し、以前の前進目標を継続しません。トルクを自動OFFにしません。

## 上限・復旧・観測

画像だけではトマトまでの実距離を保証できないため、無測距での移動量と時間を制限します。上限到達は `LIMIT_HOLD` / `image_approach_distance_or_time_limit` となり、自動再試行しません。長い対象消失で別IDになった場合も `approach_target_changed` で保持します。原因を確認してlaunchを再起動するか、収穫サイクルの明示的な次のAPPROACHで新しく開始します。短い画像消失やZ補正で予算をリセットしません。

深度取得後の欠損は `near_depth_lost_hold`、再確認中は `confirming_near_depth` です。近距離を一度見た後に遠距離の画像接近へ戻す操作はありません。背景深度を対象の代わりに採用しません。マスク内の有効深度と従来のばらつき・ジャンプ検査を維持します。

カメラ画面とログに `IMAGE_APPROACH / DEPTH_CONFIRMING / DEPTH_CONTROL / DEPTH_HOLD / LIMIT_HOLD` を表示します。`/vision/servo_diagnostics` の `approach_mode`, `blind_travel_m`, `blind_elapsed_sec`, `depth_confirm_count`, `depth_control_ready`, `angular_error_rad`, `forward_speed_m_s`, `command_velocity_xy_m_s` と、既存の `/arm_xy/goal`・`actual`・`diagnostics` を比較できます。

画像接近中は実距離誤差が不明なので収穫到達扱いにはしません。深度制御に切り替わってから既存の到達判定を使います。IKが解けない場合はtrackerが保持し、関節制限や最大到達距離を迂回しません。IK保持中も画像接近の時間上限は進みます。

## 実機検証（2026-11-17追記）

Z Picoが正しい小数速度 `10.000` を拒否する現象を再現し、浮動小数の `sscanf` を `strtod` に置き換え、対象シリアル `E6613008E3567336` へ書き込みました。その後、原点復帰と画像によるZ補正の実動作を確認しています。

実機ROSBAGから350mm境界で深度確認がリセットされ続ける問題を確認し、上記ヒステリシスを追加しました。また、モーター読取り中に受信した画像観測を読取り前の時刻で評価し、到達安定時間がリセットされる問題を修正しました。`/arm_xy/diagnostics.arrival_check` で各鮮度・IK・目標誤差条件を確認できます。

q2軸→q3軸の実測180mmは `xy_robot_config.yaml` の **`Link3: 180.0`** に反映しています。`Link2: 0.0` は廃止済み横オフセットで、物理的な第2リンクを指しません。現在の2リンク最大長は200+180=380mm、手先リンク75mmを加えた最大長は455mmです。関節制限とyaw固定により実際の可到達範囲はさらに限られます。

遠い位置のトマトでは約240mmで可到達範囲に達しました。トマトをアーム側へ移した後は目標150mm付近まで接近し、左右・距離・yawの既存許容差を広げず、実際に `HARVEST_HOLD / approach_complete / hold_ready=true` を確認しています。上下誤差が48px未満で始まる場合は、仕様どおりZを動かさず、24px以内への追加補正は行いません。

記録・各試行の条件・集計はワークスペース直下の [tracking_trials_20261117](../../tracking_trials_20261117/) にまとめています。実果実の接触・収穫や、すべての対象位置・照明での成功を保証する検証ではありません。
