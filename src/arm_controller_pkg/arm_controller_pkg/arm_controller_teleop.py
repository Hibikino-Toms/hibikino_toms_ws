#
# @file arm_controller_teleop.py
# @brief 遠隔操作用のロボットアーム制御ノード
#
# @details
# /target_arm_pos と /target_arm_angle トピックから目標値を受け取り、
# 逆運動学を計算してアームとZ軸を制御します。
#
import rclpy
from rclpy.node import Node
import yaml
import sys
from geometry_msgs.msg import Point
from std_msgs.msg import Float32 # Float32を追加

# --- 元のarm_controller.pyと同様のモジュールをインポート ---
sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
from .modules.ik_solver_arm2 import InverseKinematicsSolver
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis
from .modules.angle_converter import AngleConverter
# ---------------------------------------------------------

class ArmControllerTeleop(Node):
    """
    @class ArmControlNode
    @brief 目標座標と角度に基づきアームを制御するクラス
    """
    def __init__(self):
        """
        @brief コンストラクタ。パラメータ読み込み、制御モジュールのインスタンス化、Subscriberの作成を行う。
        """
        super().__init__('arm_control_teleop')
        
        # パラメータファイルの読み込み
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        dxl_params = params["dxl_params"]
        ik_params = params["ik_solver_params"]
        z_params = params["ZAxis_params"]
        
        # 制御モジュールのインスタンス化
        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        self.solver = InverseKinematicsSolver(ik_params)
        self.angle_converter = AngleConverter(dxl_params)
        
        # 目標値を受け取るSubscriber
        self.pos_subscriber = self.create_subscription(Point, 'target_arm_pos', self.pos_callback, 10)
        self.angle_subscriber = self.create_subscription(Float32, 'target_arm_angle', self.angle_callback, 10) # ★★★ 角度用のSubscriberを追加 ★★★

        # ★★★ 目標角度を保持する変数を初期化 ★★★
        self.target_angle = 0.0
        
        self.get_logger().info("Arm Control Node has been started.")
        # 初期位置へ移動
        self.arm_controller.init_pos()
        self.z_controller.init_pos()
        self.get_logger().info("アームを初期化しました。")

    def angle_callback(self, msg):
        """
        @brief /target_arm_angle 受信時のコールバック関数
        @param[in] msg std_msgs/msg/Float32型のメッセージ
        @details 受信した目標角度をクラスのメンバ変数に保持する。
        """
        self.target_angle = msg.data

    def pos_callback(self, msg):
        """
        @brief /target_arm_pos受信時のコールバック関数
        @param[in] msg geometry_msgs/msg/Point型のメッセージ
        @details
        受信した座標と、保持している目標角度に対して逆運動学を解き、アームとZ軸を制御する。
        """
        target_x, target_y, target_z = msg.x, msg.y, msg.z
        
        # ★★★ 手先の姿勢角は、Subscriberで受信した最新の値を使用 ★★★
        approach_angle = self.target_angle
        
        # 現在のモータ角度を読み取り、IK計算用の角度系に変換
        pre_motor_angles = self.arm_controller.read_positions()
        pre_motor_angles_deg = [self.arm_controller.position_to_angle(pos) for pos in pre_motor_angles]
        pre_motor_angles_deg.pop(1)
        pre_motor_angles_deg.pop(2)
        current_ik_angles = self.angle_converter.dxl_ang2ik_ang(pre_motor_angles_deg)

        # 現在の手先位置と姿勢を順運動学で計算
        current_x, current_y, current_angle = self.solver.forward_kinematics(
            current_ik_angles[0], current_ik_angles[1], current_ik_angles[2]
        )
        
        # 逆運動学を解く
        current_EE_posi_angle = [current_x, current_y, current_angle]
        target_EE_posi_angle = [target_x, target_y, approach_angle]
        
        next_posi, next_motor_angles_ik, solve_done = self.solver.solve_ik(
            current_EE_posi_angle, target_EE_posi_angle, current_ik_angles
        )

        if not solve_done:
            self.get_logger().warn("逆運動学の解が見つかりませんでした。")
            return

        # モータ用の角度に変換
        next_motor_angles_dxl, check_angle = self.angle_converter.ik_ang2dxl_ang(next_motor_angles_ik)

        if not check_angle:
            self.get_logger().warn("計算された角度が可動範囲外です。")
            return
            
        # モータを動かす
        self.arm_controller.move_motors(next_motor_angles_dxl, task="target")
        self.z_controller.move2target(target_z)
        self.get_logger().info(f"Moving to X:{target_x:.1f}, Y:{target_y:.1f}, Z:{target_z:.1f}, Angle:{approach_angle:.1f}")

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
    node = ArmControllerTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()