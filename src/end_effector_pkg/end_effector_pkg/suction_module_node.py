import rclpy
from rclpy.node import Node
import serial
import serial.tools.list_ports
import time
from playsound import playsound

# DEVICENAME = '/dev/usb_suction_module'
BAUDRATE   = 115200
FOTO_VAL   = 900
EDF_VAL    = 1050


class SuctionModuleNode(Node):
    def __init__(self):
        super().__init__('suction_module_node')
        self.get_logger().info('suction_module_node：active')
        # デバイスの認識とシリアル通信
        serial_number = "E66130100F63232E"
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("EE用のマイコンが接続されていません。")
        self.end_effector_ser = serial.Serial(DEVICENAME,BAUDRATE,timeout=None)
        time.sleep(2)
        # playsound("/home/ylab/toms_ws/src/end_effector_pkg/end_effector_pkg/sound/サクションモジュールノードを起動したのだ.wav")
        self.timer = self.create_timer(1.0, self.timer_callback)

    def select_device(self, serial_number):
        """指定されたシリアル番号に対応するデバイス名を返す"""
        # 接続されているUSBデバイスのリストを取得
        ports = serial.tools.list_ports.comports()

        # 特定のシリアル番号を持つデバイスを検索
        for port in ports:
            if port.serial_number == serial_number:
                return port.device  # デバイス名を返す
        
        return None  # デバイスが見つからなかった場合

    def data2pico(self, send_data):
        # Picoへデータを送信
        self.end_effector_ser .write(str.encode(send_data))
        self.end_effector_ser .flush()
        try:
            # Picoからデータを受信
            line = self.end_effector_ser .readline()
            line_decoded = str(repr(line.decode())[1:-5])
            # 配列に変換
            receive_data = line_decoded.split()
            recive_mode = int(receive_data[0])
            receive_line = [recive_mode]
        except serial.serialutil.SerialTimeoutException:
            print("time_out")
        return receive_line

    # 下顎開く＋EDF停止
    def ee_stop(self):
        send_data = str(0) +','+ str(FOTO_VAL) +','+ str(EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        self.get_logger().info(result_data)
        return result_data
    
    # EDF起動
    def edf_enable(self):
        send_data = str(1) +','+ str(FOTO_VAL) +','+ str(EDF_VAL) +'\n'
        result_data = self.data2pico(send_data)
        return result_data

    # 下顎閉じる
    def close_finger(self):
        send_data = str(2) +','+ str(FOTO_VAL) +','+ str(EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data
    
    # 下顎開く＋EDF起動
    def open_finger(self):
        send_data = str(3) +','+ str(FOTO_VAL) +','+ str(EDF_VAL) +'\n'
        result_data =  self.data2pico(send_data)
        return result_data

    def timer_callback(self):
        self.get_logger().info('トマトを吸引するのだ')
        self.edf_enable()

def main():
    rclpy.init()
    node = SuctionModuleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('Ctrl + C is pressed.')
    #rclpy.shutdown()
    print('program end')