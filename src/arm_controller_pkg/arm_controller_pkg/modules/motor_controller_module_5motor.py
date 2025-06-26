#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
モータ制御部分
司令に応じて、4つのアームを同時位置制御するプログラム
位置制御モードのみの実装

〜〜〜
2024/10/6 時点

指定された位置へのモータ制御を行うだけのコード。
Dynamixelモータの型: 
第1関節（アーム付け根）: XM540-W270-R ✕2
第2関節: XM540-W270-R（第一関節と同様）
第3関節: XM430-W350-R

# TODO: 2段階収穫動作は未実装

〜〜〜

@author : 吉永
"""

import time
from dynamixel_sdk import *
import serial.tools.list_ports
import yaml

class MotorController():
    def __init__(self, dxl_params):
        # デバイスの認識
        serial_number = dxl_params['U2D2_SERIAL_NUMBER']
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("U2D2が接続されていません。")
        
        # 角度の設定
        self.DXL_HOME_ANGLE = dxl_params['DXL_HOME_ANGLE'] # ホームポジションの角度
        self.DXL_BOX_ANGLE = dxl_params['DXL_BOX_ANGLE'] # 収穫ボックスの角度
        
        self.MAX_ANGLE = dxl_params['MAX_ANGLE']
        self.ENCODER_MAX_VALUE = dxl_params['ENCODER_MAX_VALUE']

        # Dynamixelの諸設定用の諸パラメータ
        self.BAUDRATE = dxl_params['BAUDRATE']
        PROTOCOL_VERSION = dxl_params['PROTOCOL_VERSION']
        self.DXL_IDs = dxl_params['DXL_IDs']
        self.ADDR_TORQUE_ENABLE = dxl_params['ADDR_TORQUE_ENABLE']
        self.ADDR_LED_RED = dxl_params['ADDR_LED_RED']
        self.LEN_LED_RED = dxl_params['LEN_LED_RED']
        self.ADDR_GOAL_POSITION = dxl_params['ADDR_GOAL_POSITION']
        self.LEN_GOAL_POSITION = dxl_params['LEN_GOAL_POSITION']
        self.ADDR_PRESENT_POSITION = dxl_params['ADDR_PRESENT_POSITION']
        self.LEN_PRESENT_POSITION = dxl_params['LEN_PRESENT_POSITION']
        self.DXL_MIN_POSITION_VALUE = dxl_params['DXL_MIN_POSITION_VALUE']
        self.DXL_MAX_POSITION_VALUE = dxl_params['DXL_MAX_POSITION_VALUE']

        self.ADDR_PROFILE_ACCEL = dxl_params['ADDR_PROFILE_ACCEL']
        self.ADDR_PROFILE_VELO = dxl_params['ADDR_PROFILE_VELO']
        self.PROFILE_ACCELS = dxl_params['PROFILE_ACCELS']
        self.PROFILE_VELOES = dxl_params['PROFILE_VELOES']
        # self.profile_veloes = [30, 30, 100, 100, 30]  # 加速設定例

        self.TORQUE_ENABLE = dxl_params['TORQUE_ENABLE']
        self.TORQUE_DISABLE = dxl_params['TORQUE_DISABLE']
        self.DXL_MOVING_STATUS_TH = dxl_params['DXL_MOVING_STATUS_TH']
        self.TIMEOUT_TH = dxl_params["TIMEOUT_TH"]

        self.port_handler = PortHandler(DEVICENAME)
        self.packet_handler = PacketHandler(PROTOCOL_VERSION)
        self.group_bulk_write = GroupBulkWrite(self.port_handler, self.packet_handler)
        self.group_bulk_read = GroupBulkRead(self.port_handler, self.packet_handler)

        if not self.port_handler.openPort():
            raise RuntimeError("Failed to open port.")
        else:
            print('Open the port.')
        if not self.port_handler.setBaudRate(self.BAUDRATE):
            raise RuntimeError("Baud rate change failed.")

        # self.set_profilr_accel_velo()
        self.enable_torque()
    
    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()
        
        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合

    def set_profilr_accel_velo(self, profile_vel, profile_acce):
        for i, dxl_id in enumerate(self.DXL_IDs):
            result, error = self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_PROFILE_ACCEL, profile_acce[i]
            )
            if result != COMM_SUCCESS:
                print(f"[ID:{dxl_id}] {self.packet_handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"[ID:{dxl_id}] {self.packet_handler.getRxPacketError(error)}")
        
        for i, dxl_id in enumerate(self.DXL_IDs):
            result, error = self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_PROFILE_VELO, profile_vel[i]
            )
            if result != COMM_SUCCESS:
                print(f"[ID:{dxl_id}] {self.packet_handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"[ID:{dxl_id}] {self.packet_handler.getRxPacketError(error)}")
    
    def enable_torque(self):
        for dxl_id in self.DXL_IDs:
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_ENABLE
            )
            if result != COMM_SUCCESS:
                print(f"[ID:{dxl_id}] {self.packet_handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"[ID:{dxl_id}] {self.packet_handler.getRxPacketError(error)}")

    def disable_torque(self):
        for dxl_id in self.DXL_IDs:
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_DISABLE
            )
            if result != COMM_SUCCESS:
                print(f"[ID:{dxl_id}] {self.packet_handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"[ID:{dxl_id}] {self.packet_handler.getRxPacketError(error)}")

    def add_bulk_read_params(self):
        for dxl_id in self.DXL_IDs:
            result = self.group_bulk_read.addParam(dxl_id, self.ADDR_PRESENT_POSITION, self.LEN_PRESENT_POSITION)
            if not result:
                raise RuntimeError(f"[ID:{dxl_id}] addparam failed for groupBulkRead.")

    def clear_bulk_read_params(self):
        self.group_bulk_read.clearParam()

    def add_bulk_write_params(self, goal_positions):
        for i, dxl_id in enumerate(self.DXL_IDs):
            param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_positions[i])),
                                    DXL_HIBYTE(DXL_LOWORD(goal_positions[i])),
                                    DXL_LOBYTE(DXL_HIWORD(goal_positions[i])),
                                    DXL_HIBYTE(DXL_HIWORD(goal_positions[i]))]
            result = self.group_bulk_write.addParam(dxl_id, self.ADDR_GOAL_POSITION, self.LEN_GOAL_POSITION, param_goal_position)
            if not result:
                raise RuntimeError(f"[ID:{dxl_id}] addparam failed for groupBulkWrite.")

    def clear_bulk_write_params(self):
        self.group_bulk_write.clearParam()

    def move_motors(self, goal_angles, task):
        if not self.port_handler.is_open:
            # ポートを開く処理
            if not self.port_handler.openPort():
                raise RuntimeError("Failed to open port.")
            else:
                print(f"Opened dxl port.")
            if not self.port_handler.setBaudRate(self.BAUDRATE):
                raise RuntimeError("Baud rate change failed.")
        
        if task == "target":
            print('Move to target')
            # pre_angles = self.read_positions()
            # pre_angles = [self.position_to_angle(pos) for pos in pre_angles]
            # pre_angles.pop(1)
            # pre_angles = [round(i) for i in pre_angles]
            
            # diff_posi = [abs(G - P) for G, P in zip(goal_angles, pre_angles)]
            # max_diff = max(diff_posi)
            # for diff in diff_posi:
            #     value = round(100 * (diff / max_diff))  # diffが小さいほどvalueが小さくなる
            #     value = max(1, value)  # 最小値を1に制限
            #     self.PROFILE_VELOES.append(value)
            # self.PROFILE_VELOES = [self.PROFILE_VELOES[0], self.PROFILE_VELOES[0], self.PROFILE_VELOES[1], self.PROFILE_VELOES[1], self.PROFILE_VELOES[2]]
            PROFILE_VELOES = [75, 75, 75, 75, 75]
            PROFILE_ACCELS = self.PROFILE_ACCELS
        elif task == "cutting":
            PROFILE_VELOES = [75, 75, 75, 75, 75]
            PROFILE_ACCELS = self.PROFILE_ACCELS
        elif task == "box":
            PROFILE_VELOES = [75, 75, 75, 75, 75]
            PROFILE_ACCELS = self.PROFILE_ACCELS
        else :
            PROFILE_VELOES = [75, 75, 75, 75, 75]
            PROFILE_ACCELS = self.PROFILE_ACCELS
            
        
        # 速度及び加速度プロファイルの設定 → 滑らかな動作のための設定
        self.set_profilr_accel_velo(PROFILE_VELOES, PROFILE_ACCELS)
        
        #print(goal_angles)
        while True:
            # 目標角度をモータ制御用の値に変換
            goal_angles = [goal_angles[0], 360 - goal_angles[0], goal_angles[1], 360 - goal_angles[1], goal_angles[2]]
            goal_positions = [self.angle_to_position(angle) for angle in goal_angles]
            self.add_bulk_write_params(goal_positions)
            
            # 目標位置をバルク書き込み
            result = self.group_bulk_write.txPacket()
            if result != COMM_SUCCESS:
                print(f"{self.packet_handler.getTxRxResult(result)}")
            self.clear_bulk_write_params()
            
            start_time = time.time()  # タイムアウト監視開始
            while True:
                present_positions = self.read_positions()
                # for i, dxl_id in enumerate(self.DXL_IDs):
                #     print(f"[ID:{dxl_id}] Present position: {present_positions[i]}")
                #print(f'goal_positions：{goal_positions},present_positions：{present_positions}')
                check_threshold = all(
                    abs(goal - present) <= self.DXL_MOVING_STATUS_TH
                    for goal, present in zip(goal_positions, present_positions)
                )
                elapsed_time = time.time() - start_time  # 経過時間計算
                
                if check_threshold:
                    # time.sleep(1)
                    break
                if elapsed_time >= self.TIMEOUT_TH:  # 3秒以上経過したらタイムアウト
                    print("タイムアウト．次の動作に移ります．")
                    break
            self.clear_bulk_write_params()
            break

        # self.disable_torque()
        # self.port_handler.closePort()

    def move_to_home(self):
        task = "home"
        print('Move to home')
        self.move_motors(self.DXL_HOME_ANGLE, task)

    def init_pos(self):
        task = "init"
        print('ARM: Move to initial position')
        self.move_motors(self.DXL_HOME_ANGLE, task)

    def move_to_box(self):
        task = "box"
        print('ARM: Move to harvest box')
        self.move_motors(self.DXL_BOX_ANGLE, task)

    def read_positions(self):
        self.add_bulk_read_params()
        result = self.group_bulk_read.txRxPacket()
        if result != COMM_SUCCESS:
            print(f"{self.packet_handler.getTxRxResult(result)}")
        
        # 現在位置の取得
        positions = [self.group_bulk_read.getData(dxl_id, self.ADDR_PRESENT_POSITION, self.LEN_PRESENT_POSITION) for dxl_id in self.DXL_IDs]
        self.clear_bulk_read_params()

        return positions

    #360度→4095にするみたいな関数
    def angle_to_position(self, angle):
        angle_ratio = (angle % self.MAX_ANGLE) / self.MAX_ANGLE
        position = self.DXL_MIN_POSITION_VALUE + int(angle_ratio * (self.DXL_MAX_POSITION_VALUE - self.DXL_MIN_POSITION_VALUE))
        return position
    
    #4095→360度にするみたいな関数
    def position_to_angle(self, position):
        position_ratio = (position - self.DXL_MIN_POSITION_VALUE) / (self.DXL_MAX_POSITION_VALUE - self.DXL_MIN_POSITION_VALUE)
        angle = position_ratio * self.MAX_ANGLE
        return angle
    
    def __del__(self):
        if self.port_handler.is_open:  # ポートが開いているかを確認
            print('Close the port.')
            print("正常に動作しました。")
            # self.disable_torque()
            self.port_handler.closePort()

    def close(self, dis_torque):
        if self.port_handler.is_open:  # ポートが開いているかを確認
            print('Close the port.')
            print("正常に動作しました。")
            if dis_torque:
                self.disable_torque()
            self.port_handler.closePort()

if __name__ == "__main__":
    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"YAMLファイルが見つかりません: {file_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLファイルの解析エラー: {e}")

    dis_torque = None
    user_input = input("動作後アームをロックしますか？ (y/N): ").strip().lower()
    # 入力に応じて `dis_torque` を設定
    if user_input == "y":
        dis_torque = False
    else:  # 入力が 'n' または何も入力されない場合は 'n' とみなす
        dis_torque = True
        
    try:
        yaml_path='/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = load_yaml(yaml_path)
        dxl_params = params["dxl_params"]
        controller = MotorController(dxl_params)
        
        # angle = [第1関節, 第2関節, 手先角度]
        home_angles = controller.DXL_HOME_ANGLE
        # 現在のモータの角度読み取り
        pre_angles = controller.read_positions()
        pre_angles = [controller.position_to_angle(pos) for pos in pre_angles]
        pre_angles.pop(1)
        pre_angles.pop(2)
        pre_angles = [round(i) for i in pre_angles]
        print(f'現在の角度(deg): {pre_angles}')
        
        check_now_angle = False
        
        if check_now_angle == False:
            check_threshold = all(
                        abs(home - pre_angle) <= 5
                        for home, pre_angle in zip(home_angles, pre_angles)
                    )
            if check_threshold: # アームがホームポジションにあるときのみ処理を進める
                # 目標角度を設定してモータを移動させる
                goal_angles = [90, 90, 90]
                task = "target"
                controller.move_motors(goal_angles, task)
                
            else :
                controller.move_to_home()
            pre_angles = controller.read_positions()
            pre_angles = [controller.position_to_angle(pos) for pos in pre_angles]
            pre_angles.pop(1)
            pre_angles.pop(2)
            pre_angles = [round(i) for i in pre_angles]
            print(f'現在の角度(deg): {pre_angles}')
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        controller.close(dis_torque)
