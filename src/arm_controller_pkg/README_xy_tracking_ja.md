# XY連続追従・円軌道デモ

2026-11-17: D405画像の上下画素誤差に対するZ補正を追加しました。
画像高の1/10以上で開始、1/20以内で停止します。深度はZ判定に使いません。
`z_tracking_enabled:=true` で有効になり、Z動作中はq1/q2/q3を保持します。
新しいPicoファームウェア、明示的な原点復帰、設定・停止・検証結果は
[画像追従のZ補正手順](../vision_pkg/README_z_pixel_tracking_ja.md)を参照してください。
本書の円デモおよびZ無効時の動作は従来どおりです。

## 調査した既存構成

- ROS 2 Humble。収穫ノードは`ArmService`の同期コールバックからIK、Z軸処理、Dynamixel到達待ちを順に実行します。Z軸原点復帰やPico通信にも待ち時間があります。そのため、このコールバックを10 Hz追従に流用しません。
- 既存IKの座標はmm/degreeです。FKは`x=L1 cos(q1)-L2 sin(q1)+L3 cos(q1+q2)+L4 cos(q1+q2+q3)`、`y=L1 sin(q1)+L2 cos(q1)+L3 sin(q1+q2)+L4 sin(q1+q2+q3)`で、手先角度は`q1+q2+q3`。`Link1,Link2`は第1関節の固定直交オフセットとして式に入っています。2026-11-16の機構変更に合わせた現在設定値は270, 0, 275, 75 mmです。`ik_solver_arm3`は`Link2=0`にも対応します。CAN混成経路の＋Y直線基準は関節角`[90°,0°,0°]`で、校正・微調整方法は`README_can_joint_migration_ja.md`を参照してください。
- IK関節はDynamixel ID 1, 3, 5。既存モータ層は各関節にID 2, 4を対にし、目標角を`[a, 360-a, b, 360-b, c]`として送ります。IK角から関節代表モーター角への既存変換は`[q1+90°, q2+90°, q3+180°]`です。設定済みDynamixel範囲をこのオフセットでIK範囲に変換します。2軸の方向、機構上のゼロ、対の伝達方向は設定とコード上の対応です。実機の機械的安全範囲を保証する校正値ではありません。
- Z軸は平面アームのIKとは別のPico制御です。Z補正無効時はZ軸を初期化・移動せず、目標PoseStampedのzは設定した固定平面と一致する必要があります。Z補正有効時のzは現在のZパルス位置に一致させ、上下補正は専用トピックから要求します。
- 既存コードには、以前の作業で変更されたファイルが含まれていました。指定された`arm_controller.py`、`ik_solver_arm2.py`、`motor_controller_module_5motor.py`は編集していません。追加の`ik_solver_arm3.py`と専用追従/モータ層で実装しています。

## インターフェースと制御

- `/arm_xy/goal` (`geometry_msgs/msg/PoseStamped`): m/rad相当、`frame_id=arm_base`。XY位置と平面内yawのみ対応します。roll/pitch、別frame、ゼロ/古い/未来すぎるstamp、NaN/Inf、固定Z以外を拒否します。TF変換は行わないためframeは一致させてください。
- `/arm_xy/actual` (`PoseStamped`): FKから計算した実測または模擬の手先位置・姿勢。
- `/arm_xy/joints` (`Float64MultiArray`): 現在の3関節角(rad)。円軌道事前確認用。
- `/arm_xy/error` (`Float64MultiArray`): `[x誤差(m), y誤差(m), yaw誤差(rad), IK反復回数]`。
- `/arm_xy/ready` (`Bool`, reliable/transient local): 初期姿勢への実測到達後にtrue。初期化中はfalseで、trackerは外部目標を破棄し、円ノードは目標を発行しません。
- goal subscriberは深さ1で最新目標のみを保持します。周期タイマーは既定10 Hz、1回のタイマー内で状態読取・IK・制限付き関節目標送信を行います。受信は別callback groupで動き、モーターI/Oは周期処理だけから行います。
- 速度/加速度制限は`max_joint_velocity_rad_s`と`max_joint_acceleration_rad_s2`です。到達可能な更新は制限内で進めます。目標が0.5秒途絶えた場合とIK失敗時は、測定した現在関節角を一度だけ再指令して位置保持へ移ります。通信失敗時は送信不能なので復旧まで新規指令を出しません。いずれもトルクは切りません。
- 指標ログは5秒ごとに、周期処理所要時間、直近最大50周期の平均間隔、目標経過時間、100 ms超過回数を出します。目標発行10 Hzは円ノードの周期であり、周期制御10 Hz、Dynamixelゴール送信10 Hz、モーター内部制御周期は別です。
- 初期化所要時間は`XY tracking ready after ...s initialization`として別に記録し、追従周期の統計はその時点から開始します。目標経過時間は受信時刻と計測時の単調時計で計算します。

## 模擬環境で実行

ワークスペースルートで:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg
source install/setup.bash
ros2 launch arm_controller_pkg xy_circle_demo.launch.py
```

既定は模擬バックエンド、設定した初期姿勢への移動、半径0.05 m、周期20秒、10 Hz、連続周回です。`revolutions:=0`はCtrl-Cまで継続、`revolutions:=1`は一周、`revolutions:=3`は三周です。中心は初期化後の実測位置から初期位相分だけ引いて計算するため、最初の円目標に半径分の位置ジャンプを作りません。円開始前に円周144点と必要な接近区間のIKを確認し、制限内に解けない軌道は目標を発行しません。

停止は端末で`Ctrl-C`です。トルクは維持します。目標ノードだけを停止した場合、trackerはタイムアウト後の測定位置を一度だけ指令して保持します。状態確認は別端末から:

```bash
ros2 topic echo /arm_xy/goal
ros2 topic echo /arm_xy/actual
ros2 topic echo /arm_xy/error
ros2 topic echo /arm_xy/ready
```

軌道設定例:

```bash
ros2 launch arm_controller_pkg xy_circle_demo.launch.py radius:=0.05 period:=30.0 publish_rate:=10.0 revolutions:=2 direction:=-1.0
```

`center_mode:=configured`では`center_x`, `center_y`を円中心(m)として使い、現在位置から円開始点まで`approach_duration`秒で補間します。初期値は3秒です。開始位置から開始する場合は既定の`current_start`を使用します。`follow_start_yaw`既定trueで現在yawを全周固定します。

## 実機設定と制御権

`config/xy_robot_config.yaml`のU2D2シリアル番号、ボーレート、プロトコル、ID、位置範囲、profile設定、通信timeoutを実機確認値に合わせてください。launchの`backend`引数が設定ファイルより優先されるため、実機は次のように明示して起動します。

```bash
source install/setup.bash
ros2 launch arm_controller_pkg xy_circle_demo.launch.py backend:=dynamixel
```

**この起動でトルクがONになり、設定した初期姿勢へ移動します。** 既定の`startup_mode:=configured`は、各モーターの直近の実測位置を保持目標として書き込み、通信応答を確認してOFFのモーターをONにします。全5台のONを読み戻して確認します。成功ログは`Dynamixel torque ON verified: IDs [1, 2, 3, 4, 5]; startup_mode=configured`です。手で支えている間の数tickの位置変化を理由に起動を拒否するGoal Positionの厳密一致・位置不変チェックは、このモードでは使用しません。モード・位置範囲・通信エラー・トルクON確認は維持します。

初期化は既存の`motor_controller_module_5motor.py`の`enable_torque()`→`init_pos()`と、`module/set_params.yaml`の`DXL_HOME_ANGLE: [95,260,105]`を参考にしています。新しい周期処理から次の順番で移動します。

1. ホーム関節角 `[5°,170°,-75°]`（代表モーター角から`[90°,90°,180°]`を引いた値）。
2. デモ開始関節角 `[5°,160°,-65°]`。第2関節を10°開き、第3関節を補正して既存の手先角度100°を保持。
3. 実測到達を確認し、`/arm_xy/ready=true`を通知。新しい実測位置で円を事前確認して発行。

折り畳んだホーム姿勢からの既定50 mm円はIK確認を通らなかったため、全周のIKが通る上記デモ開始姿勢を追加しました。円の中心はデモ開始後の実測位置から決まります。初期化中もZ軸は動かしません。関節間を5次補間で動かし、ソフトウェア指令の速度・加速度を追従用の制限以下にします。各区間は最低3秒、既定の到達許容差は各関節1°・3周期連続、タイムアウトは各区間60秒です。タイマーで到達を確認するため、到達待ちでコールバックを占有しません。初期化に失敗すると円は開始せず、自動再試行もしません。初期化経路に衝突回避はありません。

設定は`config/xy_robot_config.yaml`の`startup`に集約しています。`initial_joints_deg`は模擬モーターの起動時状態で、実機に設定する姿勢は`startup.home_joints_deg`と`startup.demo_joints_deg`です。現在位置からそのまま円を始める従来の動作は`startup_mode:=current`で選択できます。この場合は以下の厳密保持確認を使用します。

```bash
# 初期姿勢へ移動して連続周回（既定）
ros2 launch arm_controller_pkg xy_circle_demo.launch.py backend:=dynamixel
# 初期姿勢へ移動して一周
ros2 launch arm_controller_pkg xy_circle_demo.launch.py backend:=dynamixel revolutions:=1
# 現在位置から開始、厳密な保持確認あり
ros2 launch arm_controller_pkg xy_circle_demo.launch.py backend:=dynamixel startup_mode:=current
```

使用する制御テーブルはTorque Enable=64、Operating Mode=11、Drive Mode=10です。全台Position Control Mode=3、Drive ModeのTorque On by Goal Updateビット=0を要求し、異なる場合は理由を表示して停止します。モードを自動変更しません。起動位置が設定範囲外の場合もトルクを有効化しません。初期化失敗時は追従と自動再試行を止め、原因の解消後に再起動が必要です。一部のトルク有効化後に失敗する可能性もあるため、失敗時やCtrl-Cで自動的にトルクOFFにはしません。レジスタ定義は実際の型番のマニュアルで確認してください（参考: [ROBOTIS XM540-W270](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/)）。実機の保持・始動動作は未検証です。

### `startup_mode:=current`の厳密保持確認

これは「現在位置への到達失敗」ではなく、**保持目標としてGoal Positionに送信した値と、Goal Positionレジスタから読み戻した値の不一致**です。この段階では初期化によるトルクON指令はまだ出していません。先行する起動でONだったモーターはそのままです。

起動時だけ、再読取りを5 ms間隔、`startup_readback_timeout_ms`（既定100 ms）の期限まで行います。期限を過ぎたら次の再読取りを開始しませんが、開始済みSDK通信や診断読取りの時間は別途かかります。通常の10 Hz追従中にはこの待ちを行いません。

実機ログで`expected=2180, readbacks=2181, present_now=2181, torque=0`を確認しました。初期の現在位置と後の現在位置が1 tick異なり、Goal Positionが後の現在位置と一致する状態を、以前の厳密一致判定が拒否していました。ファームウェアが目標を書き換えた理由や、エンコーダの揺れと実際の微小移動の区別までは、このログだけでは確定できません。

現在は`startup_hold_tolerance_ticks: 1`（設定可能値0または1）です。送信値との差が1 tick以内の場合に限り、現在位置・トルク状態・Goal Positionを再読取りし、**トルクOFFかつGoal Positionの前後2回の読取りが新しい現在位置と一致する場合**も、現在位置保持として受け入れます。新しい値が設定位置範囲内であることも必須です。この場合は`startup hold confirmed at current position`に送信値・現在値・差を表示します。設定を0にすると従来の完全一致条件になります。

全台の保持目標設定後、最初のトルクON指令を出す前に、全5台のGoal Positionと現在位置を再読取りします。それぞれが初期位置から許容tick以内で、目標と現在位置の差も許容tick以内かつ設定範囲内であることを確認します。2 tick以上の移動や離れた目標を受け入れる処理ではありません。レジスタ読取りは順次処理なので、確認後の外力による移動や別プロセスの書込みまで防ぐものではありません。

再読取りで送信値と完全一致した場合は`hold goal confirmed after re-read`に観測値を記録します。上記条件を満たさない不一致では`expected`（送信tick）、`readbacks`（Goal Position履歴）、`present_now`（診断時の現在位置tick）、`torque`を表示して停止します。診断値も同時刻のスナップショットではありません。

Profile Velocity/Accelerationのレジスタ値は起動時に一度設定し、追従中はゴール位置を10 Hzで更新します。ゴール更新ごとにアクチュエーター内部の位置profileが再計画される可能性がありますが、Dynamixelへ接続して挙動を測定していません。型番・profile単位・機械限界はDynamixel Wizardと機構資料で確認が必要です。

追従ノードは`/arm_service`と`/arm_service_d435`がROSグラフに見える間、新しい追従指令を抑止します。ただし既存ノードは共有ロックを使わないため、サービス起動と検知の間の競合までは排除できません。模擬/実機のいずれも収穫ノードや別のモーター制御プロセスを停止してから追従ノードを起動してください。追従ノード自身はZ軸サービスを呼びません。

## IKと検証の境界

新IKはDLS、角度周期差分、関節範囲、1反復あたりの関節更新上限を使います。成功時のみ収束を返し、結果に失敗理由・残差・反復数を含めます。ヤコビアンはFK式の解析微分です。事前軌道確認は位置/関節制限のみを見ており、自己衝突・周辺物との衝突や安全性を保証しません。

模擬で確認できるのはメッセージ経路、最新値置換、IK/FK整合、軌道計算、制限器、タイムアウト状態遷移、周期負荷です。実機でのみ確認できるのはDynamixelのタイムアウト/応答、profileの実際の速度挙動、対モーターの向き・ゼロ点、負荷下の追従と振動、ブレーキ/保持特性、機械的衝突余裕です。模擬計測値を実機の10 Hz性能保証として扱いません。

### トルク初期化修正の検証（2026-10-11）

#### 設定姿勢への初期化・連続周回（最新）

- `colcon build --symlink-install --packages-select arm_controller_pkg`: 成功。
- `PYTHONPATH=src/arm_controller_pkg:$PYTHONPATH python3 -m pytest -q src/arm_controller_pkg/test/test_stream_torque.py src/arm_controller_pkg/test/test_joint_startup.py`: 54件成功。従来の厳密保持モードに加え、手で支えた位置変化を模擬した起動、通信エラー・範囲外の拒否、補間速度・加速度、到達タイムアウト、初期化前の円目標抑止、周回数0/1/2、デモ開始姿勢から両方向の全周IKを確認。
- 模擬バックエンドで25秒間実行。ホーム→デモ開始姿勢の実測到達確認後、約13.6秒でready。初期化中の円目標発行0件。周期2秒・周回数0で、113件の目標を11.202秒にわたり発行し、4周経過後も発行が続くことを確認。発行間隔は平均100.022 ms、最大102.365 ms。
- `backend:=sim startup_mode:=current period:=2.0 revolutions:=1`のlaunchでも一周で目標発行終了、SIGINTで両ノードが正常終了することを確認。
- 追従ログは処理3.5/4.9 ms、平均周期100.02/100.00 ms、平均10.00 Hz、最大周期102.77/100.69 ms、目標経過時間91.9/92.5 ms、100 ms超過累計25/48回。初期化時間は追従統計から分離しました。周期2秒は周回継続を短時間で検証するための設定で、実機向け推奨値や追従精度の保証ではありません。
- 実行環境のUDPソケット制限警告は出ましたが、同一プロセスのROSトピック受信と状態遷移を検証できました。実機の初期化・到達・保持動作は未検証です。今回の変更は指定された既存3ファイルには加えていません。

#### 以前の厳密保持モードの検証履歴

- `colcon build --symlink-install --packages-select arm_controller_pkg`: 成功。
- `PYTHONPATH=src/arm_controller_pkg:$PYTHONPATH python3 -m pytest -q src/arm_controller_pkg/test/test_stream_torque.py`: 16件成功。模擬レジスタで全保持目標の設定・読戻しがON指令に先行すること、既にONのモーターを切り替えないこと、設定範囲/モード/通信/読戻し異常の扱い、競合時の起動抑止、初期化失敗後に再試行しないこと、終了時にOFFを書かないことを確認しました。SDKや実機ポートは使用していません。
- `backend:=sim period:=3.0`で円目標の発行完了とSIGINTによる正常終了を確認。5秒時点のログは処理1.4 ms、平均周期100.00 ms、最大100.55 ms、平均10.00 Hz、100 ms超過22回。目標終了後の目標経過時間は1839.9 msです。実行環境のUDPソケット制限警告は出ましたが、同一launch内のトピック受信と円の事前確認・発行は完了しました。終了コード124は検証用timeoutによる停止です。
- 実機のトルク有効化・保持・円運動は自動実行していません。実機でトルクONの読み戻しログと実際の保持を確認してください。

読戻し不一致への追加修正では、模擬レジスタで遅れて完全一致する場合、1 tickの不一致が継続する場合、診断読取りが失敗する場合、設定値が不正な場合も含む24件のテストが成功しました。パッケージの再ビルドも成功しました。これは実機の不一致原因を再現・確定したものではありません。

さらに実機から報告された`2180→2181, torque=0`を再現するテストを追加し、39件が成功しました。±1 tickで現在位置と一致する場合の受入れ、2 tick以上・トルクON時の不一致・厳密設定0・現在位置と異なる目標・設定範囲を跨ぐ1 tick・トルクON直前の移動の拒否を確認しています。`backend:=sim period:=3.0`の目標発行完了とSIGINTでの正常終了も確認しました（UDPソケット制限の警告は前回同様）。実機でのトルクON・移動確認は行っていません。


## D405画像追従との連携（2026-10-12更新）

画像横方向の中心合わせと初回距離の維持は
[vision_pkgの手順](../vision_pkg/README_realtime_ja.md)を参照してください。
trackerの通常追従指令は `modules/yaw_joint_limiter.py` で生成します。
各関節の速度を個別にクリップする処理を、速度・加速度・可動範囲と関節速度和を同時に扱う処理へ変更しました。
固定yawのときは各周期の送信指令でもyawを保ちます。
前回送信指令と実測値を分け、IKは実測値から解きます。
`/arm_xy/diagnostics` の `commanded_yaw_error` と `measured_yaw_error` は別々に確認してください。
`/arm_xy/command_joints` は送信に成功した関節指令（rad）、`/arm_xy/hold` は一時保持要求です。
通信故障は自動再試行せずラッチします。トルクOFFは追加していません。


## EE操作からの収穫サイクル

`vision_xy_tracking.launch.py` は `harvest_cycle_enabled:=true` が既定です。
接近完了で `HARVEST_HOLD`、EE端末の `r` で `startup.demo_joints_deg` へ復帰、
`RETURNED` で待機し、EE端末の `n` で次の接近を開始します。
既存tracker内部の `modules/harvest_cycle.py` が制御権を管理し、ノードは増設していません。
保持・復帰中は画像目標を受け付けません。詳細は
[vision_pkgの収穫サイクル手順](../vision_pkg/README_realtime_ja.md)を参照してください。
単独trackerと円デモは収穫サイクル無効が既定です。
