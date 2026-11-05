import math
import time

import rclpy
import yaml
from geometry_msgs.msg import Pose
from rclpy.node import Node
from sensor_msgs.msg import Joy
from toms_msg.srv import ArmService

from arm_controller_pkg.modules.angle_converter import AngleConverter
from arm_controller_pkg.modules.ik_solver_arm2 import InverseKinematicsSolver


PARAMS_PATH = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
ARM_LIMITS = {
    'x': (-40.0, 250.0),
    'y': (0.0, 500.0),
    'z': (0.0, 450.0),
    'angle': (-90.0, 90.0),
}


class TeleopDemoCodex(Node):
    """Nonblocking F310 teleop publisher for the arm and Z axis only."""

    def __init__(self):
        super().__init__('teleop_demo_codex')

        with open(PARAMS_PATH, 'r', encoding='utf-8') as stream:
            params = yaml.safe_load(stream)
        arm_params = params['arm_params']
        dxl_params = params['dxl_params']

        self.declare_parameter('joy_topic', 'joy')
        self.declare_parameter('pose_topic', 'target_arm_pose')
        self.declare_parameter('arm_service', 'arm_service')
        self.declare_parameter('joy_params.x_axis', 0)
        self.declare_parameter('joy_params.y_axis', 1)
        self.declare_parameter('joy_params.z_axis', 5)
        self.declare_parameter('joy_params.angle_axis', 2)
        self.declare_parameter('joy_params.home_button', 3)
        self.declare_parameter('joy_params.unused_button', 2)
        self.declare_parameter('scale.xy', 50.0)
        self.declare_parameter('scale.z', 50.0)
        self.declare_parameter('scale.angle', 90.0)
        self.declare_parameter('deadzone', 0.1)
        self.declare_parameter('command_period_sec', 0.2)

        self.axis_indices = {
            name: int(self.get_parameter(f'joy_params.{name}_axis').value)
            for name in ('x', 'y', 'z', 'angle')
        }
        self.home_button = int(self.get_parameter('joy_params.home_button').value)
        self.unused_button = int(self.get_parameter('joy_params.unused_button').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.command_period = float(self.get_parameter('command_period_sec').value)
        if self.command_period <= 0.0:
            raise ValueError('command_period_sec は正の値にしてください。')

        self.scales = {
            'x': float(self.get_parameter('scale.xy').value),
            'y': float(self.get_parameter('scale.xy').value),
            'z': float(self.get_parameter('scale.z').value),
            'angle': float(self.get_parameter('scale.angle').value),
        }

        self.pose_pub = self.create_publisher(
            Pose, str(self.get_parameter('pose_topic').value), 10)
        self.joy_sub = self.create_subscription(
            Joy, str(self.get_parameter('joy_topic').value), self._joy_callback, 10)
        self.arm_client = self.create_client(
            ArmService, str(self.get_parameter('arm_service').value))

        self.solver = InverseKinematicsSolver(params['ik_solver_params'])
        self.angle_converter = AngleConverter(dxl_params)
        self.home_ik_angles = self.angle_converter.dxl_ang2ik_ang(
            dxl_params['DXL_HOME_ANGLE'])
        home_x, home_y, home_angle = self.solver.forward_kinematics(
            *self.home_ik_angles)
        self.home_ik_position = [home_x, home_y, home_angle]

        self.initial_position = [
            float(arm_params['INIT_X']),
            float(arm_params['INIT_Y']),
            0.0,
            max(ARM_LIMITS['angle'][0], min(
                ARM_LIMITS['angle'][1], float(arm_params['INIT_ANG']))),
        ]
        self._reset_local_state()

        self.latest_axes = None
        self.previous_buttons = []
        self.last_update_time = time.monotonic()
        self.last_publish_time = float('-inf')
        self.wait_for_neutral = False
        self.home_stage = None
        self.home_future = None

        self.timer = self.create_timer(0.05, self._control_loop)
        self.get_logger().info(
            'F310操作開始: 左スティック=アームXY、十字キー上下=Z、右スティック左右=角度')
        self.get_logger().info(
            'Yボタン=アーム/Z初期位置へ復帰、Bボタン=無効。エンドエフェクタとレールは操作しません。')
        self.get_logger().info(
            f'指令更新は最大{1.0 / self.command_period:.1f}Hz、音声再生なし')

    def _reset_local_state(self):
        self.position = list(self.initial_position)
        self.ik_angles = list(self.home_ik_angles)
        self.ik_position = list(self.home_ik_position)

    def _joy_callback(self, msg):
        self.latest_axes = list(msg.axes)
        buttons = list(msg.buttons)
        home_pressed = (
            self.home_button < len(buttons)
            and buttons[self.home_button] == 1
            and (self.home_button >= len(self.previous_buttons)
                 or self.previous_buttons[self.home_button] == 0)
        )
        if home_pressed:
            self._begin_home('Yボタン')

        unused_pressed = (
            self.unused_button < len(buttons)
            and buttons[self.unused_button] == 1
            and (self.unused_button >= len(self.previous_buttons)
                 or self.previous_buttons[self.unused_button] == 0)
        )
        if unused_pressed:
            self.get_logger().info('Bボタンはアーム/Z専用モードでは使用しません。')
        self.previous_buttons = buttons

    def _control_loop(self):
        now = time.monotonic()
        dt = min(max(now - self.last_update_time, 0.0), 0.1)
        self.last_update_time = now

        if self._advance_home():
            return
        if self.latest_axes is None or dt <= 0.0:
            return

        axes = {name: self._axis_value(index)
                for name, index in self.axis_indices.items()}
        if self.wait_for_neutral:
            if any(abs(value) > self.deadzone for value in axes.values()):
                return
            self.wait_for_neutral = False
            self.get_logger().info('スティックが中立になりました。操作を再開できます。')

        if all(value == 0.0 for value in axes.values()):
            return

        candidate = list(self.position)
        candidate[0] -= axes['x'] * self.scales['x'] * dt
        candidate[1] += axes['y'] * self.scales['y'] * dt
        candidate[2] += axes['z'] * self.scales['z'] * dt
        candidate[3] += axes['angle'] * self.scales['angle'] * dt

        if not self._within_limits(candidate):
            self._begin_home('設定されたXYZ/角度の可動範囲を超える入力')
            return

        arm_target_changed = candidate[0] != self.position[0] or candidate[1] != self.position[1] or candidate[3] != self.position[3]
        next_ik_angles = self.ik_angles
        next_ik_position = self.ik_position
        if arm_target_changed:
            goal = [candidate[0], candidate[1], candidate[3]]
            _, next_ik_angles, solved = self.solver.solve_ik(
                self.ik_position, goal, self.ik_angles)
            if not solved:
                self._begin_home('逆運動学で到達できない入力')
                return
            _, in_motor_limits = self.angle_converter.ik_ang2dxl_ang(next_ik_angles)
            if not in_motor_limits:
                self._begin_home('モータ角度の可動範囲を超える入力')
                return
            next_ik_position = goal

        self.position = candidate
        self.ik_angles = list(next_ik_angles)
        self.ik_position = list(next_ik_position)

        if now - self.last_publish_time < self.command_period:
            return
        self._publish_pose()
        self.last_publish_time = now

    def _axis_value(self, index):
        if index < 0 or index >= len(self.latest_axes):
            return 0.0
        value = max(-1.0, min(1.0, float(self.latest_axes[index])))
        return 0.0 if abs(value) < self.deadzone else value

    @staticmethod
    def _within_limits(position):
        return all(
            lower <= value <= upper
            for value, (lower, upper) in zip(
                position,
                (ARM_LIMITS['x'], ARM_LIMITS['y'], ARM_LIMITS['z'], ARM_LIMITS['angle']))
        )

    def _publish_pose(self):
        message = Pose()
        message.position.x = self.position[0]
        message.position.y = self.position[1]
        message.position.z = self.position[2]
        half_angle = math.radians(self.position[3]) * 0.5
        message.orientation.z = math.sin(half_angle)
        message.orientation.w = math.cos(half_angle)
        self.pose_pub.publish(message)

    def _begin_home(self, reason):
        if self.home_stage is not None:
            return
        self.get_logger().warning(f'{reason}。アームとZ軸を初期位置へ戻します。')
        self.home_stage = 'lock_teleop'
        self.home_future = None
        self.wait_for_neutral = True

    def _advance_home(self):
        if self.home_stage is None:
            return False
        if self.home_stage == 'failed':
            return True

        if self.home_future is None:
            if not self.arm_client.service_is_ready():
                return True
            request = ArmService.Request()
            request.task = self.home_stage
            self.home_future = self.arm_client.call_async(request)
            return True

        if not self.home_future.done():
            return True

        try:
            response = self.home_future.result()
            if not response.task_comp:
                raise RuntimeError(f'{self.home_stage} が失敗しました。')
        except Exception as error:
            self.get_logger().error(f'初期位置復帰サービスに失敗しました: {error}')
            self.home_stage = 'failed'
            self.home_future = None
            return True

        if self.home_stage == 'lock_teleop':
            self.home_stage = 'init_arm'
        elif self.home_stage == 'init_arm':
            self._reset_local_state()
            self.home_stage = 'unlock_teleop'
        else:
            self.home_stage = None
            self.wait_for_neutral = True
            self.get_logger().info('初期位置への復帰が完了しました。スティックを中立にしてください。')
        self.home_future = None
        return True


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TeleopDemoCodex()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'teleop_demo_codex 起動失敗: {error}')
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
