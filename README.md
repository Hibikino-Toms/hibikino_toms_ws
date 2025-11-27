## 自律移動起動方法（途中まで） ##
### 1. クローラーを起動 ###
```
ros2 launch cart_controller_pkg crawler_control.launch.py
```
起動するとキーボードで操作できるteleopがポップアップする
ロボットの操作方法はteleopと同じ（カーソルをそのポップアップに合わせないと動かない）
このlaunchファイルを起動すると、/odomトピックもパブリッシュされる

### 2. LiDARのドライバを起動 ###
```
ros2 launch livox_ros_driver2 rviz_MID360_launch.py
```
起動するとrvizが起動し、生データを確認できる

### 3. SLAMを起動 ###
```
ros2 launch my_nav_package slam.launch.py
```
起動後、rvizの画面で、
Global OptionsのFixed Frameをmapに変更
→Add、By topicからMapを追加
→AddからTFを追加（これによりホームポジション、ロボット、LiDARのTFが確認可能）
以上により、理論上は環境地図の作成が可能に

### 現状 ###
SLAMのlaunchファイルを起動した瞬間のマッピングはできるが、ロボットを動かしてもマップが更新されない
原因は、移動時にLiDARの情報は変化するが、TF（odomによる）が追いついておらず、時間的なずれがあるためにデータを捨ててしまっていることが考えられる
その対策として、configファイル内のslam_params.yamlファイルのtransform_timeoutパラメータを変更し、LiDARデータとTFの時間差の許容をデフォルトの0.2sから1.0sにした
しかし、yamlをうまく読み込めていないのかyamlファイルのパラメータを反映できていない
パスが通っていることは確認できており、そのほかの原因がわからない
クリーンビルドし、再ビルドしたが解消されず
