# Hibikino-Toms/hibikino_toms_wsにプログラムの変更を反映する場合 #
ワークスペース内（hibikino_toms_ws）でコードを変更した際、以下の３つのコマンドを実行するだけでgithubに更新を反映できる。
```
cd ~/hibikino_toms_ws/
git add .
git commit -m "変更内容のメモ"
git push origin main
```



# デモ起動手順 #
## 動作のみデモ ##
```
cd ~/hibikino_toms_ws/
source install/setup.bash
ros2 launch harvest_task_pkg crawler_auto_harvest.launch.py
```

## ipad映像ストリーミングのセットアップ ##
```
sudo systemctl mask wpa_supplicant
sudo systemctl stop wpa_supplicant
sudo systemctl unmask hostapd dnsmasq
sudo systemctl enable hostapd dnsmasq

sudo reboot # 再起動コマンド

sudo systemctl status hostapd dnsmasq
（activeでOK）
sudo systemctl status wpa_supplicant
（inactiveでOK）
sudo ip addr add 192.168.249.1/24 dev wlan0
```
(SSID : toms_jetson_AP, password : ylab_ipad_stream)
```
cd
cd hibikino_toms_ws/
source install/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml 
```
```
cd ~/webui
python3 -m http.server 8080
```
検索エンジンの入力欄に以下を入力する．
（ここはjetson側で見ても良いし，ipadやスマホのsafariやgoogleでも良いよ）
192.168.249.1:8080
(ipad_img_move_rev3.htmlが最新)

ここでロボットの非常停止を解除
```
cd
cd ~/hibikino_toms_ws/
source install/setup.bash
ros2 launch harvest_task_pkg ipad_demo_rev2.launch.py 
```
```
cd
cd ~/hibikino_toms_ws/
source install/setup.bash
ros2 launch cart_controller_pkg crawler_control.launch.py 
```
### 終了手順 ###
プログラム類をctrl+c
```
sudo systemctl stop hostapd dnsmasq
sudo systemctl mask hostapd dnsmasq
sudo systemctl unmask wpa_supplicant
sudo systemctl enable wpa_supplicant
```
```
sudo reboot # 再起動コマンド
```


## デバッグ用　Ipad用プログラムでのプロセス呼び出し ##
### 1. トマト検出を実行（ターゲット座標を記憶させる） ###
```
ros2 service call /detect_tomato toms_msg/srv/DetectTomato "{}"
```
### 2. 収穫を実行（アーム移動 → 吸引 → カット → ボックスへ移動　→ アームEE初期化） ###
```
ros2 service call /harvest_tomato toms_msg/srv/HarvestTomato "{}"
```
## カメラがbusy状態になった時用 ##
```
pkill -9 -f cam_pub_service
pkill -9 -f vision_service
```

# 自律移動実行手順（cdやsourceは割愛） #
## SLAM地図作成 ##
クローラを起動（teleopで移動可能）
```
ros2 launch cart_controller_pkg crawler_control.launch.py
```
LiDARを起動
```
ros2 launch livox_ros_driver2 rviz_MID360_launch.py
```
以下のslam起動コマンドによりrvizが起動する
```
ros2 launch my_nav_package slam.launch.py
```
クローラをteleopで移動させると、地図が生成され、以下のコマンドで保存（pgmとyamlが指定のパスに保存される）
```
ros2 run nav2_map_server map_saver_cli -f ~/hibikino_toms_ws/src/my_nav_package/maps/maps
```
地図保存後は、slamのlaunchは停止して良い
## 保存した地図を用いてNavigationで自律移動 ##
クローラを起動（teleopで移動可能）（地図作成時から起動している場合は再度起動したままで良い）
```
ros2 launch cart_controller_pkg crawler_control.launch.py
```
LiDARを起動（地図作成時から起動している場合は再度起動したままで良い）
```
ros2 launch livox_ros_driver2 rviz_MID360_launch.py
```
harvest launchを起動
```
ros2 launch harvest_task_pkg crawler_auto_harvest.launch.py
```
cmd_velの制御ノード起動
```
ros2 run crawler_robot_pkg crawler_control_vel 
```
以下のコマンドでNavigationを起動すると、rvizが起動してslamで保存したマップが出力される（マップのパスは/home/ylab/hibikino_toms_ws/src/my_nav_package/maps/maps.yamlで指定している）
```
ros2 launch my_nav_package navigation.launch.py
```
rvizの上部メニューにある「2D Pose Estimate」をクリック  
↓  
マップ上でロボットの姿勢を設定（設定するとリアルタイムのLiDARセンサ情報がrviz上に出力される）  
↓  
rvizの上部メニューにある「2D Goal Pose」をクリック  
↓  
マップ上でゴールのロボット姿勢を設定（設定すると移動経路を表す緑色の線が出力されて移動が開始する）
