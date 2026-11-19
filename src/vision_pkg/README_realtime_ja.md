# D405 トマト画像追従（XY・yaw固定、任意でZ補正）

## このlaunchの設定ファイル（統合済み）

`vision_xy_tracking.launch.py` は **`src/vision_pkg/config/vision_xy_tracking.yaml` の1ファイル**から設定を読みます。自動収穫時は既存の `auto_harvest` EEノードも起動し、アーム・vision・EEの3ノードへ同じファイルを渡します。

## 到達後の自動収穫サイクル（2026-11-17変更）

```text
起動: EE原点復帰・初期化 → Z原点復帰 → XY初期姿勢 → 追従
到達 → XY停止確認 → 指定量だけZ上昇・停止確認
 → EE直動を伸ばす → フックを閉じる
 → XYをホーム関節角へ戻す・停止確認
 → EE直動を戻す → フックを開く
 → Z原点復帰・離脱・整定 → CYCLE_READY（c待ち）
c → 新しい対象の追従・収穫を開始
```

到達後は画像目標を受け付けず、EEによる遮蔽でも画像に追従しません。Z動作中はXYを保持し、EE動作中はZ・XYを保持します。収穫動作は直動→フックだけで、ピッチ操作は追加しません。XY復帰は関節空間の経路で、手先の直線後退ではありません。復帰中は直動を伸ばした状態とフック閉鎖を維持し、復帰完了後に直動収納→フック開放を順番に行います。

統合YAMLの調整箇所:

| 設定 | 意味 |
|---|---|
| `launch.auto_harvest_enabled: true` | 既存EEノードを起動して自動収穫を行う。Z・到達判定も有効にする |
| `harvest_cycle.automatic_sequence: true` | 上昇・EE収穫・収納・Z原点復帰を含む状態遷移を使う |
| `harvest_cycle.post_arrival_lift_m: 0.010` | 到達時のZ位置から10mm上昇。単位m、Picoの1mm単位へ丸める |
| `startup.home_joints_deg` | 収穫後のXY復帰先。初期値 `[10,110,-30]` 度 |
| `z_tracking.speed_m_s` / `move_timeout_sec` | 上昇速度と動作時間上限 |
| `z_tracking.home_speed_m_s: 0.010` | 起動時・収穫後のZ原点復帰速度。10mm/s。速度指定対応ファームウェアへの更新が必要 |
| `auto_harvest.arm_lift_timeout_sec` / `z_home_timeout_sec` | EE側で上昇・Z原点復帰の完了を待つ上限。45秒／140秒 |
| `auto_harvest.harvest_pose.enc4` / `initial_pose.enc4` | 直動の伸長／収納先。既存値−25／0（生カウント） |
| `auto_harvest.hook_servo.closed_feedback` / `open_feedback` | GP28の閉鎖／開放目標。既存値4000／500 |

上昇目標がZ可動範囲外なら異常停止し、上限へ切り詰めて続行しません。最後のZホームはリミットを使った原点復帰で、既存ファームウェアに従い原点から5mm離脱して保持します。Z位置はPicoのパルス数による推定で、独立した位置センサーの実測ではありません。EEはセンサー許容差・安定確認を用い、サービス受理や固定時間だけでは次へ進みません。

EE設定は `module/set_params.yaml` の現在値を統合YAMLへ転記しています。閉1600µs／開1350µs、停止1500µsも維持します。**このlaunchのEE調整先は統合YAMLです。単独EE・旧iPad経路は従来のmodule/set_params.yamlを使用します。**

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg end_effector_pkg vision_pkg
source install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured \
  synthetic_camera:=false show_window:=true \
  z_tracking_enabled:=true harvest_cycle_enabled:=true auto_harvest_enabled:=true
```

このコマンドでは実機EEも初期化・動作します。EEの手動操作ノードや別の自動収穫launchは同時起動しないでください。模擬環境用は `backend:=sim synthetic_camera:=true show_window:=false` に置き換えます。`vision_auto_harvest.launch.py` も同じ統合launchを使用し、EEを重複起動しません。

`WAIT_NEXT_CYCLE` / `CYCLE_READY` になったら起動端末で **c** を押します。端末入力が使えなければ別端末で送信します。

```bash
ros2 topic pub --once /end_effector/auto/key std_msgs/msg/String '{data: c}'
```

動作中の `c` は破棄し、予約しません。このモードで `n` は再開指令になりません。Space（または `{data: space}`）はEE駆動停止とアーム保持、Ctrl-Cは終了です。異常時の `c` では復帰せず、原因確認後に再起動します。停止時に自動トルクOFFを追加していません。

`/arm_xy/harvest/state` の `LIFTING → HARVEST_HOLD(post_arrival_lift_complete) → RETURNING → RETURNED → Z_HOMING → CYCLE_READY` と、`/end_effector/auto/state` の工程・実測値・目標値を確認できます。果実回収の判定はありません。今回の順序変更後の実機動作・もぎ取り力・果実保持は未検証です。ファームウェアの変更・書き込みは不要です。

以下の手動EE連携・旧経路の説明は従来モードのものです。追従だけ使う場合は `harvest_cycle_enabled:=false auto_harvest_enabled:=false require_ee_ready:=false` を指定します。

## 設定項目一覧

Z原点復帰速度は `z_tracking.home_speed_m_s`、通常のZ追従・到達後の上昇速度は `z_tracking.speed_m_s` です。前者を今回追加したためZ用Picoの更新が必要です。更新後の速度調整はYAML変更とlaunch再起動で反映します。省略時と旧サービスからの原点復帰は従来どおり5mm/sです。カメラ目標距離は `target.desired_distance_m`（現在0.15m＝150mm）です。

| 調整内容 | YAML内の場所 |
|---|---|
| 起動バックエンド・Z有効・到達保持・画面表示 | `launch` |
| 制御周期、関節速度・加速度、IK許容差・補正分解能 | `tracking` |
| 初期関節角 | `startup.home_joints_deg` / `startup.demo_joints_deg` |
| リンク寸法・関節制限 | `ik_solver_params` / `joint_limits_deg` |
| CAN・Dynamixelの校正・通信 | `can_mixed_backend` / `dxl_params` |
| Zの開始・停止画素幅、移動量、速度 | `z_tracking` |
| 到達許容差・安定確認時間 | `harvest_cycle` |
| カメラ・検出モデル・検出周期 | `camera` / `detector` / `processing_rate_hz` |
| 目標画素の左右・上下オフセット | `target.target_pixel_offset_x_px` / `target.target_pixel_offset_y_px` |
| 手先yaw・カメラ基準yaw | `target.goal_yaw_deg` / `target.camera_reference_yaw_deg` |
| 目標距離・画像接近速度 | `target.desired_distance_m` / `target.image_approach` |

起動引数は `launch` の設定を上書きします。既定の `launch.backend: sim` は維持し、自動収穫用に `launch.z_tracking_enabled` と `launch.auto_harvest_enabled` はtrueにしています。実機にはこれまでのコマンドを使えます:

**`startup_mode:=configured` と `z_tracking_enabled:=true` の組合せでは、起動ごとにZを自動原点復帰します。** Picoが原点確定済みでも再実行します。通信確認・XYの実測停止確認 → Z原点復帰・離脱・整定 → XYのhome/demo姿勢 → 追従開始、の順です。原点復帰に失敗するとXYへ進まず異常保持し、自動再試行しません。Zを無効にした場合はZを操作しません。

```bash
source ~/hibikino_toms_ws/install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured \
  synthetic_camera:=false show_window:=true \
  z_tracking_enabled:=true harvest_cycle_enabled:=true
```

別の統合YAMLを使うには `config_file:=/絶対パス/vision_xy_tracking.yaml` を追加します。変更後はノードを再起動してください。`--symlink-install` でビルド済みならYAMLの数値変更だけで再ビルドは不要です。コピーインストールでは再ビルドしてください。

`z_tracking:` など同じ階層のキーを複数回書かず、既存ブロック内の値を編集してください。後半ブロックで前半が上書きされる事故を防ぐため、launchは重複キーを行番号付きで検出し、ノード起動前に停止します。

初期姿勢を変更した場合は、初期角度を追従中も保持するため `target.goal_yaw_deg` を `startup.demo_joints_deg` の3角度の合計に合わせてください。例えば `[10,110,-30]` なら90°です。`camera_reference_yaw_deg` は取付け校正の基準で、別の設定です。

`target_lost_or_ambiguous` は検出自体があっても同じ対象への対応付けができない場合に出ます。画像接近モードでは最初の対象IDをXY・Z共通で固定し、長い消失後に別IDを再取得しても `approach_target_changed` で保持します。再取得IDのZ観測を先に送ることはありません。短い未検出では全軸を一時保持し、同じ対象の有効画像を確認して再開します。対象IDが変わった場合は原因を確認してlaunchを再起動してください。

**旧 `xy_robot_config.yaml`・`xy_tracking_params.yaml`・`realtime_detector.yaml` は、他のlaunchや単独ノード用として残しています。このlaunchからは参照せず、自動同期もしません。** 以下の旧ファイル名に関する説明は、統合ファイル内の同名キーへ読み替えてください。互換用の `vision_config:=...` を明示した場合だけ、vision部分を指定ファイルから読みます。

## 遠距離は画像で接近、近距離で深度へ（2026-11-17更新）

既定で `target.image_approach.enabled: true` です。遠距離では深度を必須とせず、同じトマトの**横画素誤差を減らしながら、設定速度で前進**します。横ずれが大きいほど前進を抑えます。深度の代わりに仮の3D目標を作る処理はありません。

既定の前進速度は40mm/s、画像だけで動く上限は実測XY移動200mmまたは15秒です。350mm以内の有効深度を初めて得た時点で画像だけの前進を止め、380mmまでの深度で3フレームの安定確認後に `desired_distance_m`（現在150mm）への距離制御へ切り替えます。その後の深度欠損では保持し、画像だけの前進には戻しません。Z補正中もXYは保持します。

設定は `config/realtime_detector.yaml` の `target.image_approach`、詳しい設定・診断・制約は **[画像接近の手順書](README_image_approach_ja.md)** を参照してください。実機ROSBAGで約150mmへの接近と既存到達判定による保持を確認しました。IKの補正分解能は到達許容差と独立させています。記録はワークスペース直下の `tracking_trials_20261117/` に保存しています。衝突回避・EEによる収穫成功を検証したものではありません。

## 縦画素によるZ補正（2026-11-17更新）

画像の目標高さから **画像高の1/10以上** ずれたら、XYを保持してZを動かし、**1/20以内** に収まったら停止します。480px画像なら開始48px、停止24pxです。Zの判定に深度は使いません。

目標高さは `config/realtime_detector.yaml` の `target.target_pixel_offset_y_px: 0.0` です。`target_pixel: null` のとき中心からのオフセットになり、正は下、負は上です。

Z移動は既定5mmずつの上限で行い、各区間で新しい画像を確認します。補正中はXYを保持し続け、移動中でも内側の範囲に入ったらZ停止を要求します。深度が無効でもZ補正を続けられ、完了後のXYは上記の画像接近／深度制御に従います。対象消失・古い画像・通信異常時は停止保持します。

**[設定・起動・停止・ROSBAG・制約の詳細](README_z_pixel_tracking_ja.md)**

```bash
source ~/hibikino_toms_ws/install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured synthetic_camera:=false \
  harvest_cycle_enabled:=false z_tracking_enabled:=true show_window:=true
```

前回の `Z_TRACKING_V1` ファームウェアをそのまま使います。上記のconfigured起動ではZ原点復帰も自動です。`startup_mode:=current` では自動原点復帰せず、原点未確定ならXYを保持して待ちます。この場合はスイッチと移動余裕を確認してから `/arm_xy/z/home` を要求します。無指定ではZ補正無効です。

以前の「深度換算10mm」の方式は、現在の追従経路では使いません。以前の数値検証は [履歴](../arm_controller_pkg/validation/z_tracking_20261117/summary.json) として残してあり、画素方式の実測結果ではありません。

自動EE収穫サイクルは[end_effector_pkgの手順書](../end_effector_pkg/README_auto_harvest_ja.md)を参照してください。新しいlaunchは `vision_auto_harvest.launch.py` です。既存の手動連携 `arm_ee_keycontrol.launch.py` とは別にEEシリアルを開くので、同時には起動しないでください。

## 追従中の一時的な検出欠損（2026-11-17修正）

Z補正中の未検出を即座に再起動必須の異常へ変換せず、Z・XYを停止保持する `OBSERVATION_HOLD` にしました。Z停止後の新しい有効画像3回で復帰を確認します。対象ID変更・モーター通信異常・明示停止は異常停止のままです。設定と状態の詳細は [Z画素追従の手順書](README_z_pixel_tracking_ja.md#深度が取れない場合と異常時) を参照してください。

CAN混成構成のq3起動チェックも、完全一致を要求していた箇所を修正し、設定済み1カウントの差を許容します。確認時間は `dxl_params.startup_readback_timeout_ms: 250` です。[起動時保持確認](../arm_controller_pkg/README_can_joint_migration_ja.md#q3の起動時保持確認2026-11-17修正) に条件を記載しています。両修正の反映には次を実行し、以前のlaunchを終了して再起動してください。実機移動による再検証は未実施です。

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
```

## EE操作で繰り返す収穫サイクル（2026-10-13追加）

既存の `arm_xy_tracker`、`vision_service_realtime`、`pull_module_teleop` の3ノードで動きます。ノードの追加はありません。

```text
接近 APPROACH
  → 同じ対象の誤差・実測速度が安定
保持 HARVEST_HOLD（レール調整・フック閉鎖は手動）
  → EE端末で r
引き戻し RETURNING
  → 実測関節が初期姿勢に到達
復帰完了 RETURNED（果実回収・フック準備）
  → EE端末で n
次の接近 APPROACH
```

`RETURNED`から自動で接近を再開しません。収穫成功やフック状態を自動判定する処理はなく、果実を回収して準備できたことを操作者が確認して `n` を押します。

### 起動

実機を使う場合は、端末を2つ用意します。端末1はアームのトルクONと初期姿勢への移動を伴います。

```bash
# 端末1: 画像追従とアーム（harvest_cycle_enabledは既定true）
source install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py backend:=dynamixel

# 端末2: キーを入力するEE操作端末
source install/setup.bash
ros2 launch harvest_task_pkg arm_ee_keycontrol.launch.py
```

カメラ・アーム・EEを接続しない確認では、端末1に `backend:=sim synthetic_camera:=true`、端末2に `simulate_hardware:=true` を指定します。

### EE端末のキー

アームとの連携キー（`h/r/n`）は初期姿勢への移動完了後に使用します。EEモーターの `w/s` はアーム状態に関係なく操作できます。

| キー | 動作 |
|---|---|
| `1`～`4`、`w` / `s` | 従来のEEモーター選択・正転／逆転。アームの起動中・接近中・保持中・引き戻し中も操作可能 |
| `h` | EEを停止し、アームを現在位置で保持。引き戻し中にも使用可能 |
| `r` | EEを停止し、保持を解除してアームの引き戻しを開始。保持中・保持完了確認後のみ受理 |
| `n` | EEを停止し、保持／復帰完了から接近を再開。対象の対応付けをリセットして新しい画像を待つ |
| Space | EE停止＋アーム保持。引き戻しを中断できる |
| `q` | EE停止＋アーム保持要求を送り、EEノードを終了 |

`r` は**アームを初期姿勢へ戻す操作**です。レールのモーター番号・縮む方向は推測で割り当てていません。レールを一緒に縮める場合は引き戻し中に従来の `w/s` を操作します。EEはアーム状態の変化や状態通知の途絶では自動停止しません。`Space` または `h` で明示的に停止してください。

戻る姿勢は `arm_controller_pkg/config/xy_robot_config.yaml` の `startup.demo_joints_deg`（現在 `[5,150.4,-55.4]`度）です。起動時の途中のhome姿勢は経由せず、実測関節角からこの姿勢へ、速度・加速度を制限した5次補間で戻します。手先の直線後退ではなく関節空間の経路なので、実機ではレールを含む経路を確認してください。Zは動かしません。トルクOFFは追加していません。

### 接近完了と保持

arm側YAMLの `harvest_cycle` で調整します。現在は以下が0.6秒続くことを必要とします。

- 同じ対象の新しい有効な観測があること。
- 横画素誤差が50px以内、距離誤差が6mm以内。各値はarm側 `config/xy_robot_config.yaml` の `harvest_cycle` で調整します。
- 実測関節速度が0.06rad/s以下、実測yaw誤差が0.03rad以内。
- 最新目標が有効で、直近のIKが成功し、実測XYと最新目標XYの差が15mm以内。
- 上記が同じ対象について0.6秒続いた後に到達扱いになります。保持指令後は実測停止を3周期確認してからEE工程を許可します。

制御できない上下画素誤差は完了条件へ含めません。保持状態では画像目標をアーム側でも拒否するため、トマトの見え隠れ・対象切替で保持が解除されません。`h`やEE操作による手動保持では、実測速度と保持位置を3周期確認してからEEモーター操作と `r` を許可します。

引き戻しは画像が消えても継続します。EEノードの通知が1秒途絶えた場合は現在位置で保持し、通信が戻っても自動で引き戻しを再開しません。実測の追従誤差超過、戻り時間超過、モーター通信異常は故障をラッチします。

### 状態・API

- `/arm_xy/harvest/state`: `std_msgs/String`のJSON。`state`, `sequence`, `reason`, `hold_ready`, `stamp`。10Hzで通知、最後の状態も配信。
- `/arm_xy/harvest/hold`, `/pull`, `/resume`: `std_srvs/Trigger`サービス。応答は要求の受理で、動作完了は状態トピックで確認します。
- `/arm_xy/harvest/ee_alive`: EEノードが0.2秒ごとに送る`std_msgs/Bool`。引き戻しの継続監視に使用。
- 画像診断の `harvest_state` と画面の保持理由でも現在の区間を確認できます。

`/arm_xy/vision_hold` は画像観測不良による一時保持です。`/arm_xy/hold` は明示保持で、Z補正中は異常をラッチします。収穫中の操作には上記のキー／サービスを使用してください。

従来の連続追従は端末1で `harvest_cycle_enabled:=false`。EEだけを単独操作する場合は端末2で `harvest_link_enabled:=false`。連携を無効にすると、EE操作からアームへの保持・復帰要求は出しません。

### ビルド・検証

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select arm_controller_pkg vision_pkg end_effector_pkg harvest_task_pkg
source install/setup.bash
python src/vision_pkg/test/run_harvest_cycle_validation.py
```

検証プログラムは専用ドメイン174・localhostで、既存3ノードの模擬バックエンドだけを起動します。結果は `validation/harvest_cycle_summary.json` と `validation/harvest_cycle_diagnostics.json` に保存します。実機の果梗をもぎ取る力、レールとの協調、収穫成功はこの試験では評価できません。

2026-10-13の検証結果:

- 関連単体テスト88件成功。
- install側のコードで模擬収穫を2サイクル完了。復帰後は `n` を押すまで保持。
- 保持中の画像目標の拒否、画像保持要求に妨げられない引き戻し、実測初期姿勢への復帰を確認。
- EE通知途絶時の保持、Spaceによる引き戻し中断、アーム接近中のEE独立操作を確認。
- 関連4パッケージをビルド。実機・実カメラ・実EEは起動していません。


## 目的と今回の原因

画像追従部分は、手先と一緒に動くD405で、**同じトマトの画像横位置を目標画素に合わせます**。遠距離では画像接近を行い、近距離の深度確定後に設定距離または観測開始時の距離を維持します。以下の距離計算の説明は深度制御段階（または `image_approach.enabled: false`）のものです。上記の収穫サイクルはこの接近・保持処理とEE端末の操作を連携させます。

旧リアルタイムノードは中央に近い検出を選んだ後、トマトの3D位置全量を現在手先位置へ加算していました。そのため中央でも距離分の移動目標が発生しました。毎フレームの中心最近傍選択には対象切替もありました。trackerでは各関節の速度を個別にクリップし、IK解が正しいyawでも途中の `q1+q2+q3` が変わる問題がありました。提供動画の約15秒のフレームでは、赤い検出枠と中心がトマト中央でなく左側の指に重なっています（表示深度0.091m）。取付角の誤差、手を含む検出中心の偏りも実機の左移動を生む可能性がありますが、それらの実測校正は今回行っていません。

この修正では既存の `vision_service.py`、収穫サービス、旧 `arm_controller.py`、`ik_solver_arm2.py`、`motor_controller_module_5motor.py` を変更していません。既に存在した作業ツリーの変更は保持しています。対象階層に適用されるAGENTS.mdは見つかりませんでした。ROS環境はHumbleです。

## 自由度と座標

- ROSの位置は **m**、角度は **rad**。`*_deg` 設定だけ度。
- `arm_base`: +X=右、+Y=前方／奥行き。Zは固定し、Zモーターを起動しません。
- 起動関節角 `[5,160,-65] deg` → 手先yaw=100度。
- `target.goal_yaw_deg: 100` が運転中の目標yaw。現在yawに置き換えません。
- 現在の取付想定では、光学X=右、光学Y=下、光学Z=奥行き。画像上下はアームZに対応します。**XY・yaw固定では、任意の上下ずれを中央へ動かせません**。横誤差と距離のみ制御し、上下誤差は表示・記録します。縦横とも中央になるのは対象の高さが目標視線に一致する場合です。

### 変換の意味

`config/realtime_detector.yaml` の設定は以下の関係です。

```text
R = Rz(actual_yaw - camera_reference_yaw) * camera_to_end_effector[:3,:3]
camera_origin_base = tool_position_base
                   + Rz(actual_yaw - camera_reference_yaw) * camera_to_end_effector[:3,3]
point_base = camera_origin_base + R * point_camera
```

`camera_to_end_effector` は名前を互換維持していますが、**基準yawのときにarm_baseと揃う軸で表したカメラ取付変換**です。通常の「yaw=0の手先ローカル座標への変換」をそのまま入れてはいけません。回転部分は正規直交・det=+1を検証します。並進はカメラ原点の手先からの位置（m）です。元の設定にあった並進0は保持しており、校正済みとみなしていません。

`camera_reference_yaw_deg` はこの取付変換の角度基準です。`goal_yaw_deg` は制御目標です。別の役割なので個別に設定します。今回、取付回転の符号や角度は推測で変更していません。

### 画像誤差から移動への計算

既定の目標画素は `((width-1)/2,(height-1)/2)`、640×480なら `(319.5,239.5)`。RealSense内部パラメータの主点 `(ppx,ppy)` とは別です。

検出画素と深度をRealSenseの内部パラメータ・歪みモデルで3D化します。水平方向の目標視線は **目標uと観測v** を逆投影し、制御できないvの誤差を横補正へ混ぜません。

```text
horizontal_error_m = point_camera.x - desired_ray.x / desired_ray.z * depth
range_error_m      = depth - locked_distance
B = R.T[:, :2]
A = [ B[0,:] - desired_ray.x/desired_ray.z * B[2,:] ; B[2,:] ]
velocity_xy = gain * solve(A, [horizontal_error_m, range_error_m])
goal_xy = capture_time_tool_xy + limited_velocity_xy * dt
```

XY並進時に `d(point_camera) = -R.T[:, :2] d(tool_xy)` となることから導出しています。取付によってこの2×2行列が悪条件なら保持します。相対変位なので並進オフセットを再加算しません。yawは固定、上下誤差は計算へ入れません。

中心・目標距離なら両誤差がゼロです。深度全量を前進量にする処理はなくなりました。`desired_distance_m: 0` はready後の最初の安定6フレームの深度中央値を固定します。正の値ならその距離を使います。短い見失いでは距離を保持、1.5秒以上の消失後は新IDで再取得し、初回距離方式では再ロックします。

## ファイルの役割

| ファイル | 内容 |
|---|---|
| `vision_pkg/vison_sevice_realtime.py` | D405、YOLO、深度、時刻付き姿勢、表示、ROS入出力。既存名のスペルを維持 |
| `vision_pkg/modules/image_servo.py` | 対象対応付け、深度判定、画像誤差のXY変換、重みパス解決。ROSノードは増設しない |
| `arm_controller_xy_tracker.py` | 最新目標、実測関節からのIK、保持／故障、周期と姿勢診断 |
| `modules/yaw_joint_limiter.py`（arm側） | 速度・加速度・可動範囲の箱制約と関節速度和の制約を同時に満たす指令 |
| `launch/vision_xy_tracking.launch.py` | visionとtrackerの同時起動。既定は模擬モーター＋実D405 |
| `test/test_image_servo.py` | FKから固定3D対象を再投影する閉ループなどの検証 |
| `test/run_ros_servo_validation.py` | 合成カメラ＋模擬アーム専用のROS実時間計測 |

## ビルドと起動

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
```

ソースのYAMLを書き換えたら再ビルドしてください。通常インストールでは `install/vision_pkg/share/vision_pkg/config/realtime_detector.yaml` はコピーです。今回ソース側の並進Z=0に対しinstall側に0.110が残っていた点も確認し、再ビルドで揃えています。

### D405画面が出ない・途中で止まる場合（2026-11-16）

`Opened RealSense`はストリーム開始が成功したという意味です。その後のUSB切断は別に確認します。2026-11-16 14:45:25の調査ログでは、D405のUVC処理で`-71`と`-32`が発生してUSBが切断され、14:45:30に新しいUSB機器番号で再認識されていました。旧ノードは古いSDKパイプラインをpollし続け、画像なしの分岐ではウィンドウも周期ログも表示しなかったため、何も起きないように見えていました。`goal_age=inf`はtrackerが目標を一度も受理していない状態を表します。

修正版は起動直後から待機画面を表示し、画像がなくても5秒ごとの周期ログと`/vision/servo_diagnostics`を出します。`camera_frame_age_sec`は最後にフレームを受け取ってからの経過時間、`camera_reconnect_count`はSDK再接続の試行回数です。YAMLの`camera`に以下を追加しています。

```yaml
camera:
  frame_timeout_sec: 2.0       # この時間フレームがなければSDK接続を開き直す
  reconnect_interval_sec: 3.0 # 再接続試行の最小間隔
```

画像未受信・再接続中はアーム保持を要求し、目標を送りません。再接続後も新しい画像・時刻・実測姿勢などの通常の検証を通った場合に目標を送ります。この処理はカメラのSDK接続を閉じて開き直すもので、USB機器のハードウェアリセットやアームの再初期化は行いません。カメラが物理的に接続できない状態なら待機と再接続を繰り返します。

切り分けは、実行中のlaunchをCtrl-Cで終了してから、カメラ単独で行います。

```bash
cd ~/hibikino_toms_ws
source install/setup.bash
ros2 run vision_pkg vision_service_realtime --ros-args -p show_window:=true
```

別端末で`journalctl -k -f`を開き、`USB disconnect`やUVCエラーが出るか確認してください。USB経路・ケーブル・ハブ給電が候補ですが、今回のログだけで不良部品までは特定していません。複数のカメラノードで同じD405を同時に開かないでください。コマンドを改行するときの`\`は行末に置き、その後ろに空白を入れないでください。

再認識後のD405を実機でカメラ単独起動し、ウォームアップ後14.66～15.00fps、処理58.3～63.3ms/枚、正常なCtrl-C終了を確認しました。取得処理がフレームを返さない状態を試験上で注入した復帰試験でも、2秒でSDK接続を開き直し、その後131枚の実画像を処理できました（物理的なUSB抜き差しを再現した試験ではありません）。未受信時の表示・保持・再接続など関連テスト26件に成功しています。実機の移動は行っていません。試験記録は`validation/camera_no_frames_20261116/`です。USB断そのものの解消と、長時間の接続安定性は別途確認が必要です。

現在のアーム起動角度を`[20,100,-30]°`にした場合、合計yawは90°です。ビジョン設定の`target.goal_yaw_deg: 100`とは10°異なるため、目標を受け取ると100°へ動こうとします。`camera_reference_yaw_deg`はカメラ取付変換の基準であり、起動角や目標yawとは別に実取付へ合わせて確認してください。

### カメラ・モーターを使わない閉ループ

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=sim synthetic_camera:=true show_window:=true
```

固定された3D対象を、模擬関節の実測FKから得た移動カメラへ投影します。画像が動くのは目標を循環再生しているためではありません。表示不要なら `show_window:=false`。合成カメラは最新の模擬実測姿勢を保持して15Hzで再投影します（姿勢入力自体は10Hz）。`synthetic_camera:=true backend:=dynamixel` の組合せはlaunchで拒否します。

### 実D405で検出と指令を確認、アームは模擬

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py backend:=sim
```

D405は動かないため、模擬アームの移動に応じた画像フィードバックはありません。この組合せで実機追従の成功を判定しないでください。実画像検出・深度・診断の確認用です。

### 検出ノード単独

```bash
ros2 run vision_pkg vision_service_realtime
# または
ros2 launch vision_pkg vision_service_realtime.launch.py
```

`/arm_xy/ready` と時刻の合う `/arm_xy/actual` がなければ表示・検出のみで、移動目標を発行しません。モデルはYAML相対パスをまず試し、install配置では祖先から `module/weights/base.pt` を探します。別配置は `detector.weights` に絶対パスを指定できます。

### 実機を使うとき（今回自動実行していない）

取付変換・対応するモーター・限界を実測確認した後、操作者が実行します。これはトルクONと既存の初期姿勢への移動を伴います。

```bash
ros2 launch vision_pkg vision_xy_tracking.launch.py backend:=dynamixel
```

U2D2、モーターID、反転、ゼロ、範囲、プロファイルは `arm_controller_pkg/config/xy_robot_config.yaml`。Zは移動しません。収穫サービスや円デモとの同時運転はしないでください。

停止はlaunchの端末で **Ctrl+C**。表示ウィンドウの `q`/Escは検出ノードのみ終了します。接近中は目標タイムアウト後に保持します。収穫保持・引き戻しの制御権はアーム側にあり、引き戻しの中断にはEE端末のSpaceまたは `h` を使います。接近中の一時的な観測保持を要求する場合:

```bash
ros2 topic pub --once /arm_xy/hold std_msgs/msg/Empty '{}'
```

有効な次の観測で追従再開します。停止を続ける場合は検出ノードを終了します。自動トルクOFFは追加していません。通信断時は保持指令自体が届かない可能性があります。

## 調整項目

| 設定 | 既定／意味 |
|---|---|
| `processing_rate_hz` | 15Hz（取得・検出の目標レート。実績は診断で確認） |
| `target.target_pixel` | null=表示中心。`[u,v]` で変更可能 |
| `target.target_pixel_offset_x_px` | `target_pixel`（nullなら表示中心）からの左右オフセット。正で画面右、負で画面左。単位px、既定0 |
| `desired_distance_m` | 0=初回安定値を固定。正値=指定距離 |
| `pixel_deadband_px` / `distance_deadband_m` | 3px / 0.004m。連続した不感帯 |
| `gain_per_sec` | 2/s |
| `max_speed_m_s` / `max_acceleration_m_s2` | 0.025m/s / 0.08m/s² |
| `max_step_m` | 1観測で最大0.003m。dt上限0.15sでも守れる速度上限を併用 |
| `tracking_confidence` | 0.45。YOLO候補抽出自体は0.25 |
| `association_gate_px` / `ambiguity_margin_px` | 前中心から45px以内、競合候補の差8px未満は保持 |
| `depth_jump_m` / `depth_spread_m` | 前有効深度から0.035m跳躍、パッチの10–90百分位幅0.015m超は保持 |
| `pose_sync_tolerance_sec` | 撮影時刻と最近傍姿勢の差最大0.12s。前後の姿勢が揃えば補間 |
| `observation_max_age_sec` | 推論後の画像年齢0.25s超で保持 |
| `actual_max_age_sec` | 最新姿勢の年齢上限0.25s |

関節速度0.25rad/s、加速度0.8rad/s²はarm側 `xy_tracking_params.yaml`。新しい `tracking_position_tolerance_m`=1e-5、`tracking_angle_tolerance_rad`=1e-4 はtracker専用。前回の送信指令と実測関節は別に保持し、IKは毎回実測から開始します。指令生成は加速度制限付きで関節速度和を拘束し、100度の指令yawを保ちます。`max_following_error_rad`=0.15超なら故障保持します。

目標消失などで実測位置へ停止・保持するときは、通常軌道の加速度連続性より停止を優先します。実際の減速はDynamixel内部プロファイルにも依存します。速度和制約は送信指令の姿勢を保つもので、各モーターの物理的遅れが異なる場合の実測yawを保証するものではありません。

## 対象・深度・時刻・故障

- 初回は中心に近い有効検出。以後は前中心との距離、bbox面積比、信頼度で対応付け。bbox縦横比0.5～2.0の候補に制限し、極端に細長い指などの候補を抑えます（閾値は設定可能）。競合が曖昧なら保持。重なった見た目の似たトマトの識別を保証する外観モデルではありません。
- マスクがあればマスク重心、なければbbox中心。空マスクは破棄。どちらかを画面と診断に表示します。手・背景をトマトとする高信頼の誤検出を完全には除けないため、記録した中心・bbox・信頼度を画像と照合します。
- 深度は中心付近の有効なマスク内値の中央値。無効時に背景の値を代用しません。急な深度ジャンプは以前の有効深度を保持し、元へ戻るまで指令を停止します。長い消失後の再取得／ノード再起動でも再初期化できます。
- 撮影はRealSense global/system時刻。ハードウェア時刻だけのフレームは指令に使わず同期待ち。ROS時刻への変換、推論後年齢判定、姿勢履歴との対応を行います。実D405で `use_sim_time` は使用しないでください。
- ROS姿勢受信は専用executorスレッド、カメラ・推論・OpenCV生成／表示／終了はmainスレッド。カメラ取得はpollで最新フレームを取得。二重imshowによる点滅を防ぎます。
- 対象消失・異常観測は `/arm_xy/vision_hold` で一時保持要求。対象ID変更は `/arm_xy/hold` で停止します。プロセス停止はtrackerの目標タイムアウトでXYを保持し、Z補正中の画素観測タイムアウトではZ・XYを一時保持します。Goalのstampは受信時刻に書き換えず撮影時刻を保持します。
- IK失敗は実測位置で保持。通信異常は一度だけ可能な範囲で実測保持を試みて故障をラッチし、動作の自動再試行はしません。競合する収穫サービスが見えた場合は指令を抑止します。

## 記録・診断

```bash
ros2 bag record /vision/servo_diagnostics /arm_xy/diagnostics \
 /arm_xy/actual /arm_xy/goal /arm_xy/joints /arm_xy/command_joints \
 /arm_xy/error /arm_xy/hold /arm_xy/vision_hold /arm_xy/z/state /arm_xy/ready
```

- `/vision/servo_diagnostics` (`std_msgs/String`、JSON): `track_id`, `center_source`, `center`, `target_pixel`, `pixel_error`, `depth_m`, `desired_distance_m`, `distance_error_m`, `capture_stamp`, `observation_age_sec`, `pose_gap_sec`, `actual_pose`, `goal_pose`, `reason`, `processing_sec`。無効／未観測の値は省略またはnullで、古い値を新しい観測として流しません。
- `/arm_xy/diagnostics` (JSON): 実測pose/関節、目標pose、IK解とFK、送信関節とFK、`commanded_yaw_error`, `measured_yaw_error`, IK理由、保持理由、周期／処理時間／目標年齢。
- `/arm_xy/command_joints` は成功した送信指令、`/arm_xy/joints` は実測。いずれもrad。起動途中の指令は初期姿勢までの移動であり、運転中の100度保持評価とは分けます。
- 目標受信15Hz、モーター指令10Hz、モーター内部制御周期は別です。内部周期・追従遅れは今回測定していません。

## 実機で測定する項目

基準姿勢でのカメラ光学軸とarm_baseの対応、取付傾き・レバーアーム、内部パラメータ／深度精度、モーター型番とプロファイル再設定時の動作、各関節の遅れ・バックラッシュ・角度ゼロ、取付高さと対象高さ、画像時刻と実測姿勢時刻の偏り。取付誤差をgoal_yawで打ち消す調整はしません。今回のIKと閉ループ確認は衝突安全性を保証しません。

## 検証の再実行

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
PYTHONPATH=src/vision_pkg:src/arm_controller_pkg:$PYTHONPATH python -m pytest -q \
 src/vision_pkg/test/test_image_servo.py src/vision_pkg/test/test_realtime_gui.py \
 src/arm_controller_pkg/test/test_joint_startup.py src/arm_controller_pkg/test/test_stream_torque.py
python src/vision_pkg/test/run_ros_servo_validation.py
```

後者は専用ドメイン172、localhost、backend=sim、synthetic_camera=trueを固定し約80秒動きます。通信にはlocalhost DDSソケットが必要です。結果は `validation/`。推論速度測定は保存画像のみ:

```bash
python src/vision_pkg/test/benchmark_recorded_inference.py 保存画像.png --device 0
```

## 今回の測定結果（2026-10-12）

ビルド成功: `arm_controller_pkg`, `vision_pkg`。上記pytest **77件成功**。
結果詳細は [ROS集計](validation/ros_summary.json)、[全周期の診断](validation/ros_diagnostics.json)、[数値閉ループ](validation/closed_loop.json)、[グラフ](validation/closed_loop_ros.svg)。

| 項目 | 結果 |
|---|---|
| 中央・0.25mの固定対象 | 60秒の数値閉ループでXY移動は数値精度内でゼロ |
| 左右の固定対象 | 初期±60px → 最終約±3.117px（不感帯3px＋IK許容差） |
| 到達後 | 最後5秒のXY変化0.2mm未満をテストで確認 |
| 縦方向だけの誤差 | 96px相当を与えてもXY移動ゼロ、Z/yaw変更なし |
| ROS合成画像レート | 15.000fps |
| ROS制御レート | 10.008Hz |
| ROS横誤差 | 60.5 → 3.177px |
| ROS上下誤差 | 36.5 → 36.491px（制御対象外） |
| 最終距離誤差 | 0.100mm |
| 送信指令yaw最大誤差 | 8.88e-16rad |
| 模擬実測yaw最大誤差 | 8.88e-16rad（実機保証ではない） |
| 制御処理時間 平均／最大 | 5.694 / 8.964ms |
| 周期間隔 最大 | 104.368ms |
| 周期間隔100ms超／処理時間100ms超 | 256 / 0回（tracking集計） |
| 観測年齢 平均／姿勢時刻差 最大 | 3.046 / 75.455ms |

平均10Hzは満たしました。厳密な100ms以内の周期保証ではありません。`>100ms` は100.01msのようなスケジューラの揺れも数えるため、処理時間超過とは分けています。

無理な距離変化、左右対象、主点と表示中心の差、深度外れ値、空マスク、識別の曖昧さ、短い消失と長い消失後の再取得、古い／重複画像、姿勢時刻ずれ、関節速度・加速度・範囲、IK不能、通信故障ラッチ、GUIスレッド、source/installの重み解決をテストしました。ROS実行では検出停止後の保持、複数目標の最新値置換、IK失敗保持、競合サービスでの抑止を確認しています。各関節の応答遅れを変えた模擬試験では実測yawの過渡誤差が出ることも確認しており、送信yawだけで実機姿勢保持を判定していません。

base.ptの保存画像GPU推論（ウォームアップ5回除外、20回）:

- スクリーンキャスト全体: 平均49.99ms、20.00fps。
- D405表示の640×480切り出し: 平均46.71ms、最大67.39ms、21.41fps。レート制限15Hzで動かす想定です。この切り出しは表示文字や枠を含み、再推論での検出数は0でした。元の未描画画像の検出精度を評価した数値ではありません。
- CPU（全体画像）: 平均1964ms、0.51fps。CPUでは10～20fpsを満たしません。

[GPU結果](validation/inference_0_camera_crop.json) / [CPU結果](validation/inference_cpu.json)。サンドボックスではGPUが見えなかったため、GPU測定とlocalhost DDS試験のみ許可された実行範囲で行いました。いずれも実D405・実モーターは開いていません。**D405取得・推論・GUIを合わせた実機10～20fps、および実機での画素誤差収束は未測定**です。

| パラメータ | 意味 |
|---|---|
| `desired_distance_m: 0.3` | カメラから対象まで保ちたい距離。今回は **30cm**。`0`にすると、最初の安定した深度から距離を決めます。 |
| `stable_depth_frames: 6` | `desired_distance_m: 0` のとき、距離を決めるために使う連続フレーム数。 |
| `stable_depth_spread_m: 0.005` | 上記フレームの深度のばらつき上限。今回は **5mm**。これ以内に収まると初期距離を確定します。 |
| `gain_per_sec: 20.0` | 画像の横ずれと距離誤差を、補正速度へ変換する強さ。値を上げるほど速く反応します。 |
| `pixel_deadband_px: 3.0` | 中心から横に3px以内なら、横方向の補正を行いません。 |
| `distance_deadband_m: 0.004` | 目標距離との差が **4mm以内**なら、距離方向の補正を行いません。 |
| `max_speed_m_s: 0.5` | XY補正速度の上限。**0.5m/s**です。15Hzで毎回この上限に達すると、1回あたり約3.3cmの補正量になり得ます。 |
| `max_acceleration_m_s2: 0.5` | XY補正速度の加速・減速の上限。単位はm/s²です。 |
| `max_step_m: 0.1` | 1回の目標更新で許すXY移動量の上限。コードでは速度上限にも使います。今回の設定では `0.1 / 0.15 ≈ 0.67m/s` なので、実際は `max_speed_m_s` の **0.5m/s** が先に上限になります。 |
| `min_depth_m: 0.07` | これより近い深度は無効として扱います。今回は **7cm**。 |
| `depth_spread_m: 0.015` | 深度パッチ内の10～90パーセンタイルの幅の上限。**15mm**を超えると深度を無効にします。 |
| `depth_jump_m: 0.035` | 前回の有効深度から **35mm超**の急変があれば、異常として指令を保持します。 |
| `observation_max_age_sec: 0.25` | 撮影から処理までの遅れが **0.25秒超**なら、その観測を使いません。 |
| `pose_sync_tolerance_sec: 0.12` | 撮影時刻と手先姿勢の時刻の差の許容値。**0.12秒超**なら保持します。 |
| `tracking_confidence: 0.45` | 対象追跡に使う検出の信頼度下限。0～1の値です。 |
| `association_gate_px: 45.0` | 追跡中の対象中心から **45px以内**にある検出を、同じ対象の候補として扱います。 |
| `ambiguity_margin_px: 8.0` | 候補同士の距離差が **8px未満**で曖昧なら、対象を切り替えず保持します。 |
| `min_bbox_aspect: 0.5` | bboxの幅÷高さの最小値。細長すぎる検出を除外します。 |
| `max_bbox_aspect: 2.0` | bboxの幅÷高さの最大値。横長すぎる検出を除外します。 |
| `min_bbox_area_px: 80.0` | bbox面積の下限。80px²未満の検出は除外します。 |
| `max_bbox_area_px: 70000.0` | bbox面積の上限。70000px²を超える検出は除外します。 |
| `lost_timeout_sec: 1.5` | **1.5秒**対象が見つからなければ追跡IDを解除し、再検出時に対象を選び直します。 |
