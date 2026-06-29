# end_effector_driver_node.py
# ボーレートをYAMLから読み込まず、プログラム内で直接設定するバージョン

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String
import serial, serial.tools.list_ports, yaml

class EndEffectorDriverNode(Node):
    def __init__(self):
        super().__init__('end_effector_driver_node')
        self.get_logger().info('エンドエフェクタ専門家ノード (End Effector Driver) を起動します。')

        # === YAMLパラメータ読み込み ===
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        EE_params = params["EE_params"]

        # ★★★ ボーレートをプログラム内に直接設定（ハードコード） ★★★
        baudrate = 115200
        self.get_logger().info(f"ボーレートはプログラム内で直接 {baudrate} に設定されています。")

        # === シリアル通信の初期化 ===
        serial_number = EE_params["EE_PICO_SERIAL_NUMBER"]
        DEVICENAME = self.select_device(serial_number)
        if DEVICENAME is None: raise RuntimeError("EE用のマイコンが接続されていません。")
        self.end_effector_ser = serial.Serial(DEVICENAME, baudrate, timeout=1.0)
        self.FOTO_VAL, self.EDF_VAL = EE_params["FOTO_VAL"], EE_params["EDF_VAL"]
        
        # === 高信頼性QoSプロファイルを作成 ===
        reliable_qos = QoSProfile(
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        # === Subscriberの作成 ===
        self.cmd_subscriber = self.create_subscription(String, 'end_effector_command', self.command_callback, reliable_qos)
        
        self.get_logger().info('指令待機中...')

    def command_callback(self, msg):
        """司令塔からのコマンドに応じて適切なシリアルデータを送信する"""
        command = msg.data
        self.get_logger().info(f"コマンド受信: '{command}'")
        if command == 'ENABLE_EDF': self.enable_edf()
        elif command == 'DISABLE_EDF': self.disable_edf()
        elif command == 'CLOSE_FINGER': self.close_finger()
        elif command == 'OPEN_FINGER': self.open_finger()
        else: self.get_logger().warn(f"未定義のコマンドです: '{command}'")

    def select_device(self, serial_number):
        for port in serial.tools.list_ports.comports():
            if port.serial_number == serial_number: return port.device
        return None

    @staticmethod
    def load_yaml(file_path):
        with open(file_path, "r") as file: return yaml.safe_load(file)

    def data2pico(self, send_data):
        self.get_logger().info(f"Picoへ送信 -> {send_data.strip()}")
        self.end_effector_ser.write(str.encode(send_data))
        self.end_effector_ser.flush()
        line = self.end_effector_ser.readline().decode().strip()
        self.get_logger().info(f"Picoから受信 <- {line}")
        return line

    def disable_edf(self): return self.data2pico(f"0,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def enable_edf(self): return self.data2pico(f"1,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def close_finger(self): return self.data2pico(f"2,{self.FOTO_VAL},{self.EDF_VAL}\n")
    def open_finger(self): return self.data2pico(f"3,{self.FOTO_VAL},{self.EDF_VAL}\n")

def main(args=None):
    rclpy.init(args=args)
    node = EndEffectorDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()