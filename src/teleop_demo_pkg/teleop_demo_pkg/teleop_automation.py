# teleop_automation.py
# ビジョンベースの完全自動収穫ノード (時間制限付き周回・自動帰還機能)

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default
from toms_msg.srv import SuctionCommand, ArmService, VisionService, RailService

from playsound import playsound
import time
import numpy as np
import yaml
import sys

class AnalizeToHarvestNode(Node):
    def __init__(self):
        super().__init__('analyze2harvest_node')
        
        # === YAML読み込みとパラメータ設定 ===
        self.rail_params_loaded = False
        self.return_mode = False
        
        try:
            yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
            params = self.load_yaml(yaml_path)
            
            # 音声設定
            self.VOICE = params.get("ZUNDA_VOICE", False)
            
            # レールパラメータ設定
            rail_p = params["rail_params"]
            self.step_dist_mm = rail_p["DEFAULT_DISTANCE_MOVEMENT"] 
            self.limit_dist_mm = rail_p["DISTANCE_LIMIT_UPPER"]     
            
            # ★★★ 修正箇所: rail_p (rail_params内) から取得するように変更 ★★★
            self.work_time_limit_min = rail_p.get("WORK_TIME_LIMIT_MIN", 60)
            self.time_limit_sec = self.work_time_limit_min * 60
            
            # 現在位置と進行方向の初期化
            self.current_pos_mm = 0       
            self.rail_direction = 'f'     
            
            self.rail_params_loaded = True
            self.get_logger().info(f"設定完了: Limit={self.limit_dist_mm}mm, Step={self.step_dist_mm}mm")
            # ログで読み込み値を確認
            self.get_logger().info(f"稼働時間制限: {self.work_time_limit_min}分 ({self.time_limit_sec}秒)")
            
        except Exception as e:
            self.get_logger().error(f"初期設定エラー: {e}")
            self.VOICE = False
            self.limit_dist_mm = 0
            self.step_dist_mm = 0
            self.time_limit_sec = 0

        # 開始時刻の記録
        self.start_time = time.time()

        # === VisionService クライアント ===
        self.vision_client = self.create_client(
            VisionService,
            "vision_service",
            qos_profile=qos_profile_services_default)
        while not self.vision_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('ビジョンサーバ待機中...')
        self.vision_request =  VisionService.Request()
        
        # === ArmService クライアント ===
        self.arm_client = self.create_client(
            ArmService,
            "arm_service",
            qos_profile=qos_profile_services_default)
        while not self.arm_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('アームサーバ待機中...')
        self.arm_request =  ArmService.Request()
        
        # === SuctionCommand (EE) クライアント ===
        self.ee_client = self.create_client(
            SuctionCommand,
            'command',
            qos_profile=qos_profile_services_default)
        while not self.ee_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('EEサーバ待機中...')
        self.ee_request = SuctionCommand.Request()
        
        # === RailService クライアント ===
        self.rail_client = self.create_client(
            RailService,
            "rail_control",
            qos_profile=qos_profile_services_default)
        while not self.rail_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('レールサーバ待機中...')
        self.rail_request = RailService.Request()
        
        # === 初期化実行 ===
        self.arm_and_ee_send_request_init()
    
    @staticmethod
    def load_yaml(file_path):
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    # === ビジョンノードへのリクエスト関数 ===
    def vision_send_request_check(self):
        self.vision_request.task = "detect_check"
        self.vision_request.direction = self.rail_direction 
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    def vision_send_request_tompos(self):
        self.vision_request.task = "req_tomato_pose"
        self.vision_request.direction = self.rail_direction
        self.vision_future = self.vision_client.call_async(self.vision_request)
        rclpy.spin_until_future_complete(self, self.vision_future)
        return self.vision_future.result()

    # === アームノードへのリクエスト関数 ===
    def arm_and_ee_send_request_init(self):
        self.arm_request.task = "init_arm"
        self.ee_request.command = '0'
        self.arm_future = self.arm_client.call_async(self.arm_request)
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        rclpy.spin_until_future_complete(self, self.ee_future)
        self.ee_send_request('3')
        return self.arm_future.result()
    
    def arm_send_request_target(self, target, pre_h):
        self.arm_request.task = "move_to_target"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z + pre_h.data
        self.arm_request.target.approach_direction = target.approach_direction
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_box(self):
        self.arm_request.task = "move_to_box"
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()
    
    def arm_send_request_home(self, target):
        self.arm_request.task = "home"
        self.arm_request.target.x = target.x
        self.arm_request.target.y = target.y
        self.arm_request.target.z = target.z
        self.arm_request.target.approach_direction = target.approach_direction
        self.arm_future = self.arm_client.call_async(self.arm_request)
        rclpy.spin_until_future_complete(self, self.arm_future)
        return self.arm_future.result()

    def ee_send_request(self, mode):
        self.ee_request.command = mode
        self.ee_future = self.ee_client.call_async(self.ee_request)
        rclpy.spin_until_future_complete(self, self.ee_future)
        return self.ee_future.result()
    
    def rail_send_request(self, direction):
        self.get_logger().info(f'レールを {direction} へ移動要求します。')
        self.rail_request.req_dir = direction
        self.rail_future = self.rail_client.call_async(self.rail_request)
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.rail_future.done():
                try:
                    result = self.rail_future.result()
                    self.get_logger().info(f'レール移動完了応答(Pulse): {result.pulse.data}')
                    return result
                except Exception as e:
                    self.get_logger().error(f'レールサービス呼び出し失敗: {e}')
                    return None
        return None

def main(args=None):
    rclpy.init(args=args)
    node = AnalizeToHarvestNode()
    logger = node.get_logger()
    
    if node.rail_params_loaded == False:
        logger.error("パラメータ読み込み失敗のため終了します")
        return

    if node.VOICE:
        playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/おいしそうなトマトを収穫するのだ.wav")

    skip_vision_check = False

    try:
        while rclpy.ok():
            # --- 時間チェック ---
            elapsed_time = time.time() - node.start_time
            if elapsed_time > node.time_limit_sec and not node.return_mode:
                logger.info("【時間切れ】設定時間を経過しました。帰還モード(Return Mode)に移行します。")
                node.return_mode = True

            # --- 認識スキップ判定 ---
            if node.return_mode or skip_vision_check:
                if skip_vision_check:
                    logger.info("一連の収穫動作が終了したため、この位置での再認識をスキップして移動します。")
                
                vision_response = None 
                detect_check_result = False
                skip_vision_check = False # フラグをリセット
            else:
                vision_response = node.vision_send_request_check()
                detect_check_result = vision_response.detect_check if vision_response else False
            
            # --- 分岐処理 ---
            if vision_response is not None and detect_check_result:
                # === A. トマトが見つかった場合 (通常収穫) ===
                logger.info("トマトを発見しました。収穫シーケンスを開始します。")
                if node.VOICE:
                    playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/トマトを見つけたのだ.wav")
                
                target = vision_response.target_pos.tomato_data[0]
                arm_response = node.arm_send_request_home(target)
                pre_arm_hight = arm_response.tom_hight
                
                vision_response = node.vision_send_request_tompos()
                targets = vision_response.target_pos.tomato_data

                if not targets:
                    logger.warn("手先カメラでターゲットを見失いました。認識をスキップして移動します。")
                    node.arm_and_ee_send_request_init()
                    skip_vision_check = True
                    continue 

                if node.VOICE:
                    playsound("/home/ylab/hibikino_toms_ws/src/harvest_task_pkg/sound/熟したトマトを収穫するのだ.wav")
                
                # ★★★ 認識した全トマトに対してループ実行 ★★★
                for i, target in enumerate(targets):
                    logger.info(f"{i+1}/{len(targets)}個目のトマトへ移動します。")
                    arm_response = node.arm_send_request_target(target, pre_arm_hight)
                    
                    if arm_response.task_comp:
                        time.sleep(0.5)
                        if node.ee_send_request('1').answer not in ['1', '666']: continue 
                        if node.ee_send_request('2').answer not in ['2', '666']: 
                            node.ee_send_request('0')
                            continue
                        node.arm_send_request_box()
                        node.ee_send_request('3')
                        node.ee_send_request('0')
                        logger.info(f"{i+1}個目のトマト収穫完了。")
                    else:
                        # ★★★ 変更: 失敗しても諦めて次のトマトへ (continue) ★★★
                        logger.error(f"{i+1}個目のアーム移動失敗(範囲外など)。スキップして次を試みます。")
                        node.ee_send_request('0') 
                        node.ee_send_request('3') 
                        # breakせず、次のループへ進む
                        continue 
                
                # ★★★ ループ終了後の処理 ★★★
                logger.info("全ターゲットの試行終了。アームを初期化して移動します。")
                node.arm_and_ee_send_request_init()
                
                # ここで必ずフラグを立てることで、次のwhileループでは認識を行わずレール移動へ進む
                skip_vision_check = True
                
            else:
                # === B. トマトが見つからない、またはスキップされた場合 (レール移動) ===
                
                next_direction = node.rail_direction
                move_allowed = False
                
                if node.return_mode:
                    if node.current_pos_mm <= 0:
                        logger.info("【帰還完了】スタート地点(0mm)に戻りました。全作業を終了します。")
                        break 
                    else:
                        logger.info("スタート地点へ戻るため後進します。")
                        next_direction = 'b'
                        move_allowed = True
                else:
                    logger.info("探索移動を行います。")
                    if node.rail_direction == 'f':
                        if node.current_pos_mm + node.step_dist_mm > node.limit_dist_mm:
                            logger.info(f"終端({node.limit_dist_mm}mm)到達。折り返し(後進)します。")
                            node.rail_direction = 'b'
                            next_direction = 'b'
                            move_allowed = False 
                        else:
                            next_direction = 'f'
                            move_allowed = True
                            
                    elif node.rail_direction == 'b':
                        if node.current_pos_mm - node.step_dist_mm < 0:
                            logger.info("始点(0mm)到達。折り返し(前進)して探索を継続します。")
                            node.rail_direction = 'f'
                            next_direction = 'f'
                            move_allowed = False 
                        else:
                            next_direction = 'b'
                            move_allowed = True

                # 移動実行
                if move_allowed:
                    logger.info(f"レール移動: {next_direction}, 現在位置: {node.current_pos_mm}mm")
                    rail_response = node.rail_send_request(next_direction)
                    
                    if rail_response is None or rail_response.res_dir != next_direction:
                        logger.error("!!! レール移動失敗。中断します。 !!!")
                        break
                    else:
                        if next_direction == 'f':
                            node.current_pos_mm += node.step_dist_mm
                        else:
                            node.current_pos_mm -= node.step_dist_mm
                        
                        logger.info(f"移動完了。現在位置: {node.current_pos_mm}mm")
                        time.sleep(1.0)
                else:
                    logger.info("方向転換または待機中...")
                    time.sleep(1.0)
            
            # ビジョンノード応答なし待機 (スキップ時は待機不要)
            if vision_response is None and not node.return_mode and not skip_vision_check:
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        logger.info("Ctrl+Cが押されました。")
    finally:
        logger.info("終了処理中... アームを安全な位置に戻します。")
        try:
            node.arm_and_ee_send_request_init()
        except Exception as e:
            logger.warn(f"アーム初期化失敗: {e}")
            
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()