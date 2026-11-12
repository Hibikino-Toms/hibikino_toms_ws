# 自動収穫EE：NCリミットによる直動原点復帰

2026-11-12更新。起動時の`c`押下を廃止し、直動を引き込んでNCリミットを検出するとENC4を0に設定します。ROSノードは既存の`auto_harvest`を使い、追加しません。

EEの自動動作・PWM・センサー・原点復帰・サーボ校正値は`module/set_params.yaml`の`auto_harvest`にまとめています。Picoのシリアル番号とボーレートは同ファイルの`EE_params`を共用します。

## 現在の配線

| 機能 | 駆動 | センサー | 備考 |
|---|---|---|---|
| ロール | M1 GP10/GP11 | POT1 GP26 | 既存のロール設定を維持 |
| 直動 | M2 GP12/GP13 | ENC4 GP8/GP9 | **論理正PWM（GP13）が引込み、論理負PWM（GP12）が押出し** |
| フック | 連続回転サーボ GP17 | FB GP28 | PicoとYAMLを1500µs停止、1600µs閉指令、1350µs開指令に統一 |
| 収納端リミット | GP19–COM/NC–GND | INPUT_PULLUP | 通常LOW、作動／断線でHIGH |
| ピッチ | 現在の配線には無し | 無し | 自動収穫のピッチ工程は実行しない |

詳細は[ピン設定](../../module/pico_programs/hardware_pin_reference.md)。自動収穫用ファームウェアは、実際の回転方向に合わせてM2の論理PWM極性を補正しています。GP16/17を旧M4のDC出力として使用するファームウェアは、この配線に使用しません。

ROS内部でもセンサー名を実配線に合わせ、`pot1`=ロール、`servo_fb`=GP28のサーボFB、`enc4`=直動として扱います。現在の構成ではPOT3/POT2を読みません。旧`legacy_four_dc`プロファイルだけが実POT3を使います。`DRIVE`の4要素は`[ロール, 未使用0, フック, 直動]`という論理順です。手動シリアルの`M1`=ロール、`M2`=直動、`M3`=サーボで、`M4`は使用しません。

## 起動時の処理

1. 全出力を停止し、`/end_effector/ready=false`のまま、新ファームウェアの正常なセンサー・リミット通知を待つ。
2. `HOME_ENC4`要求を1回だけ送り、直動M2のみを正PWMで引き込む。他のDC軸とサーボは停止。
3. GP19がHIGHになると**Pico内で直動を停止**する。接点が40ms安定したら、実際の引込み中のエンコーダー変化から符号を決めてENC4を0にする。以後のENC4は引込みが正、伸長が負。
4. ROS側で今回の要求IDに対応する新しい完了通知・リミット・停止PWM・ENC4ゼロを確認する。古い完了通知やPico再起動時のENC4=0だけでは原点成立にしない。
5. サーボのFB端点が校正済みなら、装着されている軸だけを初期化してEE readyを通知する。アームはEE ready後に起動する。

起動時からGP19がHIGHの場合は、すぐ原点成立にせず、制限付きで少し伸ばしてLOWと最低1カウントの変化を確認し、再び引き込みます。引込みで1カウントも変わらずリミットへ触れた場合にも、この確認を行って符号を確定します。LOWにならない場合やエンコーダーが変化しない場合は停止してFAULTになります。NC開放はスイッチ作動と断線で同じ電気状態なので、運転中の断線を完全には識別できません。

原点復帰には時間・移動量・エンコーダー無変化の上限があります。600ms以上ホスト通信が途絶えた場合はPicoが駆動を停止します。通常動作でもリミットHIGH中の追加引込みは禁止し、リミットから離れる伸長方向は許可します。停止・異常からの自動再試行はしません。

## 原点復帰の設定

`module/set_params.yaml`の`auto_harvest.encoder_homing`を編集します。

| 設定 | 現在値 | 意味 |
|---|---:|---|
| `retract_pwm` | 220 | M2引込みの正PWM。`pwm.min/max.enc4`の範囲で指定 |
| `timeout_sec` | 20.0 | 原点復帰全体の上限時間 |
| `progress_timeout_sec` | 3.0 | 駆動中にENC4が変化しない最大時間 |
| `debounce_ms` | 40 | スイッチ状態の安定確認時間 |
| `release_max_counts` | 4 | 初期HIGH時にスイッチを離す移動の最大ENCカウント |
| `max_travel_counts` | 70 | 引込み探索の最大ENCカウント（未原点値そのものではなく変化量） |
| `initial_telemetry_timeout_sec` | 5.0 | 起動時に新しい正常通知を待つ上限時間 |

PicoはGP19固定です。変更する場合はファームウェアも変更・再ビルドしてください。値は生カウントで、角度や距離へ推測で換算しません。

## サーボ指令値とフィードバック校正

YAMLに記録した実測指令値をPicoにも反映しています。1500µsが停止、1600µsが閉方向、1350µsが開方向です。値の大小が逆転していてもクランプ範囲を正しく計算します。ROS側は通常運転時にこのファームウェア設定と一致する端点を要求します。原点復帰だけの確認ではサーボを1500µsに保持し、開閉指令は送りません。

```yaml
hook_servo:
  neutral_us: 1500
  close_us: 1600
  open_us: 1350
  calibration_valid: true
  open_feedback: 1900
  closed_feedback: 3705
  feedback_median_samples: 3
  direction_window_sec: 0.6
```

実測した開放・閉鎖のGP28サーボFB値（0～4095）を`open_feedback`/`closed_feedback`に設定し、`calibration_valid: true`へ変更して再ビルド・再起動すると、初期化と収穫シーケンスへ進みます。両端点はFBが0/4095を跨がない同じ単調区間で測定してください。`sensor_limits.servo_fb`の0～4095はADC値の妥当性範囲であり、機械限界の校正値ではありません。実行時診断の`sensor`にも`servo_fb`として表示されます。`harvest_pose.enc4`の伸長目標も、新しい原点・機構で確認してください。

現在の実機では閉方向の正指令でFBが増加し、開方向の負指令で減少します。`increase_pwm_sign.servo_fb`も現在は`+1`です。実行時には`open_feedback`と`closed_feedback`の大小から自動的に決定します。初期FBが1900未満でも、その値だけで校正不良とは判断せず、目標との差と実際の移動方向を監視します。

`close_us`と`open_us`は方向ごとの最大速度指令です。Picoは`1500 + (方向の端点 - 1500) × |PWM| / 255`で速度を調整します。PWM=+255なら1600µs、PWM=-255なら1350µsです。現在の自動制御の上限PWM=220では、閉方向1586µs・開方向1371µsになります。`servo_us`は送信パルスの診断値で、位置の到達判定には使いません。

### 動作中のFB揺れと逆方向判定

2026-11-12の実機確認で、閉方向に動いていてもFBが946→860と1サンプルだけ逆行し、従来の30カウント閾値で停止する現象を再現しました。次の設定で一時的な揺れを処理します。

| 設定 | 値 | 用途 |
|---|---:|---|
| `hook_servo.feedback_median_samples` | 3 | 新しく受信したGP28値の中央値。1・3・5・7・9から指定 |
| `hook_servo.direction_window_sec` | 0.6秒 | この時間幅の正味変化で継続的な逆方向移動を判定 |
| `home_stability_tolerance.servo_fb` | 30 | 逆方向判定で許容するFBの変化幅 |
| `target_tolerance.servo_fb` | 70 | 目標FBとの許容差。今回拡大していない |

`/end_effector/auto/state`の`sensor.servo_fb_raw`が受信した生値、`sensor.servo_fb`が制御に使う中央値です。停止・指令反転・工程切替で逆方向の観測履歴をリセットします。継続的な逆方向移動は引き続き停止し、判定には設定した時間窓と通信・フィルタ分の時間が必要です。無進捗・タイムアウト・通信断の監視も維持します。

FBは1回転を0〜3.3Vで表す信号です（[メーカー仕様書](https://www.feetechrc.com/Data/feetechrc/upload/file/20200612/6372755559651881253812758.pdf)）。今回の端点は同じ単調区間として扱い、受信値が半回転相当の2048カウントを超えて飛んだ場合は、別の回転を選んで続行せず停止します。

測定には自動ノードを終了してから、既存の手動ノードを使えます。

```bash
ros2 run end_effector_pkg pull_module_teleop --ros-args \
  -p harvest_link_enabled:=false \
  -p motor_pwm:=180 \
  -p servo_pwm:=100
```

`motor_pwm`はDC軸（M1ロール、M2直動）のPWM、`servo_pwm`はM3フックサーボの速度指定で、どちらも1～255です。サーボ速度を変えるときは`servo_pwm`だけを調整し、値が小さいほど停止パルスに近い指令になります。小さすぎるとサーボが動かない場合があります。値はノード起動時に読み込むため、変更後はノードを再起動してください。

2026-11-12のロール実測では、PWM100でPOT1の変化が停止中の揺れと区別できず、PWM180では正PWMでPOT1が減少しました。このため現構成の`pwm.min.pot1`・`pwm.max.pot1`を180に設定しています。`roll_motor.feedback_median_samples: 3`でPOT1を中央値処理し、`roll_motor.direction_window_sec: 0.4`秒の変化から継続的な逆方向を判定します。診断の`pot1_raw`は受信生値、`pot1`は制御に使う中央値です。継続的な逆転・無進捗・通信断は停止します。

新ファームウェアでは`3`でサーボ選択、`w`が閉方向、`s`が開方向です。各目標位置でSpaceを押して停止し、表示される`SERVO_FB`値を記録します。手動ノードの終了後にYAMLを反映してください。

## ビルド・書込み

新ファームウェアは`module/pico_programs/pull_ee_auto_harvest/pull_ee_auto_harvest_limit.ino`、原点状態機械は同フォルダーの`rail_homing.h`です。PlatformIOプロジェクトの`src/main.cpp`がこの新スケッチを取り込みます。旧4DCスケッチと手動用スケッチは保存しています。

```bash
cd ~/hibikino_toms_ws
/home/ylab/.platformio/penv/bin/pio run -d module/pico_programs/pull_ee_auto_harvest_pio
cd module/pico_programs/pull_ee_auto_harvest_pio
./upload_auto_harvest.sh
```

書込みスクリプトは設定済みPico 2 WのUSBシリアル番号`A437E4B324D4447A`を照合します。新ファームウェア単体の起動は全出力停止で、原点復帰はROSからの要求後に始まります。旧ファームウェア／テストスケッチには今回の通信機能がなく、ROS側は原点復帰を開始せずFAULTにします。

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select end_effector_pkg
source install/setup.bash
```

## 原点復帰だけを確認する起動

次の起動は実EEの直動だけをリミットまで引き込みます。homing_only:=trueにより、サーボ校正値に関係なく原点確認後に全出力を停止し、ロール・フックの初期化やアーム起動へ進みません。

```bash
ros2 run end_effector_pkg auto_harvest --ros-args -p backend:=serial -p keyboard_enabled:=false -p homing_only:=true
```

`c`は不要です。停止するには`Ctrl-C`を押します。原点復帰中に止めるとPico出力を停止します。エラー時は原因を解消してノードを再起動します。通常の全体起動では、Picoのサーボパルス設定とYAMLを一致させてください。homing_only:=trueはサーボパルスの一致確認を省きますが、サーボは1500µs停止のままで位置指令を送りません。

サーボ端点校正後の全体起動は既存Launchを使います。

```bash
ros2 launch vision_pkg vision_auto_harvest.launch.py backend:=can_mixed synthetic_camera:=false
```

EE用シリアルを自動ノードと手動ノードで同時に開かないでください。停止時にアームのトルクを自動OFFにする変更はありません。

## 状態確認と検証

`/end_effector/auto/state`のJSONに`hardware_profile`、`homing_verified`、`homing`（phase、request_id、limit_open、encoder_sign、error）、`servo_calibrated`、実測値、駆動値、停止理由を出します。

```bash
ros2 topic echo /end_effector/auto/state
```

実機を使わない検証は、Picoに組み込むC++状態機械のネイティブ検証、Pythonプロトコル・模擬原点復帰・旧処理の回帰検証、模擬アーム・合成カメラとの連携で行います。模擬連携で使うサーボ端点1000/3000は検証専用の一時設定です。実機校正値として保存・使用しません。

旧4DC構成の設定・実機ログ調査・検証履歴は[旧構成の記録](README_auto_harvest_legacy_202610.md)に保存しています。

2026-11-12の検証結果: Pythonの原点復帰・通信デコード・旧EE／手動処理の回帰40件成功。実際にPicoへ組み込むC++原点状態機械について、通常検出・チャタリング・初期HIGH・スイッチ異常・無進捗・タイムアウト・停止・millis桁あふれをネイティブ実行で確認しました。RP2350用ファームウェアのPlatformIOビルドとROSパッケージビルドも成功しています。模擬アーム・模擬EE・合成カメラで原点復帰と2サイクルを完了しました（[結果](validation/limit_homing_20261112/auto_harvest_sim_summary.json)）。

2026-11-12の先行する原点復帰確認: M2論理方向をGP13引込み／GP12押出しに補正したファームウェアをPico 2 W（シリアル`A437E4B324D4447A`）へ書き込み、フラッシュ照合OKを確認しました。`homing_only:=true`で直動の原点復帰だけを実行し、約1.6秒でHOME=DONE、LIMIT作動、ENC4=0、全PWM=0、サーボ1500µsを確認しました。この段階ではフック・アームへの動作指令は出していません。

同日のサーボ修正後の実機確認: 同じPicoで1600µs／1350µsの出力とFBの増減を確認しました。サーボ以外の駆動指令を禁止した試験で、復帰用の制御経路では開1900→閉3705→開1900、初期化用の制御経路では閉3705→開1900を実行しました。停止後のFBは順に1953・3764・1914・3736・1940となり、すべて既存の許容差±70以内でした。最後はFB1940、1500µs、全PWM=0で停止しています。アーム、直動、ロールは動かしていません。果実の把持力・収穫成功・アームと連動した収穫シーケンスはこのサーボ試験の確認範囲に含みません。ログと結果はワークスペースの[検証記録](../../artifacts/servo_direction_20261112/summary.json)に保存しています。

同日の手先カメラ単独・ロール修正の確認では、EEロールのみで初期化の制御経路を使用し、POT1目標2000→1900に対する停止後の値が2056→1860でした。その後、実機の原点復帰・EE初期化から`WAIT_ARM_STARTUP`まで確認し、さらにiPad用Launchで`APPROACH`へ進んだことを確認しました。記録はワークスペースの`artifacts/hand_only_ee_dxl_20261112/`にあります。
