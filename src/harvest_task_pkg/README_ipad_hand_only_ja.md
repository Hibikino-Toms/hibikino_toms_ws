# iPad用・手先カメラ単独の収穫起動

`ipad_demo_rev2_eetest.launch.py`は手先D405（シリアル`230322272057`）だけを使用します。手先映像は`/camera/hand/image/compressed`です。俯瞰映像と俯瞰Depthを使う機能はこのLaunchでは無効です。他のLaunchのビジョンノードは従来どおり俯瞰カメラも使用します。

手先画面で選んだ画素の座標変換は、カメラ内部パラメータと`module/set_params.yaml`の`manual_target_params.FIXED_DEPTH_MM`を使います。これは固定奥行きであり、選択対象までの実測距離ではありません。アーム座標への変換には同ファイルのオフセットも使用します。

手動目標のXYZは、`camera_to_ee` → `ee_to_arm`の順で変換してから`manual_target_params.OFFSET_X_MM/OFFSET_Z_MM`を加算します。`Z_DIFF_EE2ARM`もZ目標に加算されます。旧収穫順序処理の「アームX/Y＋EE相対Z」はこの経路で使いません。ログの`camera`、`ee`、`arm_before`、`arm`で各段階の座標を確認できます。

アームは`ik_solver_params.Link4`の先端を目標へ合わせます。`Link4`にはQ3軸中心からEE作用点までの最終リンク方向の距離を設定し、`X/Y/Z_DIFF_CAM2EE`にはその作用点を原点としたカメラ光学中心の位置を設定します。`X/Y_DIFF_EE2ARM`は撮影時の基準姿勢の作用点のアームXY座標です。リセット後に撮影する設定では`arm_params.INIT_X/Y`と一致させます。`Z_DIFF_EE2ARM`は撮影時のZ軸指令座標で、付け根から測った物理的な高さとは区別します。撮影姿勢を変えた場合はこの固定変換も再調整が必要です。最終リンク方向から横にずれた作用点や追加のカメラ回転には、モデルの追加調整が必要です。

2026-11-13の設定では、カメラより作用点が前方へ130mmなので`Y_DIFF_CAM2EE=-130`です。固定奥行き200mmなら前進量は約70mm、300mmなら約170mmです。`Link4=130`（Q3軸から作用点までの長さ）も同じ値ですが、別の寸法です。

リセット時のZ軸応答は`[2,5]`であり、`Z_DIFF_EE2ARM=5`を撮影基準にします。同姿勢でのEE作用点の実測高さ約120mmをそのまま加算すると、Z軸が余分に115mm動きます。作用点から目標までの相対高さを`dz`とすると、Z軸指令は`5+dz`、目標の物理高さは約`120+dz`です。画素(344,133)、固定奥行き200mm、現在のカメラ高さオフセット60mmでは、記録したカメラ座標から`dz≈110mm`、Z軸指令約115mmとなります。これは設定・ログに基づく計算で、実機到達精度の確認は別途必要です。

YAML変更後はlaunchを終了して再起動し、目標を選び直します。Z目標が0〜450mmの外になる設定は拒否されます。自動補正や範囲内への丸めは行いません。

## 起動

```bash
cd ~/hibikino_toms_ws
source install/setup.bash
ros2 launch harvest_task_pkg ipad_demo_rev2_eetest.launch.py
```

起動するとEEの直動がリミットまで原点復帰し、EEが初期化されます。アーム側はDynamixelのトルクとZ軸ドライバーを有効にします。画面から収穫開始を指示するまで、今回の起動確認では収穫位置への移動指令を送っていません。

```bash
ros2 topic info --verbose /camera/hand/image/compressed
ros2 topic hz /camera/hand/image/compressed
ros2 topic echo /end_effector/auto/state
```

## 2026-11-12の確認

- D405で640×480の画像を取得し、ROSの画像購読とrosbridgeのWebSocket経由でJPEGを受信しました。
- 実機EEロールのPWM100はPOT1の揺れと区別できる進捗がなく、PWM180で移動しました。初期化の目標1900に対し停止後1860を確認しました。設定は`module/set_params.yaml`の`auto_harvest.pwm.min/max.pot1`と`auto_harvest.roll_motor`です。
- Dynamixelの復電前にはID 1〜5で約21.5〜21.7V、Hardware Error Status=1でした。モーターはID 1・2がXM540-W270、ID 3〜5がXM430-W350で、両機種の指定入力電圧は10.0〜14.8Vです（[XM540](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/)、[XM430](https://emanual.robotis.com/docs/en/dxl/x/xm430-w350/)）。約12Vへ是正して再投入した後、統合起動後も11.8〜11.9V・ハードウェア異常0を確認しました。
- 実機LaunchでEEの`APPROACH`、画像受信、アームサービスと手先ピクセル指定サービスの応答を確認しました。果実への移動・把持・収穫成功はこの確認には含みません。

ログはワークスペースの`artifacts/hand_only_ee_dxl_20261112/`にあります。停止後のDynamixelはトルクONで現在位置を保持していました。
