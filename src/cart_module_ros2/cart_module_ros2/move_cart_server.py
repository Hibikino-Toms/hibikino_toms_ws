import rclpy
from rclpy.node import Node
import serial
import serial.tools.list_ports

from toms_msg.srv import CartService

class MoveCartServer(Node):
    def __init__(self):
        super().__init__('move_cart_server')
        
        # サービスの設定
        self.srv = self.create_service(CartService, 'cart', self.callback)

        # デバイスの認識
        serial_number = "E66130100F9F7B2E" 
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None:
            raise RuntimeError("レール用のマイコンが接続されていません。")
        BAUDRATE = 115200
        
        # シリアルポートの設定
        self.serial_port = serial.Serial(DEVICENAME, BAUDRATE, timeout=None)
        if self.serial_port.is_open:  # シリアルポートが開いたか確認
            self.get_logger().info(f"シリアルポート {DEVICENAME} が開きました。ボーレート: {BAUDRATE}")
        else:
            self.get_logger().error(f"シリアルポート {DEVICENAME} を開くことができませんでした。")

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
        self.serial_port.write(str.encode(send_data))
        self.serial_port.flush()
        try:
            # Picoからデータを受信
            line = self.serial_port.readline()
            line_decoded = str(repr(line.decode())[1:-5])
            # 配列に変換
            receive_data = line_decoded.split()
            print(receive_data[0])
            recive_val = float(receive_data[0])
            receive_line = recive_val
        except serial.serialutil.SerialTimeoutException:
            print("time_out")
        return receive_line
    
    def callback(self, request, response):
        req_move = request.move_value
        req_pwm = request.pwm_value
        # cart動作
        a = self.Go(req_move, req_pwm)

        response.move_result = float(a)
        return response

    def Go(self, move_val, pwm_val):
        move_val = int(move_val)
        pwm_val = int(pwm_val)
        print("Move Cart")
        send_data = str(move_val) +','+ str(pwm_val) +'\n'
        result_data = self.data2pico(send_data)
        # print(result_data)
        return result_data


def main():
    rclpy.init()
    server_node = MoveCartServer()
    try:
        rclpy.spin(server_node)
    except KeyboardInterrupt:
        print("Ctrl+Cが押されました．")
    finally:
        rclpy.shutdown()