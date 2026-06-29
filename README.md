# Hibikino-Toms/hibikino_toms_wsにプログラムの変更を反映する場合 #
ワークスペース内（hibikino_toms_ws）でコードを変更した際、以下の３つのコマンドを実行するだけでgithubに更新を反映できる。
```
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
