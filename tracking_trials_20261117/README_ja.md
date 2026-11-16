# トマト接近の実機改良・ROSBAG記録（2026-11-17）

Gitには手順書と検証用Pythonコードを保存しています。ROSBAG・実測JSON・画像・実行ログはローカル保存のみです。この文書内のそれらへのリンクは、実験PCに記録がある場合に参照できます。

## 現在のlaunch設定（統合後）

この手順の `vision_xy_tracking.launch.py` は、**[src/vision_pkg/config/vision_xy_tracking.yaml](../src/vision_pkg/config/vision_xy_tracking.yaml)** の1ファイルを読みます。アーム・カメラ・Z・到達判定・制御周期の設定をここで変更してください。各試行フォルダのYAMLは当時の記録で、起動時には参照しません。

- 初期角度: `startup`、リンク・制限: `ik_solver_params` / `joint_limits_deg`
- モーター校正・通信: `can_mixed_backend` / `dxl_params`
- 周期・速度・加速度・IK補正分解能: `tracking`
- 接近完了の許容差: `harvest_cycle`
- 画素オフセット・目標距離・接近速度: `target` / `target.image_approach`
- Zの画素幅・移動量・速度: `z_tracking`
- 起動オプション: `launch`。コマンドラインで明示した値が優先

起動コマンドはこれまでどおりです。別ファイルを使うときは `config_file:=/絶対パス/vision_xy_tracking.yaml` を追加できます。旧3ファイルは他のlaunch・単独起動用で、このlaunchへ自動同期しません。[設定項目の説明](../src/vision_pkg/README_realtime_ja.md#このlaunchの設定ファイル統合済み)

## 結果

q1=RMD X8 ID0、q2=RMD X6 ID1、q3=Dynamixel ID5、D405、Z_TRACKING_V1の実機で実施しました。最終試行では、初期姿勢から約263mm先の対象へ接近し、既存の到達判定で `HARVEST_HOLD / reason=approach_complete / hold_ready=true` になりました。EEは動かしていません。終了時は各ノード正常終了、Zもbusy=0・通電保持・異常なしです。

停止後にカメラだけを起動し、8フレームで再確認した値:

| 項目 | 結果 | 既存設定 |
|---|---|---|
| 深度 | 150.1～151.5mm | 目標150mm、到達許容±10mm |
| 横画素誤差 | −13.7～−12.9px | 到達許容±50px、制御デッドバンド±3px |
| 縦画素誤差 | −32.8～−31.9px | Z開始48px、動作後停止24px（480px画像） |
| 到達直前5秒の実測yaw誤差 | 最大0.00660rad（約0.378°） | 到達許容0.1rad |

到達許容差は広げていません。到達許容50pxと画像制御の3pxデッドバンドは別です。自動到達保持が有効なら、3pxまでの中心合わせ完了前でも50px内で停止します。縦誤差は48px未満だったので最終試行ではZを動かしていません。24px以内・画像中央への完全一致を達成したとの扱いはしません。

主な証拠:

- [最終ROSBAG](trial_06_full_arrival/bag/metadata.yaml)、[集計](trial_06_full_arrival/bag_analysis.json)、[実行ログ](trial_06_full_arrival/console.log)
- [接近グラフ](trial_06_full_arrival.png): オレンジの縦線が実際の接近完了通知
- [停止後の画像](final_stopped_scene.jpg)、[停止後8フレームの測定](final_stopped_scene.json)
- [完了条件の照合](completion_audit.json)

## 見つかった原因と変更

1. **Z指令の小数速度受信**: 移動不要の `ZMOVE,201,5,10.000` まで `RANGE_OR_SPEED` で拒否されました。Picoの速度変換を浮動小数の `sscanf` から、末尾検証付きの `strtod` に変更しました。範囲・速度上限・ウォッチドッグを緩めていません。支持確認後に対象Picoへ書き込み、原点復帰と画像Z補正を確認しました。ハッシュは [z_firmware_sha256.txt](z_firmware_sha256.txt)。
2. **深度の350mm境界で停止したままになる**: 350mm以下を一度見た後、約355mmへ戻るたびに確認数が0になっていました。切替開始350mm、切替確認上限380mmのヒステリシスを追加しました。近距離を見た後の深度消失で、画像だけの前進へ戻すことはしません。
3. **小さな補正が消える**: 到達／IK許容差と、追従補正の計算分解能を分離しました。trackerは `solve_tracking()` を使い、数値精度を `tracking_correction_resolution_m=0.0001`、`tracking_correction_resolution_rad=0.001` 以下に制限します。IK許容差を20mmへ広げても、±X/±Yの1mm補正は26～41µmの残差まで計算されました。[回帰結果](small_corrections.json)
4. **接近が遅い**: 画像フレーム間隔だけ先の目標は関節制御の応答に対して短すぎるため、深度制御にも0.25秒の目標先読みを適用しました。速度・加速度・1指令の移動量・関節制限は引き続き適用します。
5. **許容内でも到達判定が出ない**: モーター読取り中に届いた観測の受信時刻が、古い周期開始時刻より後になるため、到達安定時間が繰り返しリセットされていました。ロック内で観測取得後の単調時刻を使います。[時刻回帰結果](arrival_timing_check.json)
6. **リンク寸法**: ユーザー確認に基づき、q2軸→q3軸を200mmから180mmへ変更しました。設定名は `Link3: 180.0` です。`Link2: 0.0` は廃止済みの横オフセットで、そのままです。

`/arm_xy/diagnostics` の `arrival_check` は、観測・IK・epoch・受信鮮度・撮影鮮度・目標鮮度・目標とのFK誤差を示します。`APPROACH`以外では新しい到達判定を行わないため、条件がfalseになっていても保持失敗を意味しません。

## 各試行

| フォルダ | 内容 |
|---|---|
| `trial_01` | 小数速度修正後。Z原点復帰・画素Z補正は動作。XYが350mm境界の深度確認で停止 |
| `trial_02` | 深度ヒステリシス・先読み修正。約400mmから約240mmへ接近後、可到達範囲付近でIK保持 |
| `trial_03` | トマトを手前に移し、q2→q3を180mmへ訂正。150mm付近で継続追従。記録スクリプトがZの内側24pxを追加条件にしていたため、試行summaryは到達完了になっていない。製品のZ開始条件は48px |
| `trial_04_arrival_gate` | 到達保持を有効化。実際は許容内なのにAPPROACHのまま。受信時刻と古い周期開始時刻の比較が原因 |
| `trial_05_arrival_fixed` | 時刻修正後、現在姿勢から `approach_complete` と `hold_ready=true` を確認 |
| `trial_06_full_arrival` | 初期姿勢からの全体再試行でも到達保持を確認。正常終了 |

各試行の `bag/` にROSBAG、`console.log` にROS出力、`observations.jsonl` に確認用の購読値、`bag_analysis.json` に実際のbagをCDRデシリアライズした集計があります。`trial_03`以降には使用したYAMLのコピーもあります。最初の2回は当時の200mmリンクモデルで、現在の180mmモデルと区別してください。

元の遠いトマト位置は、旧200+200mmモデルで計算しても目標150mmでの必要手首半径が約492mmとなり、最大400mmを超えていました。[当時の解析](trial_02/geometry.json)。現在の実寸モデルの最大手首半径は380mmです。許容差を変えても届かない対象位置は存在します。

## 実測周期

最終試行の到達直前5秒:

| 項目 | 測定値 |
|---|---|
| 画像観測周期 | 約14.99fps |
| 制御周期平均／最大 | 100.003ms／101.092ms（平均約10.00Hz） |
| 制御処理時間 平均／最大 | 53.32ms／63.80ms |
| 制御処理時間が100msを超えた回数 | 0回 |
| 周期間隔が厳密に100msを超えた回数 | 26回（最大約1.1msの超過を含む） |
| 撮影からtrackerが扱う目標までの古さ 平均／最大 | 116.85ms／158.61ms |

起動時のモデル読込み・初回推論はこの定常測定から除いています。モーター内部の制御周期は測定していません。ハードリアルタイムの100ms以内を保証する結果ではありません。

## 通常の起動・停止

```bash
cd ~/hibikino_toms_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select arm_controller_pkg vision_pkg
source install/setup.bash
ros2 launch vision_pkg vision_xy_tracking.launch.py \
  backend:=can_mixed startup_mode:=configured \
  synthetic_camera:=false show_window:=true \
  z_tracking_enabled:=true harvest_cycle_enabled:=true
```

現在のこのコマンドでは、Z通信とXYの実測停止を確認し、**起動ごとにZ原点復帰 → Z整定 → XY初期姿勢 → 接近 → 到達保持** の順に動きます。原点確定済みでもZ原点復帰を再実行します。失敗時は保持してXYへ進まず、自動再試行しません。EEノードは起動しません。到達後も連続追従したい場合は `harvest_cycle_enabled:=false` にします。

`startup_mode:=current` はZ自動原点復帰を行いません。このモードでZが `NEEDS_HOME` なら、スイッチ・機構の余裕を確認して別端末から明示要求します:

```bash
ros2 service call /arm_xy/z/home std_srvs/srv/Trigger '{}'
```

これは実際にZを原点復帰させ、完了後に初期姿勢移動・接近が始まります。終了はCtrl-C。停止時の自動トルクOFFは追加していません。異常が出た場合は原因を確認し、状態を整えてから再起動してください。

## 再集計・回帰検証（モーターを動かさない）

```bash
source ~/hibikino_toms_ws/install/setup.bash
cd ~/hibikino_toms_ws
python3 tracking_trials_20261117/analyze_bags.py
python3 tracking_trials_20261117/check_small_corrections.py
python3 tracking_trials_20261117/check_image_handover.py
python3 tracking_trials_20261117/check_arrival_timing.py
```

`run_trial.py` は実機を動かす試行用です。上記の再集計コマンドとは違うため、記録確認だけの目的で実行しないでください。初回書込みの失敗・中間試行の終了時割込みもログに残しています。最終試行では両ノードの正常終了を確認しています。

## 未検証・制約

果実への接触、EE収穫、もぎ取り力、あらゆる対象位置での成功は確認していません。カメラ基準yaw100°は変更していません。移動データによる概算では取付け角に差がある可能性があり、精密な手眼校正の代わりにはなりません。Z位置はパルス数の推定で、独立したエンコーダ実測ではありません。接近動作は衝突回避を実装したものではありません。
