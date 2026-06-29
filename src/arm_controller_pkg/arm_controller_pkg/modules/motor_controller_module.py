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

class MotorController():
    def __init__(self):
        self.dxl_home_angle = [100, 340, 100]  # モータの数に応じて調整
        self.dxl_harvest_box_angle = [115, 80, 120]  # モータの数に応じて調整
        self.max_angle = 360.0
        self.encoder_max_value = 4095
        
        serial_number = "FT94VZIA"
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME == None:
            print("デバイスが接続されていません。")
        
        self.BAUDRATE = 4000000
        PROTOCOL_VERSION = 2.0

        self.DXL_IDs = [1, 2, 3, 4]
        self.ADDR_TORQUE_ENABLE          = 64
        self.ADDR_LED_RED                = 65
        self.LEN_LED_RED                 = 1         # データバイト長
        self.ADDR_GOAL_POSITION = 116
        self.LEN_GOAL_POSITION = 4
        self.ADDR_PRESENT_POSITION = 132
        self.LEN_PRESENT_POSITION = 4
        self.DXL_MIN_POSITION_VALUE = 0
        self.DXL_MAX_POSITION_VALUE = 4095
        
        # モータの加速・減速の滑らかさの設定
        self.ADDR_PROFILE_ACCEL = 108
        self.ADDR_PROFILE_VELO = 112
        # 設定のための値
        self.profile_accels = [10, 10, 10, 10]
        # self.profile_veloes = [30, 30, 100, 30]
        self.profile_veloes = []
        # DXL_1_MIN_POSI = 1024 # 90 [deg]
        # DXL_1_MAX_POSI = 3072 # 270[deg]
        # DXL_2_MIN_POSI = 1024 # 90 [deg]
        # DXL_2_MAX_POSI = 3072 # 270[deg]
        # DXL_3_MIN_POSI = 171  # 15 [deg]
        # DXL_3_MAX_POSI = 3925 # 345[deg]
        # DXL_4_MIN_POSI = 512  # 45 [deg]
        # DXL_4_MAX_POSI = 3584 # 315[deg]

        self.TORQUE_ENABLE               = 1
        self.TORQUE_DISABLE              = 0
        self.DXL_MOVING_STATUS_THRESHOLD = 20

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

    def set_profilr_accel_velo(self, profile_veloes):        
        for i, dxl_id in enumerate(self.DXL_IDs):
            result, error = self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_PROFILE_ACCEL, self.profile_accels[i]
            )
            if result != COMM_SUCCESS:
                print(f"[ID:{dxl_id}] {self.packet_handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"[ID:{dxl_id}] {self.packet_handler.getRxPacketError(error)}")
        
        for i, dxl_id in enumerate(self.DXL_IDs):
            result, error = self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, self.ADDR_PROFILE_VELO, profile_veloes[i]
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
            pre_angles = self.read_positions()
            pre_angles = [self.position_to_angle(pos) for pos in pre_angles]
            pre_angles.pop(1)
            pre_angles = [round(i) for i in pre_angles]
            
            diff_posi = [abs(G - P) for G, P in zip(goal_angles, pre_angles)]
            max_diff = max(diff_posi)
            for diff in diff_posi:
                value = round(80 * (diff / max_diff))  # diffが小さいほどvalueが小さくなる
                value = max(1, value)  # 最小値を1に制限
                self.profile_veloes.append(value)
            self.profile_veloes = [self.profile_veloes[0], self.profile_veloes[0], self.profile_veloes[1], self.profile_veloes[2]]
        else :
            self.profile_veloes = [90, 90, 90, 90]
        
        # 速度及び加速度プロファイルの設定 → 滑らかな動作のための設定
        self.set_profilr_accel_velo(self.profile_veloes)
        
        while 1:
            # 目標角度をモータ制御用の値に変換
            goal_angles = [goal_angles[0], 360 - goal_angles[0], goal_angles[1], goal_angles[2]]
            goal_positions = [self.angle_to_position(angle) for angle in goal_angles]
            self.add_bulk_write_params(goal_positions)
            
            # 目標位置をバルク書き込み
            result = self.group_bulk_write.txPacket()
            if result != COMM_SUCCESS:
                print(f"{self.packet_handler.getTxRxResult(result)}")
            self.clear_bulk_write_params()
        
            while 1:
                present_positions = self.read_positions()
                # for i, dxl_id in enumerate(self.DXL_IDs):
                #     print(f"[ID:{dxl_id}] Present position: {present_positions[i]}")
                check_threshold = all(
                    abs(goal - present) <= self.DXL_MOVING_STATUS_THRESHOLD
                    for goal, present in zip(goal_positions, present_positions)
                )
                if check_threshold:
                    # time.sleep(1)
                    break
            self.clear_bulk_write_params()
            
            # self.disable_torque()
            # self.port_handler.closePort()
            break

    def move_to_home(self):
        task = "home"
        print('Arm :Move to home')
        self.move_motors(self.dxl_home_angle, task)

    def init_pos(self):
        task = "init"
        print('Arm :Move to initial position')
        self.move_motors(self.dxl_home_angle, task)

    def move_to_box(self):
        task = "box"
        print('Arm :Move to harvest box')
        self.move_motors(self.dxl_harvest_box_angle, task)

    def read_positions(self):
        self.add_bulk_read_params()
        result = self.group_bulk_read.txRxPacket()
        if result != COMM_SUCCESS:
            print(f"{self.packet_handler.getTxRxResult(result)}")
        
        # 現在位置の取得
        positions = [self.group_bulk_read.getData(dxl_id, self.ADDR_PRESENT_POSITION, self.LEN_PRESENT_POSITION) for dxl_id in self.DXL_IDs]
        self.clear_bulk_read_params()

        return positions

    def angle_to_position(self, angle):
        angle_ratio = (angle % self.max_angle) / self.max_angle
        position = self.DXL_MIN_POSITION_VALUE + int(angle_ratio * (self.DXL_MAX_POSITION_VALUE - self.DXL_MIN_POSITION_VALUE))
        return position
    
    def position_to_angle(self, position):
        position_ratio = (position - self.DXL_MIN_POSITION_VALUE) / (self.DXL_MAX_POSITION_VALUE - self.DXL_MIN_POSITION_VALUE)
        angle = position_ratio * self.max_angle
        return angle
    
    def __del__(self):
        if self.port_handler.is_open:  # ポートが開いているかを確認
            print('Close the port')
            self.disable_torque()
            self.port_handler.closePort()
    
    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()
        
        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合


if __name__ == "__main__":
    try:
        controller = MotorController()
        
        # angle = [第1関節, 第2関節, 手先角度]
        home_angles = controller.dxl_home_angle
        # 現在のモータの角度読み取り
        pre_angles = controller.read_positions()
        pre_angles = [controller.position_to_angle(pos) for pos in pre_angles]
        pre_angles.pop(1)
        pre_angles = [round(i) for i in pre_angles]
        print(pre_angles)

        check_threshold = all(
                    abs(home - pre_angle) <= 2
                    for home, pre_angle in zip(home_angles, pre_angles)
                )
        
        if check_threshold: # アームがホームポジションにあるときのみ処理を進める
            # 目標角度を設定してモータを移動させる
            goal_angles = [90, 270, 270]
            task = "target"
            controller.move_motors(goal_angles, task)
            # goal_angles = [125, 50, 100]
            # task = ""
            # controller.move_motors(goal_angles, task)
            
        else :
            controller.move_to_home()
            
        print("正常に動作しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        controller.__del__()
