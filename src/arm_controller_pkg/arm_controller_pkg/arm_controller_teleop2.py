import rclpy
from rclpy.node import Node
import yaml
import sys
from geometry_msgs.msg import Point
from std_msgs.msg import Float32, String, Bool
import time
from toms_msg.srv import ArmService

sys.path.append("/home/ylab/hibikino_toms_ws/src/arm_controller_pkg/arm_controller_pkg/modules")
from .modules.ik_solver_arm2 import InverseKinematicsSolver
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis
from .modules.angle_converter import AngleConverter

class ArmControllerTeleop(Node):
    def __init__(self):
        super().__init__('arm_control_teleop')
        yaml_path = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
        params = self.load_yaml(yaml_path)
        dxl_params, ik_params, z_params = params["dxl_params"], params["ik_solver_params"], params["ZAxis_params"]
        self.arm_controller = MotorController(dxl_params)
        self.z_controller = ZAxis(z_params)
        self.solver = InverseKinematicsSolver(ik_params)
        self.angle_converter = AngleConverter(dxl_params)
        self.box_angles = dxl_params["DXL_BOX_ANGLE"]
        
        self.teleop_locked = False
        
        self.last_harvest_position, self.last_harvest_angle = None, 0.0
        self.pos_subscriber = self.create_subscription(Point, 'target_arm_pos', self.pos_callback, 10)
        self.angle_subscriber = self.create_subscription(Float32, 'target_arm_angle', self.angle_callback, 10)
        self.srv = self.create_service(ArmService, "arm_service", self.service_callback)
        self.target_angle = 0.0

        # ★★★ 入力値の可動範囲を定義 ★★★
        self.x_limit = {'min': -40.0, 'max': 250.0}
        self.y_limit = {'min': 0.0, 'max': 500.0}
        self.z_limit = {'min': 0.0, 'max': 450.0} # Z軸の物理的な可動範囲に合わせる
        self.angle_limit = {'min': -90.0, 'max': 90.0}
        self.get_logger().info(f"入力値の制限を設定しました: X={self.x_limit}, Y={self.y_limit}, Z={self.z_limit}, Angle={self.angle_limit}")
        
        self.get_logger().info("Arm Controller (Teleop/Service) Node has been started.")
        self.initialize_all_systems()

    def initialize_all_systems(self):
        self.get_logger().info("--- システム全体の初期化を開始します ---")
        
        # 1. 最初に内部で保持しているコントローラーの入力値をリセット
        self.target_angle = 0.0
        self.last_harvest_position = None
        self.last_harvest_angle = 0.0
        self.get_logger().info("コントローラーの内部目標値をリセットしました。")

        # 2. 次にアームとZ軸を物理的な初期位置へ移動
        self.get_logger().info("アームとZ軸を初期位置へ移動します。")
        self.arm_controller.init_pos()
        self.z_controller.init_pos()

        self.get_logger().info("--- 初期化が完了しました ---")

    def service_callback(self, request, response):
        self.get_logger().info(f"サービス実行中... (Task: {request.task})")
        success = True
        
        if request.task == "lock_teleop":
            self.get_logger().info("手動操作をロックします。")
            self.teleop_locked = True
        elif request.task == "unlock_teleop":
            self.get_logger().info("手動操作のロックを解除します。")
            self.teleop_locked = False
        elif request.task == "init_arm":
            # 修正された初期化メソッドを呼び出す
            self.initialize_all_systems()
        elif request.task == "move_to_box":
            self.arm_controller.move_motors(self.box_angles, task="box")
        else:
            self.get_logger().warn(f"未定義タスク: {request.task}")
            success = False
            
        response.task_comp = success
        self.get_logger().info("サービス完了。")
        return response

    def angle_callback(self, msg):
        if self.teleop_locked: return

        # ★★★ 入力値をmin/maxの範囲内に制限（クランプ） ★★★
        original_angle = msg.data
        clamped_angle = max(self.angle_limit['min'], min(self.angle_limit['max'], original_angle))
        
        # 制限された値を目標角度として設定
        self.target_angle = clamped_angle

    def pos_callback(self, msg):
        if self.teleop_locked:
            return
        
        # ★★★ 入力値を各軸のmin/maxの範囲内に制限（クランプ） ★★★
        clamped_x = max(self.x_limit['min'], min(self.x_limit['max'], msg.x))
        clamped_y = max(self.y_limit['min'], min(self.y_limit['max'], msg.y))
        clamped_z = max(self.z_limit['min'], min(self.z_limit['max'], msg.z))

        # 制限された値を目標位置として保存し、アームを動かす
        self.last_harvest_position = Point(x=clamped_x, y=clamped_y, z=clamped_z)
        self.last_harvest_angle = self.target_angle
        self._calculate_and_move_arm(clamped_x, clamped_y, clamped_z, self.target_angle)

    def _calculate_and_move_arm(self, target_x, target_y, target_z, approach_angle):
        try:
            pre_positions = self.arm_controller.read_positions()
            if not pre_positions: return False
            pre_motor_angles_deg = [self.arm_controller.position_to_angle(pos) for pos in pre_positions]
            current_ik_angles = self.angle_converter.dxl_ang2ik_ang(pre_motor_angles_deg[:3])
            current_x, current_y, current_angle = self.solver.forward_kinematics(current_ik_angles[0], current_ik_angles[1], current_ik_angles[2])
            current_EE_posi_angle, target_EE_posi_angle = [current_x, current_y, current_angle], [target_x, target_y, approach_angle]
            _, next_motor_angles_ik, solve_done = self.solver.solve_ik(current_EE_posi_angle, target_EE_posi_angle, current_ik_angles)
            if not solve_done: self.get_logger().warn("逆運動学の解なし"); return False
            next_motor_angles_dxl, check_angle = self.angle_converter.ik_ang2dxl_ang(next_motor_angles_ik)
            if not check_angle: self.get_logger().warn("可動範囲外"); return False
            self.arm_controller.move_motors(next_motor_angles_dxl, task="target")
            self.z_controller.move2target(target_z)
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