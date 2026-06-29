#
# @file arm_control_node.py
# @brief 遠隔操作用のロボットアーム制御ノード (目標角度受信・安全装置付き)
#
# @details
# /target_arm_angles と /target_z_pos トピックから目標値を受け取り、
# 物理的な可動範囲を超えないかチェックした上で、モーターとZ軸を制御します。
#
import rclpy
from rclpy.node import Node
import yaml
import sys
from std_msgs.msg import Float32MultiArray, Float32

# --- 必要なモジュールのみインポート ---
sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis
# ---------------------------------------------------------

# ★★★ 新しい安全装置クラス ★★★
class SafetyLimiter:
    """
    @class SafetyLimiter
    @brief モーターの可動範囲をチェックする安全装置クラス
    """
    def __init__(self, dxl_params):
        """
        @brief コンストラクタ。YAMLファイルから5つのモーターすべての可動範囲を読み込む。
        """
        self.motor_limits = [
            (dxl_params.get("DXL_1_MIN_DEG", 0), dxl_params.get("DXL_1_MAX_DEG", 360)),
            (dxl_params.get("DXL_2_MIN_DEG", 0), dxl_params.get("DXL_2_MAX_DEG", 360)),
            (dxl_params.get("DXL_3_MIN_DEG", 0), dxl_params.get("DXL_3_MAX_DEG", 360)),
            (dxl_params.get("DXL_4_MIN_DEG", 0), dxl_params.get("DXL_4_MAX_DEG", 360)),
            (dxl_params.get("DXL_5_MIN_DEG", 0), dxl_params.get("DXL_5_MAX_DEG", 360)),
        ]

    def check_limits(self, joint_angles):
        """
        @brief 3つの関節角度から5つのモーター角度を計算し、可動範囲内かチェックする。
        @param[in] joint_angles 3つの関節の目標角度リスト [j1, j2, j3]
        @param[out] tuple (is_safe: bool, violating_id: int)
        @details
        is_safeは、全モーターが範囲内ならTrue。violating_idは、最初に範囲外になったモーターのID(1-5)、安全なら0。
        """
        # 3つの関節角度から5つのモーター角度を計算
        motor1_angle = joint_angles[0]
        motor2_angle = 360.0 - joint_angles[0]
        motor3_angle = joint_angles[1]
        motor4_angle = 360.0 - joint_angles[1]
        motor5_angle = joint_angles[2]

        all_motor_angles = [motor1_angle, motor2_angle, motor3_angle, motor4_angle, motor5_angle]

        # 各モーターが可動範囲内かチェック
        for i in range(5):
            if not (self.motor_limits[i][0] <= all_motor_angles[i] <= self.motor_limits[i][1]):
                # 範囲外のモーターがあればFalseを返す
                return False, i + 1
        
        # すべて範囲内ならTrueを返す
        return True, 0

class ArmControlAngleNode(Node):
    """
    @class ArmControlAngleNode
    @brief 目標角度に基づきアームを直接制御するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。パラメータ読み込み、制御モジュールのインスタンス化、Subscriberの作成を行う。
        """
        super().__init__('arm_control_node')
        
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        dxl_params = params["dxl_params"]
        z_params = params["ZAxis_params"]
        
        # 制御モジュールのインスタンス化
        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        
        # ★★★ 安全装置のインスタンス化 ★★★
        self.limiter = SafetyLimiter(dxl_params)
        
        self.angle_subscriber = self.create_subscription(
            Float32MultiArray, 'target_arm_angles', self.angle_callback, 10)
        self.z_pos_subscriber = self.create_subscription(
            Float32, 'target_z_pos', self.z_pos_callback, 10)
        
        self.get_logger().info("Arm Control Node (with Safety Limiter) has been started.")

        self.arm_controller.init_pos()
        self.z_controller.init_pos()
        self.get_logger().info("アームを初期化しました。")

    def angle_callback(self, msg):
        """
        @brief /target_arm_angles 受信時のコールバック関数
        """
        if len(msg.data) != 3:
            self.get_logger().warn(f"受信した角度の数が不正です。期待: 3, 実際: {len(msg.data)}")
            return
            
        joint_angles = list(msg.data)
        
        # ★★★ 安全装置でチェック ★★★
        is_safe, violating_id = self.limiter.check_limits(joint_angles)

        if is_safe:
            # 安全な場合のみモーターに指令を送る
            self.arm_controller.move_motors(joint_angles, task="target")
        else:
            # 危険な場合は警告を出し、何もしない
            self.get_logger().warn(f"目標角度がモーター{violating_id}の可動範囲外のため、指令をキャンセルしました。")

    def z_pos_callback(self, msg):
        """
        @brief /target_z_pos 受信時のコールバック関数
        """
        target_z = msg.data
        self.z_controller.move2target(target_z)

    @staticmethod
    def load_yaml(file_path):
        """YAMLファイルを読み込むヘルパー関数"""
        try:
            with open(file_path, "r") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise e

def main(args=None):
    rclpy.init(args=args)
    node = ArmControlAngleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.arm_controller.torque_disable()
        node.get_logger().info("モーターのトルクをオフにしました。")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
