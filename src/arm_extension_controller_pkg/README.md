# アーム延長：距離指定クライアント／サービス（ROS 2）

参考のcrawler_client_node / crawler_service_nodeと同様に、クライアントが要求し、
サービスがUSBでPicoへ送信します。クローラー用の `toms_msg` や固定パルス値は使いません。
サービス定義も同じパッケージに含めるため、**1パッケージ**で構成しています。

## 何ができるか

- `10` → **今の位置から**10mm伸ばす（R、GP15）。
- `-10` → 今の位置から10mm戻す（F、GP14）。
- `home` → F方向へ戻し、原点スイッチが押されたら減速停止して0mmに設定。
- `zero` → 停止した原点を手動で0mmに設定。
- `stop` → 停止要求。物理的な非常停止の代わりではありません。
- 動作後、成功/失敗・今回の推定移動量・原点からの推定位置を返します。

`10`を2回送ると原点から20mmです。「原点から10mmへ行く」という絶対位置指定ではありません。
原点未設定、範囲外、同時の移動要求は拒否します。移動はPico側でパルスを数えて停止します。

## 大切な制約

これは既存ハードウェア用の**低速・短距離の試験コード**です。
SPEED信号は単相で、実際の方向を検出できません。方向は指令から仮定します。
モジュール2・15歯、減速比1:50、内部モーター1回転12パルスを前提に、
1パルスを約0.1570796mmとして計算しています。部品を変えた場合はArduino側を修正します。

**目標パルスで停止指令を出す方式で、減速中のオーバーランをなくす位置サーボではありません。**
指定10mmでも、実際は減速分だけ多く動く場合があります。停止後の推定移動量を返します。
末尾の `TARGET_STOP_COMMAND` は「目標に達して停止指令を出した」の意味で、
指定距離に正確に止まったことを保証しません。

伸び側リミットは未搭載です。`max_position_mm` のソフト制限だけで衝突・落下防止を
保証できません。実機では減速距離に余裕を取り、機械的な脱落防止、伸び側リミット、
PCとは別の停止手段を用意してください。最初はラックから切り離した固定済みモーターで確認します。
今のブレッドボードは試作用で、ロボットの常設回路として扱わないでください。

## フォルダー

```text
arm_extension_controller_pkg/
  CMakeLists.txt
  package.xml
  srv/MoveArm.srv
  scripts/arm_client_node.py
  scripts/arm_service_node.py
  scripts/arm_driver.py         # USB通信とシミュレーション
  firmware/arm_extension_motor/arm_extension_motor.ino
  test/test_arm_driver.py
```

独自srvを生成するためビルド形式は `ament_cmake` です。ノード本体はPythonです。
固定の `/home/ylab/...` はコードに入れていません。

## 1. ROS 2側でビルド（Ubuntu / bash）

ROS 2とcolconが導入済みのPCを想定します。まずこのフォルダーを
`hibikino_toms_ws/src/arm_extension_controller_pkg` にコピーします。

```bash
source /opt/ros/humble/setup.bash
cd ~/hibikino_toms_ws
rosdep install --from-paths src/arm_extension_controller_pkg --ignore-src -r -y
colcon build --packages-select arm_extension_controller_pkg --symlink-install
source install/setup.bash
```

`humble`とワークスペースの場所は学校の環境に合わせて変更してください。
WindowsのPowerShellでは上記bashコマンドをそのまま実行しません。

## 2. まず実機を動かさず試す

端末A：

```bash
cd ~/hibikino_toms_ws
source install/setup.bash
ros2 run arm_extension_controller_pkg arm_service_node --ros-args \
  -p simulate:=true -p max_position_mm:=100.0
```

`100.0` はシミュレーション用の例で、実機の可動域を示す値ではありません。

端末B：

```bash
cd ~/hibikino_toms_ws
source install/setup.bash
ros2 run arm_extension_controller_pkg arm_client_node
```

クライアントに `zero` → 確認に `yes` → `10` → `-5` と入力します。
推定位置は0 → 10 → 5mmとなります。シミュレーションではUSBを開かず、モーターは動きません。

## 3. 実機へ切り替える準備

1. 24V電源をOFFにし、既存のキーボード操作画面・シリアルモニターを閉じます。
2. Arduino IDEで同梱の `arm_extension_motor.ino` を開き、Pico 2 Wにアップロードします。
   既存のキーボード用スケッチのままでは、このサービスとは通信できません。
   前のキーボード用ファイルは変更していません。戻す場合はそちらを再アップロードします。
3. GP14・15のC1815回路、GP16の原点COM–NC、GP17のSPEED変換回路は現状のままです。
   モーターは単体で固定し、24V電源は最初OFFのままにします。
4. USBデバイスを確認します（クローラーのPicoと取り違えない）。

```bash
python3 -m serial.tools.list_ports -v
```

実機起動例（値は実測して決めた安全範囲に置き換えてください）：

```bash
ros2 run arm_extension_controller_pkg arm_service_node --ros-args \
  -p simulate:=false -p port:=/dev/ttyACM0 \
  -p max_position_mm:=100.0 -p max_move_mm:=5.0
```

**100mmは例です。実機で確認せず採用しないでください。**
`max_position_mm` は原点からの使用上限、`max_move_mm` は1回の要求の上限です。
両方とも停止後の余裕を確保して設定します。max_position_mmの初期値0では実機起動を拒否します。
必要なら `port` の代わりに `-p serial_number:=PICOの実際のシリアル番号` で選択できます。
USBアクセス権がなければ学校のPC管理方法に従って設定してください。

## 4. 原点と移動

- 起動後10秒以上、完全に停止していることを確認。
- **実際にアームが初期位置でスイッチを押している**こと、断線がないことを確認。
- クライアントで `zero` → `yes`。原点設定はモーターを回しません。
- モーター単体の試験中にスイッチを手で押して設定する場合、その位置は仮原点です。
- 設定後、低速・小さい数値から試験し、定規で実移動距離と比較してください。
- Pico再起動、断線・パルス異常後は原点を再設定してください。
- 1回の駆動は最大10秒、停止後は10秒待って結果を返します。
  その間も次の移動は受け付けません。PCが応答待ちでも勝手に再送しないでください。
- キーボード操作アプリとROSサービスは同時に同じUSBを使用できません。

## 停止

サービス側端末のCtrl+Cは停止指令を送り、通信断でもPicoが300msで停止指令を出します。
クライアントの終了だけで物理停止したと判断しないでください。
別端末からの停止要求：

```bash
ros2 service call /arm_extension/control arm_extension_controller_pkg/srv/MoveArm \
  "{command: stop, distance_mm: 0.0}"
```

停止要求への成功応答は「要求を受けた」という意味で、機械の停止完了ではありません。
通信断・パルスなし・タイムアウト・原点スイッチ到達などでは失敗応答にします。
NC配線では「押された」と「断線」を電気的に区別できないため、原点設定は目視確認が必要です。

## ROSなしのテスト

```bash
cd arm_extension_controller_pkg
python3 -m unittest discover -s test -v
```

テストでは実機・USB・モーターに接続しません。
作成時にPythonの6件のテスト・構文・package.xmlを確認し、Pico 2 W用ヘッダーを使った
Arduinoスケッチの文法確認も通っています。
この作成環境にはROS 2がないため、ROSインターフェース生成とcolconビルド、
Picoプログラムの最終リンク・アップロード、実機での停止精度は未確認です。
実機運転前に学校のROS環境でビルド・シミュレーション・停止動作を順に確認してください。

参考：ROS 2公式の独自サービス定義の構成
https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.rst
