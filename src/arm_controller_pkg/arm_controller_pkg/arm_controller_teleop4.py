import rclpy
from rclpy.node import Node
import yaml
import sys
from geometry_msgs.msg import Point, Pose
from std_msgs.msg import String
import time
from toms_msg.srv import ArmService
import math
from tf_transformations import euler_from_quaternion

sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
from .modules.ik_solver_arm2 import InverseKinematicsSolver
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis
from .modules.angle_converter import AngleConverter

class ArmControllerTeleop(Node):
    def __init__(self):
        super().__init__('arm_control_teleop')
        self.get_logger().info('arm_controller_teleopを起動します。')
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        dxl_params, ik_params, z_params = params["dxl_params"], params["ik_solver_params"], params["ZAxis_params"]
        arm_params_yaml = params.get('arm_params', {'INIT_X': 0.0, 'INIT_Y': 180.0, 'INIT_ANG': 90.0})

        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        self.solver = InverseKinematicsSolver(ik_params)
        self.angle_converter = AngleConverter(dxl_params)
        self.box_angles = dxl_params["DXL_BOX_ANGLE"]
        
        self.teleop_locked = False
        
        # ★★★ Subscriberを削除し、Serviceのみに変更 ★★★
        # self.pose_subscriber = self.create_subscription(Pose, 'target_arm_pose', self.pose_callback, 10)
        self.srv = self.create_service(ArmService, "arm_service", self.service_callback)
        
        # ★★★ 手動操作時の目標値を内部で保持 ★★★
        self.manual_target_pos = Point()
        self.manual_target_angle_deg = 90.0
        self.step_size_cm = 5.0 # 1回の入力で動く距離(cm)
        self.angle_step_size_deg = 5.0 # 1回の入力で動く角度(deg)

        self.get_logger().info("Arm Controller (Service Mode) has been started.")
        self.initialize_all_systems()

    def initialize_all_systems(self):
        self.get_logger().info("--- システム全体の初期化を開始します ---")
        self.get_logger().info("アームとZ軸を初期位置へ移動します")
        self.arm_controller.init_pos()
        self.z_controller.init_pos()
        
        # ★★★ 初期化時に内部の目標値もリセット ★★★
        # 実際の初期位置を読み込むのが理想だが、ここでは固定値とする
        time.sleep(1.0) # モーターが初期位置に移動するのを待つ
        try:
            # 現在位置を読み込んで手動操作の開始位置とする
            pre_positions = self.arm_controller.read_positions()
            pre_motor_angles_deg = [self.arm_controller.position_to_angle(pos) for pos in pre_positions]
            current_ik_angles = self.angle_converter.dxl_ang2ik_ang(pre_motor_angles_deg[:3])
            current_x, current_y, current_angle = self.solver.forward_kinematics(current_ik_angles[0], current_ik_angles[1], current_ik_angles[2])
            self.manual_target_pos.x = current_x
            self.manual_target_pos.y = current_y
            self.manual_target_pos.z = self.z_controller.read_position() # Z軸の現在位置を読み込む
            self.manual_target_angle_deg = current_angle
            self.get_logger().info(f"手動操作の開始位置を更新: Pos:[{current_x:.1f}, {current_y:.1f}, {self.manual_target_pos.z:.1f}], Ang:{current_angle:.1f}")
        except Exception as e:
            self.get_logger().error(f"初期位置の読み込みに失敗: {e}。デフォルト値を使用します。")
            self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z = 0.0, 180.0, 0.0
            self.manual_target_angle_deg = 90.0

        self.get_logger().info("--- 初期化が完了しました ---")

    def service_callback(self, request, response):
        self.get_logger().info(f"サービス実行中... (Task: {request.task})")
        success = True
        
        task = request.task
        
        # ★★★ ステップ動作の指令を追加 ★★★
        step_mm = self.step_size_cm * 10.0
        if self.teleop_locked and "step" in task:
            self.get_logger().warn("手動操作はロックされています。")
            success = False
        elif task == "step_x_plus": success = self._calculate_and_move_arm(self.manual_target_pos.x + step_mm, self.manual_target_pos.y, self.manual_target_pos.z, self.manual_target_angle_deg)
        elif task == "step_x_minus": success = self._calculate_and_move_arm(self.manual_target_pos.x - step_mm, self.manual_target_pos.y, self.manual_target_pos.z, self.manual_target_angle_deg)
        elif task == "step_y_plus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y + step_mm, self.manual_target_pos.z, self.manual_target_angle_deg)
        elif task == "step_y_minus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y - step_mm, self.manual_target_pos.z, self.manual_target_angle_deg)
        elif task == "step_z_plus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z + step_mm, self.manual_target_angle_deg)
        elif task == "step_z_minus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z - step_mm, self.manual_target_angle_deg)
        elif task == "step_angle_plus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z, self.manual_target_angle_deg + self.angle_step_size_deg)
        elif task == "step_angle_minus": success = self._calculate_and_move_arm(self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z, self.manual_target_angle_deg - self.angle_step_size_deg)
        
        # 既存のサービス機能
        elif task == "lock_teleop": self.teleop_locked = True
        elif task == "unlock_teleop": self.teleop_locked = False
        elif task == "init_arm": self.initialize_all_systems()
        elif task == "move_to_box": self.arm_controller.move_motors(self.box_angles, task="box")
        else:
            self.get_logger().warn(f"未定義タスク: {task}")
            success = False
            
        response.task_comp = success
        self.get_logger().info("サービス完了。")
        return response

    def _calculate_and_move_arm(self, target_x, target_y, target_z, approach_angle):
        try:
            # ... (中略) ...
            next_motor_angles_dxl, check_angle = self.angle_converter.ik_ang2dxl_ang(next_motor_angles_ik)
            if not check_angle: self.get_logger().warn("可動範囲外"); return False
            
            self.arm_controller.move_motors(next_motor_angles_dxl, task="target")
            self.z_controller.move2target(target_z)
            
            # ★★★ 移動成功時に内部の目標値を更新 ★★★
            self.manual_target_pos.x, self.manual_target_pos.y, self.manual_target_pos.z = target_x, target_y, target_z
            self.manual_target_angle_deg = approach_angle
            
            return True
        except Exception as e:
            self.get_logger().error(f"モーター指令・計算中にエラー: {e}"); return False

    @staticmethod
    def load_yaml(file_path):
        with open(file_path, "r") as file: return yaml.safe_load(file)

def main(args=None):
    rclpy.init(args=args)
    node = ArmControllerTeleop()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()